import json
import logging
import re
from datetime import date
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
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


def _server_error(error):
    """Log the exception while returning a safe response to the client."""
    logger.exception("StudyAI request failed: %s", error)
    return JsonResponse(
        {"error": "The request could not be completed. Check the backend logs."},
        status=502,
    )


# ── 1. SOLVE PROBLEM ─────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def solve(request):
    try:
        data    = json.loads(request.body)
        problem = data.get("problem", "").strip()

        if not problem:
            return JsonResponse({"error": "Problem text is required."}, status=400)

        subject  = detect_subject(problem)
        solution = solve_problem(problem)

        ProblemHistory.objects.create(
            problem=problem,
            solution=solution,
            subject=subject
        )

        return JsonResponse({
            "success":  True,
            "solution": solution,
            "subject":  subject,
        })

    except Exception as error:
        return _server_error(error)


# ── 2. OCR ────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def ocr(request):
    try:
        if "image" not in request.FILES:
            return JsonResponse({"error": "No image file provided."}, status=400)

        image_file = request.FILES["image"]
        result     = extract_text(image_file)

        return JsonResponse(result)

    except Exception as error:
        return _server_error(error)


# ── 3. FLASHCARDS ─────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def flashcards(request):
    try:
        data  = json.loads(request.body)
        notes = data.get("notes", "").strip()
        topic = data.get("topic", "General").strip()

        if not notes:
            return JsonResponse({"error": "Notes text is required."}, status=400)

        cards = generate_flashcards(notes)

        for card in cards:
            Flashcard.objects.create(
                topic=topic,
                question=card["question"],
                answer=card["answer"]
            )

        return JsonResponse({
            "success":    True,
            "flashcards": cards,
            "count":      len(cards),
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Could not parse AI response. Try again."}, status=500)
    except Exception as error:
        return _server_error(error)


# ── 4. QUIZ ───────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def quiz(request):
    try:
        data  = json.loads(request.body)
        topic = data.get("topic", "").strip()
        test_type = data.get("type", "mcq").strip().lower()
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

    except json.JSONDecodeError:
        return JsonResponse({"error": "Could not parse AI response. Try again."}, status=500)
    except Exception as error:
        return _server_error(error)


# ── 5. HISTORY ────────────────────────────────────────────────────────────────
@require_http_methods(["GET"])
def history(request):
    try:
        problems = ProblemHistory.objects.all()[:20]

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
@csrf_exempt
@require_http_methods(["DELETE"])
def clear_history(request):
    try:
        ProblemHistory.objects.all().delete()
        Flashcard.objects.all().delete()

        return JsonResponse({
            "success": True,
            "message": "All history cleared.",
        })

    except Exception as error:
        return _server_error(error)


# ── 7. STUDY PLANNER ──────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def study_plan(request):
    try:
        data          = json.loads(request.body)
        topics        = data.get("topics", "").strip()
        exam_date     = data.get("exam_date", "").strip()
        hours_per_day = data.get("hours_per_day", "2").strip()

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

        plan = generate_study_plan(topics, exam_date, hours_per_day)

        return JsonResponse({
            "success": True,
            "plan":    plan,
        })

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


@csrf_exempt
@require_http_methods(["GET", "POST"])
def saved_plans(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Please log in to manage study plans."}, status=401)

    if request.method == "GET":
        plans = StudyPlan.objects.filter(user=request.user)
        return JsonResponse({"success": True, "plans": [_serialize_plan(plan) for plan in plans]})

    try:
        data = json.loads(request.body)
        title = data.get("title", "Untitled study plan").strip() or "Untitled study plan"
        topics = data.get("topics", "").strip()
        exam_date = date.fromisoformat(data.get("exam_date", ""))
        hours_per_day = int(data.get("hours_per_day", 2))
        plan_text = data.get("plan", "").strip()
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


@csrf_exempt
@require_http_methods(["PATCH", "DELETE"])
def saved_plan_detail(request, plan_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Please log in to manage study plans."}, status=401)
    try:
        saved_plan = StudyPlan.objects.get(id=plan_id, user=request.user)
    except StudyPlan.DoesNotExist:
        return JsonResponse({"error": "Study plan not found."}, status=404)

    if request.method == "DELETE":
        saved_plan.delete()
        return JsonResponse({"success": True})

    try:
        data = json.loads(request.body)
        if "title" in data:
            saved_plan.title = data["title"].strip() or saved_plan.title
        if "topics" in data:
            saved_plan.topics = data["topics"].strip()
        if "exam_date" in data:
            saved_plan.exam_date = date.fromisoformat(data["exam_date"])
        if "hours_per_day" in data:
            saved_plan.hours_per_day = int(data["hours_per_day"])
        if "plan" in data:
            saved_plan.plan = data["plan"].strip()
        saved_plan.save()
        return JsonResponse({"success": True, "plan": _serialize_plan(saved_plan)})
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"error": "Please provide valid plan details."}, status=400)
    except Exception as error:
        return _server_error(error)


# ── 8. SUMMARIZER ─────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def summarize(request):
    try:
        data   = json.loads(request.body)
        text   = data.get("text", "").strip()
        length = data.get("length", "medium").strip()

        if not text:
            return JsonResponse({"error": "Text is required."}, status=400)

        summary = summarize_text(text, length)

        return JsonResponse({
            "success": True,
            "summary": summary,
        })

    except Exception as error:
        return _server_error(error)


# ── 9. FORMULA SHEET ──────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def formula_sheet(request):
    try:
        data  = json.loads(request.body)
        notes = data.get("notes", "").strip()

        if not notes:
            return JsonResponse({"error": "Notes are required."}, status=400)

        formulas = generate_formula_sheet(notes)

        return JsonResponse({
            "success":  True,
            "formulas": formulas,
        })

    except Exception as error:
        return _server_error(error)


# ── 10. EXPLAIN LIKE I'M 5 ────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def explain_like_five(request):
    try:
        data      = json.loads(request.body)
        topic     = data.get("topic", "").strip()
        age_group = data.get("age_group", "child").strip()

        if not topic:
            return JsonResponse({"error": "Topic is required."}, status=400)

        explanation = explain_simple(topic, age_group)

        return JsonResponse({
            "success":     True,
            "explanation": explanation,
        })

    except Exception as error:
        return _server_error(error)


# ── MDCAT TOPIC COACH ─────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def topic_study_guide(request):
    try:
        data = json.loads(request.body)
        topic = data.get("topic", "").strip()
        difficulty = data.get("difficulty", "medium").strip().lower()

        if not topic:
            return JsonResponse({"error": "Topic is required."}, status=400)
        if len(topic) > 200:
            return JsonResponse({"error": "Topic must be 200 characters or fewer."}, status=400)
        if difficulty not in {"medium", "advanced"}:
            return JsonResponse({"error": "Choose medium or advanced difficulty."}, status=400)

        guide = generate_topic_study_guide(topic, difficulty)
        return JsonResponse({"success": True, **guide})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Please provide a valid topic request."}, status=400)
    except Exception as error:
        return _server_error(error)


@csrf_exempt
@require_http_methods(["POST"])
def mdcat_chat(request):
    try:
        data = json.loads(request.body)
        message = data.get("message", "").strip()
        topic = data.get("topic", "").strip()[:200]
        history = data.get("history", [])
        if not message:
            return JsonResponse({"error": "Message is required."}, status=400)
        if len(message) > 2000:
            return JsonResponse({"error": "Message must be 2000 characters or fewer."}, status=400)
        if not isinstance(history, list):
            return JsonResponse({"error": "Chat history must be a list."}, status=400)
        reply = generate_mdcat_chat_reply(message, history, topic)
        return JsonResponse({"success": True, "reply": reply})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Please provide a valid chat request."}, status=400)
    except Exception as error:
        return _server_error(error)