import json
import logging
import re
from functools import wraps
from datetime import date
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import ProblemHistory, Flashcard, StudyPlan
from .ai_helper import (
    solve_problem,
    generate_flashcards,
    generate_quiz,
    generate_topic_study_guide,
    generate_mdcat_chat_reply,
    generate_written_test,
    generate_qa_test,
    detect_subject,
    generate_study_plan,
    summarize_text,
    generate_formula_sheet,
    explain_simple
)
from .ocr_helper import extract_text


logger = logging.getLogger(__name__)
MAX_AI_TEXT_LENGTH = 12_000


def api_login_required(view):
    """Return a JSON 401 for unauthenticated API requests instead of redirecting to HTML."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Please log in to access this resource."}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def rate_limit_ai(view):
    """Cap AI/OCR requests per client to reduce accidental or automated quota abuse."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        client_ip = request.META.get("REMOTE_ADDR", "unknown")
        cache_key = f"studyai:ai-rate:{client_ip}"
        if not cache.add(cache_key, 1, timeout=60):
            try:
                request_count = cache.incr(cache_key)
            except ValueError:
                cache.add(cache_key, 1, timeout=60)
                request_count = 1
            if request_count > 20:
                response = JsonResponse(
                    {"error": "Too many requests. Please wait a minute and try again."},
                    status=429,
                )
                response["Retry-After"] = "60"
                return response
        return view(request, *args, **kwargs)

    return wrapped


def _server_error(error):
    """Log the exception while returning a safe response to the client."""
    logger.exception("StudyAI request failed: %s", error)
    return JsonResponse(
        {"error": "The request could not be completed. Check the backend logs."},
        status=502,
    )


def _parse_json_object(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _invalid_json_response():
    return JsonResponse({"error": "Please provide a valid JSON object."}, status=400)


def _text_field(data, field, default="", *, max_length=MAX_AI_TEXT_LENGTH):
    value = data.get(field, default)
    if not isinstance(value, str):
        raise ValueError(f"{field.replace('_', ' ').capitalize()} must be text.")
    value = value.strip()
    if len(value) > max_length:
        raise ValueError(f"{field.replace('_', ' ').capitalize()} must be {max_length} characters or fewer.")
    return value


# ── 1. SOLVE PROBLEM ─────────────────────────────────────────────────────────
@rate_limit_ai
@require_http_methods(["POST"])
def solve(request):
    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        problem = _text_field(data, "problem")

        if not problem:
            return JsonResponse({"error": "Problem text is required."}, status=400)

        subject  = detect_subject(problem)
        solution = solve_problem(problem)

        if request.user.is_authenticated:
            ProblemHistory.objects.create(
                user=request.user,
                problem=problem,
                solution=solution,
                subject=subject
            )

        return JsonResponse({
            "success":  True,
            "solution": solution,
            "subject":  subject,
        })

    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Exception as error:
        return _server_error(error)


# ── 2. OCR ────────────────────────────────────────────────────────────────────
@rate_limit_ai
@require_http_methods(["POST"])
def ocr(request):
    try:
        if "image" not in request.FILES:
            return JsonResponse({"error": "No image file provided."}, status=400)

        image_file = request.FILES["image"]
        if image_file.size > 5 * 1024 * 1024:
            return JsonResponse({"error": "Image must be 5 MB or smaller."}, status=400)
        if image_file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            return JsonResponse({"error": "Upload a JPG, PNG, or WebP image."}, status=400)
        result     = extract_text(image_file)

        return JsonResponse(result)

    except Exception as error:
        return _server_error(error)


# ── 3. FLASHCARDS ─────────────────────────────────────────────────────────────
@rate_limit_ai
@require_http_methods(["POST"])
def flashcards(request):
    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        notes = _text_field(data, "notes")
        topic = _text_field(data, "topic", "General", max_length=200)

        if not notes:
            return JsonResponse({"error": "Notes text is required."}, status=400)

        cards = generate_flashcards(notes)

        if request.user.is_authenticated:
            for card in cards:
                Flashcard.objects.create(
                    user=request.user,
                    topic=topic,
                    question=card["question"],
                    answer=card["answer"]
                )

        return JsonResponse({
            "success":    True,
            "flashcards": cards,
            "count":      len(cards),
        })

    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Exception as error:
        return _server_error(error)


# ── 4. QUIZ ───────────────────────────────────────────────────────────────────
@rate_limit_ai
@require_http_methods(["POST"])
def quiz(request):
    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        topic = _text_field(data, "topic", max_length=200)
        test_type = _text_field(data, "type", "mcq", max_length=20).lower()
        requested_count = data.get("count")
        question_count = requested_count if requested_count not in (None, "") else 5
        if requested_count in (None, ""):
            mentioned_count = re.search(r"\b(\d{1,2})\s*(?:mcqs?|questions?)\b", topic, re.IGNORECASE)
            if mentioned_count:
                question_count = mentioned_count.group(1)

        if not topic:
            return JsonResponse({"error": "Topic is required."}, status=400)

        try:
            question_count = int(question_count)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Question count must be a whole number."}, status=400)

        if not 1 <= question_count <= 20:
            return JsonResponse({"error": "Choose between 1 and 20 questions."}, status=400)

        generators = {
            "mcq": generate_quiz,
            "written": generate_written_test,
            "qa": generate_qa_test,
        }
        if test_type not in generators:
            return JsonResponse({"error": "Choose MCQ, written, or Q&A test."}, status=400)

        questions = generators[test_type](topic, question_count)

        return JsonResponse({
            "success":   True,
            "questions": questions,
            "count":     len(questions),
                "type":      test_type,
        })

    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Exception as error:
        return _server_error(error)


# ── 5. HISTORY ────────────────────────────────────────────────────────────────
@require_http_methods(["GET"])
def history(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": True, "history": [], "count": 0})
    try:
        problems = ProblemHistory.objects.filter(user=request.user)[:20]

        data = [
            {
                "id":         p.id,
                "problem":    p.problem,
                "solution":   p.solution,
                "subject":    p.subject,
                "created_at": p.created_at.strftime("%b %d, %H:%M"),
            }
            for p in problems
        ]

        return JsonResponse({
            "success": True,
            "history": data,
            "count":   len(data),
        })

    except Exception as error:
        return _server_error(error)


# ── 6. CLEAR HISTORY ──────────────────────────────────────────────────────────
@require_http_methods(["DELETE"])
def clear_history(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": True, "message": "No signed-in history to clear."})
    try:
        ProblemHistory.objects.filter(user=request.user).delete()
        Flashcard.objects.filter(user=request.user).delete()

        return JsonResponse({
            "success": True,
            "message": "All history cleared.",
        })

    except Exception as error:
        return _server_error(error)


# ── 7. STUDY PLANNER ──────────────────────────────────────────────────────────
@rate_limit_ai
@require_http_methods(["POST"])
def study_plan(request):
    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        topics = _text_field(data, "topics", max_length=4_000)
        exam_date = _text_field(data, "exam_date", max_length=10)
        hours_per_day = data.get("hours_per_day", "2")
        if not isinstance(hours_per_day, (str, int)):
            return JsonResponse({"error": "Hours per day must be a whole number."}, status=400)
        try:
            hours_per_day = int(hours_per_day)
        except ValueError:
            return JsonResponse({"error": "Hours per day must be a whole number."}, status=400)
        if not 1 <= hours_per_day <= 24:
            return JsonResponse({"error": "Hours per day must be between 1 and 24."}, status=400)

        if not topics:
            return JsonResponse({"error": "Topics are required."}, status=400)
        if not exam_date:
            return JsonResponse({"error": "Exam date is required."}, status=400)
        try:
            selected_final_date = date.fromisoformat(exam_date)
        except ValueError:
            return JsonResponse({"error": "Please choose a valid final study date."}, status=400)
        if selected_final_date < date.today():
            return JsonResponse({"error": "Final study date cannot be before today."}, status=400)

        plan = generate_study_plan(topics, exam_date, str(hours_per_day))

        return JsonResponse({
            "success": True,
            "plan":    plan,
        })

    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Exception as error:
        return _server_error(error)


def _serialize_plan(saved_plan):
    return {
        "id": saved_plan.id,
        "title": saved_plan.title,
        "topics": saved_plan.topics,
        "exam_date": saved_plan.exam_date.isoformat(),
        "hours_per_day": saved_plan.hours_per_day,
        "plan": saved_plan.plan,
        "created_at": saved_plan.created_at.strftime("%b %d, %Y"),
        "updated_at": saved_plan.updated_at.strftime("%b %d, %Y %H:%M"),
    }


@api_login_required
@require_http_methods(["GET", "POST"])
def saved_plans(request):
    if request.method == "GET":
        plans = StudyPlan.objects.filter(user=request.user)
        return JsonResponse({"success": True, "plans": [_serialize_plan(plan) for plan in plans]})

    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        title = _text_field(data, "title", "Untitled study plan", max_length=200) or "Untitled study plan"
        topics = _text_field(data, "topics", max_length=4_000)
        exam_date = date.fromisoformat(_text_field(data, "exam_date", max_length=10))
        hours_per_day = int(data.get("hours_per_day", 2))
        plan_text = _text_field(data, "plan")
        if not topics or not plan_text:
            return JsonResponse({"error": "Topics and generated plan are required."}, status=400)
        if not 1 <= hours_per_day <= 24:
            return JsonResponse({"error": "Hours per day must be between 1 and 24."}, status=400)
        saved_plan = StudyPlan.objects.create(
            user=request.user,
            title=title,
            topics=topics,
            exam_date=exam_date,
            hours_per_day=hours_per_day,
            plan=plan_text,
        )
        return JsonResponse({"success": True, "plan": _serialize_plan(saved_plan)}, status=201)
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"error": "Please provide valid plan details."}, status=400)
    except Exception as error:
        return _server_error(error)


@api_login_required
@require_http_methods(["PATCH", "DELETE"])
def saved_plan_detail(request, plan_id):
    try:
        saved_plan = StudyPlan.objects.get(id=plan_id, user=request.user)
    except StudyPlan.DoesNotExist:
        return JsonResponse({"error": "Study plan not found."}, status=404)

    if request.method == "DELETE":
        saved_plan.delete()
        return JsonResponse({"success": True})

    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        if "title" in data:
            saved_plan.title = _text_field(data, "title", max_length=200) or saved_plan.title
        if "topics" in data:
            saved_plan.topics = _text_field(data, "topics", max_length=4_000)
        if "exam_date" in data:
            saved_plan.exam_date = date.fromisoformat(_text_field(data, "exam_date", max_length=10))
        if "hours_per_day" in data:
            saved_plan.hours_per_day = int(data["hours_per_day"])
        if "plan" in data:
            saved_plan.plan = _text_field(data, "plan")
        saved_plan.save()
        return JsonResponse({"success": True, "plan": _serialize_plan(saved_plan)})
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"error": "Please provide valid plan details."}, status=400)
    except Exception as error:
        return _server_error(error)


# ── 8. SUMMARIZER ─────────────────────────────────────────────────────────────
@rate_limit_ai
@require_http_methods(["POST"])
def summarize(request):
    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        text = _text_field(data, "text")
        length = _text_field(data, "length", "medium", max_length=10)

        if not text:
            return JsonResponse({"error": "Text is required."}, status=400)

        summary = summarize_text(text, length)

        return JsonResponse({
            "success": True,
            "summary": summary,
        })

    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Exception as error:
        return _server_error(error)


# ── 9. FORMULA SHEET ──────────────────────────────────────────────────────────
@rate_limit_ai
@require_http_methods(["POST"])
def formula_sheet(request):
    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        notes = _text_field(data, "notes")

        if not notes:
            return JsonResponse({"error": "Notes are required."}, status=400)

        formulas = generate_formula_sheet(notes)

        return JsonResponse({
            "success":  True,
            "formulas": formulas,
        })

    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Exception as error:
        return _server_error(error)


# ── 10. EXPLAIN LIKE I'M 5 ────────────────────────────────────────────────────
@rate_limit_ai
@require_http_methods(["POST"])
def explain_like_five(request):
    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        topic = _text_field(data, "topic", max_length=200)
        age_group = _text_field(data, "age_group", "child", max_length=20)

        if not topic:
            return JsonResponse({"error": "Topic is required."}, status=400)

        explanation = explain_simple(topic, age_group)

        return JsonResponse({
            "success":     True,
            "explanation": explanation,
        })

    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Exception as error:
        return _server_error(error)


# ── MDCAT TOPIC COACH ─────────────────────────────────────────────────────────
@rate_limit_ai
@require_http_methods(["POST"])
def topic_study_guide(request):
    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        topic = _text_field(data, "topic", max_length=200)
        difficulty = _text_field(data, "difficulty", "medium", max_length=20).lower()

        if not topic:
            return JsonResponse({"error": "Topic is required."}, status=400)
        if len(topic) > 200:
            return JsonResponse({"error": "Topic must be 200 characters or fewer."}, status=400)
        if difficulty not in {"medium", "advanced"}:
            return JsonResponse({"error": "Choose medium or advanced difficulty."}, status=400)

        guide = generate_topic_study_guide(topic, difficulty)
        return JsonResponse({"success": True, **guide})
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Exception as error:
        return _server_error(error)


@rate_limit_ai
@require_http_methods(["POST"])
def mdcat_chat(request):
    try:
        data = _parse_json_object(request)
        if data is None:
            return _invalid_json_response()
        message = _text_field(data, "message", max_length=2_000)
        topic = _text_field(data, "topic", max_length=200)
        history = data.get("history", [])
        if not message:
            return JsonResponse({"error": "Message is required."}, status=400)
        if len(message) > 2000:
            return JsonResponse({"error": "Message must be 2000 characters or fewer."}, status=400)
        if not isinstance(history, list):
            return JsonResponse({"error": "Chat history must be a list."}, status=400)
        reply = generate_mdcat_chat_reply(message, history, topic)
        return JsonResponse({"success": True, "reply": reply})
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    except Exception as error:
        return _server_error(error)