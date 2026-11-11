import json
import re
from datetime import date
from functools import lru_cache

from google import genai
from google.genai import types
from django.conf import settings


# ── Client ────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_client():
    """Initialize Gemini client. Key comes from Django settings (loaded from .env)."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Add it to your .env file.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=30000),
    )


GENERATION_MODEL = getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite")


def _generate(prompt: str, *, json_output: bool = False, max_output_tokens: int = 700):
    """Run a bounded Gemini request so responses stay quick and predictable."""
    client = get_client()
    config = types.GenerateContentConfig(
        max_output_tokens=max_output_tokens,
        temperature=0.2,
        **({"response_mime_type": "application/json"} if json_output else {}),
    )
    response = client.models.generate_content(
        model=GENERATION_MODEL,
        contents=prompt,
        config=config,
    )
    return response.text


def _extract_json(raw: str) -> list:
    """
    Safely extract a JSON array from Gemini output.
    Handles markdown fences, leading/trailing prose, and backticks.
    """
    text = raw.strip()

    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)

    # Find the first '[' .. last ']' block (the JSON array)
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return json.loads(text)


def _extract_json_object(raw: str) -> dict:
    """Extract a JSON object from model output that may contain markdown."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("AI response did not contain a JSON object.")
    result = json.loads(text[start:end + 1])
    if not isinstance(result, dict):
        raise ValueError("AI response was not a JSON object.")
    return result


# ── Subject detection ─────────────────────────────────────────────────────────

def detect_subject(text: str) -> str:
    """Detect subject from problem text using keywords."""
    text_lower = text.lower()
    if any(w in text_lower for w in [
        "equation", "solve", "calculate", "integral", "derivative",
        "algebra", "geometry", "x =", "y =", "math", "triangle",
        "angle", "area", "volume", "matrix", "polynomial"
    ]):
        return "Math"
    elif any(w in text_lower for w in [
        "atom", "molecule", "force", "energy", "biology", "chemical",
        "physics", "cell", "dna", "reaction", "velocity", "gravity",
        "photosynthesis", "mitochondria", "nucleus", "element"
    ]):
        return "Science"
    elif any(w in text_lower for w in [
        "war", "history", "century", "president", "revolution",
        "empire", "ancient", "civilization", "treaty", "battle",
        "dynasty", "colonial", "independence", "world war"
    ]):
        return "History"
    elif any(w in text_lower for w in [
        "grammar", "essay", "paragraph", "sentence", "literature",
        "poem", "novel", "author", "vocabulary", "synonym", "antonym"
    ]):
        return "English"
    else:
        return "General"


# ── Solution ──────────────────────────────────────────────────────────────────

def solve_problem(problem: str) -> str:
    """Send problem to Gemini and get step-by-step solution."""
    prompt = f"""You are an expert tutor helping a student understand a problem clearly.

Problem: {problem}

Provide a structured response with these exact sections:

UNDERSTAND:
(What is this problem asking? 1-2 sentences)

APPROACH:
(What method, formula, or concept will we use?)

STEP-BY-STEP SOLUTION:
Step 1: ...
Step 2: ...
Step 3: ...
(as many steps as needed)

FINAL ANSWER:
(State the answer clearly and directly)

KEY CONCEPT:
(One sentence — what should the student remember from this?)

Use simple, encouraging language. Show all working clearly."""

    return _generate(prompt, max_output_tokens=900)


# ── Flashcards ────────────────────────────────────────────────────────────────

def generate_flashcards(notes: str) -> list:
    """Generate flashcards from notes. Returns list of dicts."""
    prompt = f"""Create exactly 6 flashcards from the notes below.
Return ONLY valid JSON — no markdown, no backticks, no explanation.

Format:
[
  {{"question": "...", "answer": "..."}},
  {{"question": "...", "answer": "..."}}
]

Notes:
{notes}"""

    raw = _generate(prompt, json_output=True, max_output_tokens=700)
    return _extract_json(raw)


# ── Quiz ──────────────────────────────────────────────────────────────────────

def generate_quiz(topic: str, question_count: int = 5) -> list:
    """Generate the requested number of MCQ questions."""
    prompt = f"""Create exactly {question_count} multiple choice questions about: {topic}
Return ONLY valid JSON — no markdown, no backticks, no explanation.

Format:
[
  {{
    "question": "...",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct": "A) ...",
    "explanation": "..."
  }}
]"""

    raw = _generate(prompt, json_output=True, max_output_tokens=max(700, question_count * 220))
    return _extract_json(raw)


def generate_topic_study_guide(topic: str, difficulty: str = "medium") -> dict:
        """Explain an MDCAT topic and create answer-backed practice MCQs."""
        selected_difficulty = difficulty if difficulty in {"medium", "advanced"} else "medium"
        prompt = f"""You are an expert MDCAT tutor. Teach this topic accurately and clearly:

Topic: {topic}
Question difficulty: {selected_difficulty}

Return ONLY valid JSON, with no markdown fences or extra text, in this exact shape:
{{
    "topic": "...",
    "explanation": "A clear, structured explanation in 3-5 short paragraphs.",
    "key_points": ["...", "...", "..."],
    "mcqs": [
        {{
            "question": "...",
            "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
            "correct": "A) ...",
            "explanation": "Why this answer is correct and why the concept matters."
        }}
    ]
}}

    Create exactly 3 MCQs. They must test understanding and application, not trivia.
Use MDCAT-relevant terminology, formulas, mechanisms, or examples when appropriate.
Make every correct answer match one option exactly. Include a concise explanation for every answer.
"""
        result = _extract_json_object(_generate(prompt, json_output=True, max_output_tokens=1200))
        result["mcqs"] = result.get("mcqs", [])[:3]
        return result


def generate_written_test(topic: str, question_count: int = 5) -> list:
        """Generate open-ended questions with model answers for a written test."""
        prompt = f"""Create exactly {question_count} written-answer questions about: {topic}
Return ONLY valid JSON — no markdown, no backticks, no explanation.

Format:
[
    {{
        "question": "...",
        "answer": "A concise model answer with the important points...",
        "key_points": ["important point 1", "important point 2"]
    }}
]"""
        return _extract_json(_generate(prompt, json_output=True, max_output_tokens=max(700, question_count * 180)))


def generate_qa_test(topic: str, question_count: int = 5) -> list:
        """Generate question-and-answer practice cards."""
        prompt = f"""Create exactly {question_count} question-and-answer practice items about: {topic}
Return ONLY valid JSON — no markdown, no backticks, no explanation.

Format:
[
    {{
        "question": "...",
        "answer": "A clear, student-friendly answer...",
        "memory_tip": "A short memory tip..."
    }}
]"""
        return _extract_json(_generate(prompt, json_output=True, max_output_tokens=max(700, question_count * 160)))


# ── Study plan ────────────────────────────────────────────────────────────────

def generate_study_plan(topics: str, exam_date: str, hours_per_day: str) -> str:
    """Generate a personalized study schedule."""
    current_date = date.today().isoformat()
    prompt = f"""You are an expert academic coach. Create a detailed, realistic study plan.

Topics to cover: {topics}
Today's date: {current_date}
Final study/exam date selected by the student: {exam_date}
Available study hours per day: {hours_per_day}

Start the schedule from today's date ({current_date}) and finish on the student's selected final date ({exam_date}). Treat the selected date as the last day of the plan. Never start from a later date or schedule study days after the selected final date. Use calendar dates for every day and include only dates from today through the selected final date.

Create a day-by-day study schedule with:

OVERVIEW:
(Total days available, total hours, strategy summary)

DAILY SCHEDULE:
Day 1:
- Topic: ...
- Duration: ... hours
- Focus: ...

Day 2:
(continue for all days)

REVISION DAYS:
(last 2 days before exam)

TIPS:
(3 specific tips for this study plan)

Be realistic and encouraging."""

    return _generate(prompt, max_output_tokens=1400)


# ── Summary ───────────────────────────────────────────────────────────────────

def summarize_text(text: str, length: str = "medium") -> str:
    """Summarize long text into concise points."""
    length_guide = {
        "short":  "3-5 bullet points, maximum 100 words",
        "medium": "8-10 bullet points, maximum 250 words",
        "long":   "detailed summary with sections, maximum 500 words"
    }

    prompt = f"""You are an expert at summarizing academic content.

Summarize the following text. Length: {length_guide.get(length, length_guide['medium'])}

Format:
MAIN TOPIC:
(One sentence — what is this text about?)

KEY POINTS:
- Point 1
- Point 2
- Point 3
(etc.)

KEY TERMS:
(Important vocabulary or concepts)

ONE-LINE SUMMARY:
(The entire text in one sentence)

Text:
{text}"""

    return _generate(prompt, max_output_tokens=700)


# ── Formula sheet ─────────────────────────────────────────────────────────────

def generate_formula_sheet(notes: str) -> str:
    """Extract all formulas and key equations from notes."""
    prompt = f"""Extract ALL formulas, equations, and key relationships from the text below.
If no formulas exist, extract key facts, definitions, and rules instead.

Format:
SUBJECT AREA:
(What subject are these formulas from?)

FORMULAS AND EQUATIONS:
1. Name: ...
   Formula: ...
   Variables: ...
   Used for: ...

2. (continue for all formulas)

KEY RULES:
- Rule 1
- Rule 2

MEMORY TIPS:
(How to remember the most important formulas)

Notes:
{notes}"""

    return _generate(prompt, max_output_tokens=700)


# ── ELI5 ──────────────────────────────────────────────────────────────────────

def explain_simple(topic: str, age_group: str = "child") -> str:
    """Explain any topic in very simple language."""
    audience = {
        "child":  "a 10-year-old child with no prior knowledge",
        "teen":   "a 14-year-old teenager",
        "simple": "an adult with no technical background"
    }

    prompt = f"""Explain the following topic to {audience.get(age_group, audience['child'])}.

Topic: {topic}

Use ZERO technical jargon. Use everyday analogies.

Format:
SIMPLE EXPLANATION:
(2-3 paragraphs using very simple language)

ANALOGY:
(Compare it to something from everyday life)

THE KEY IDEA IN ONE SENTENCE:
(The simplest way to understand this)

REAL LIFE EXAMPLE:
(Where do we see this in the real world?)

FUN FACT:
(One interesting fact about this topic)"""

    return _generate(prompt, max_output_tokens=500)


def generate_mdcat_chat_reply(message: str, history: list, topic: str = "") -> str:
    """Answer a student as a focused MDCAT tutor."""
    recent_history = history[-4:] if isinstance(history, list) else []
    transcript = "\n".join(
        f"{item.get('role', 'user').upper()}: {str(item.get('content', ''))[:700]}"
        for item in recent_history
        if isinstance(item, dict) and item.get("content")
    )
    prompt = f"""You are StudyAI's MDCAT tutor for a Pakistani medical-entry student.
Answer the student's latest message accurately and helpfully.
Current topic: {topic or 'not specified'}

Conversation so far:
{transcript}

LATEST STUDENT MESSAGE: {message}

Rules:
- Explain concepts step by step in clear English; use a short Roman Urdu clarification when it genuinely helps.
- For Biology, Chemistry, and Physics, include the relevant mechanism, formula, units, or misconception when appropriate.
- If the student asks for a question, give a hint first unless they explicitly ask for the full answer.
- Never invent an official MDCAT rule or source. Say when something should be verified.
- Keep the response focused, with short headings or bullets when useful.
"""
    return _generate(prompt, max_output_tokens=500)
