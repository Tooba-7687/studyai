"""
AI Study Companion - Streamlit Frontend
9 Modes: Solve, Scan, Flashcards, Quiz,
         Study Planner, Summarizer, Formula Sheet, ELI5, History
"""

import os
import re

import streamlit as st
import requests


def get_api_base() -> str:
    """Resolve Django backend URL.

    Priority:
    1. Streamlit secrets (secrets.toml)  -> key: api_base
    2. Environment variable               -> API_BASE
    3. Local dev default
    """
    try:
        return st.secrets.get("api_base", "").strip() or os.getenv("API_BASE", "").strip()
    except Exception:
        return os.getenv("API_BASE", "").strip()


API_BASE = get_api_base() or "http://127.0.0.1:8000/api"
API_ROOT = API_BASE.rsplit("/api", 1)[0].rstrip("/")


def get_backend_session():
    """Keep a CSRF-enabled anonymous session for the optional Streamlit client."""
    session = st.session_state.get("studyai_backend_session")
    if session is None:
        session = requests.Session()
        response = session.get(f"{API_ROOT}/login/", timeout=10)
        response.raise_for_status()
        st.session_state["studyai_backend_session"] = session
    csrf_token = session.cookies.get("csrftoken")
    if not csrf_token:
        raise RuntimeError("The Django backend did not provide a CSRF token.")
    return session, csrf_token


# Page setup
st.set_page_config(
    page_title="StudyAI - AI Study Companion",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Inter:wght@300;400;500&display=swap');

:root {
    --ink: #07131a;
    --panel: #101f27;
    --panel-soft: #142a32;
    --line: #29434a;
    --muted: #8fa8ad;
    --text: #edf7f4;
    --teal: #40d9c2;
    --coral: #ff8b68;
    --amber: #f6c85f;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: radial-gradient(circle at 85% 0%, #16383a 0, transparent 34%), #07131a; color: var(--text); }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1120px; }

[data-testid="stSidebar"] { background: #0b1b22 !important; border-right: 1px solid var(--line) !important; }
[data-testid="stSidebar"] * { color: #b5c8c9 !important; }

.hero { text-align: center; padding: 1.8rem 0 1.4rem; border-bottom: 1px solid var(--line); margin-bottom: 1.5rem; }
.hero-badge { display: inline-block; font-family: 'Syne', sans-serif; font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--teal); background: rgba(64,217,194,0.1); border: 1px solid rgba(64,217,194,0.3); padding: 5px 14px; border-radius: 20px; margin-bottom: 0.8rem; }
.hero-title { font-family: 'Syne', sans-serif; font-size: 2.2rem; font-weight: 800; color: var(--text); margin: 0.3rem 0 0.5rem; line-height: 1.15; }
.hero-title span { color: var(--teal); }
.hero-sub { font-size: 13px; color: var(--muted); max-width: 560px; margin: 0 auto; line-height: 1.6; }



/* 1. Mode buttons: responsive grid prevents labels from wrapping awkwardly. */
div[data-testid="stRadio"] > label { display: none; }
div[data-testid="stRadio"] > div { display: grid !important; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; width: 100%; }
div[data-testid="stRadio"] > div > label { min-width: 0; min-height: 58px; background: rgba(16,31,39,0.9); border: 1px solid var(--line); border-radius: 12px; padding: 8px 10px !important; cursor: pointer; font-size: 12px !important; font-weight: 600 !important; color: #c8d9d9 !important; text-align: center; transition: all 0.2s ease; display: flex !important; align-items: center !important; justify-content: center !important; }
div[data-testid="stRadio"] > div > label p,
div[data-testid="stRadio"] > div > label span { color: #c8d9d9 !important; line-height: 1.25 !important; white-space: normal !important; overflow-wrap: anywhere; }
div[data-testid="stRadio"] > div > label:has(input:checked) { background: rgba(64,217,194,0.14); border-color: var(--teal); color: #effffc !important; box-shadow: 0 0 18px rgba(64,217,194,0.15); }
div[data-testid="stRadio"] > div > label:has(input:checked) p,
div[data-testid="stRadio"] > div > label:has(input:checked) span { color: #effffc !important; }
div[data-testid="stRadio"] > div > label:hover { border-color: var(--coral); color: #ffd0c2 !important; background: rgba(255,139,104,0.09); transform: translateY(-1px); }
            

/* 2. Text area and input */
textarea, input[type="text"] { background: var(--panel) !important; border: 1.5px solid var(--line) !important; border-radius: 12px !important; color: var(--text) !important; font-size: 14px !important; padding: 12px 14px !important; line-height: 1.6 !important; transition: all 0.2s !important; }
textarea:focus, input[type="text"]:focus { border-color: var(--teal) !important; box-shadow: 0 0 0 3px rgba(64,217,194,0.14) !important; background: var(--panel-soft) !important; }
textarea::placeholder, input[type="text"]::placeholder { color: #789398 !important; opacity: 1 !important; }

            
/* 3. Button */
div[data-testid="stButton"] > button { background: linear-gradient(135deg, var(--coral), #ffb36b) !important; color: var(--ink) !important; border: none !important; border-radius: 12px !important; padding: 13px 26px !important; font-family: 'Syne', sans-serif !important; font-size: 14px !important; font-weight: 700 !important; width: 100% !important; transition: all 0.25s !important; letter-spacing: 0.03em !important; box-shadow: 0 5px 18px rgba(255,139,104,0.2) !important; }
div[data-testid="stButton"] > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(255,139,104,0.35) !important; background: linear-gradient(135deg, #ff9f75, var(--amber)) !important; }
div[data-testid="stButton"] > button:active { transform: translateY(0px) !important; }
            
.rc { background: #0c1220; border: 1px solid #1a2235; border-radius: 14px; padding: 1.25rem 1.5rem; margin-bottom: 12px; line-height: 1.8; }
.rc.a { border-color: rgba(56,189,248,0.35); background: rgba(56,189,248,0.04); }
.rc.g { border-color: rgba(52,211,153,0.35); background: rgba(52,211,153,0.04); }
.rc.y { border-color: rgba(251,191,36,0.35); background: rgba(251,191,36,0.04); }
.rc.p { border-color: rgba(167,139,250,0.35); background: rgba(167,139,250,0.04); }

.lbl { font-family: 'Syne', sans-serif; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--teal); margin-bottom: 6px; display: block; }
.fc { background: linear-gradient(135deg, #0c1220, #0f172a); border: 1px solid #1e3a5f; border-radius: 16px; padding: 2rem; text-align: center; min-height: 150px; display: flex; align-items: center; justify-content: center; margin-bottom: 12px; }
.sb { height: 5px; background: #1a2235; border-radius: 3px; overflow: hidden; margin: 8px 0; }
.sf { height: 5px; border-radius: 3px; background: linear-gradient(90deg, #0ea5e9, #38bdf8); }
.badge { display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 10px; font-weight: 500; margin-left: 6px; }
.qo { background: #0c1220; border: 1px solid #1a2235; border-radius: 10px; padding: 11px 15px; margin-bottom: 7px; font-size: 13px; color: #a0aec0; }
.qc { border-color: #34d399 !important; background: rgba(52,211,153,0.08) !important; color: #34d399 !important; }
.plan-header { border-left: 3px solid var(--teal); padding: 4px 0 8px 14px; margin: 18px 0 14px; }
.plan-header h2 { color: var(--text); font-family: 'Syne', sans-serif; margin: 2px 0 4px; font-size: 1.35rem; }
.plan-header p { color: var(--muted); margin: 0; font-size: 13px; }
.plan-kicker, .plan-section-title span { color: var(--teal); font-family: 'Syne', sans-serif; font-size: 10px; letter-spacing: 0.14em; font-weight: 700; }
.plan-metric { background: linear-gradient(145deg, #122b32, #102027); border: 1px solid #2c5558; border-radius: 12px; padding: 13px 15px; min-height: 72px; }
.plan-metric span { display: block; color: var(--muted); font-size: 11px; margin-bottom: 5px; }
.plan-metric strong { display: block; color: var(--amber); font-family: 'Syne', sans-serif; font-size: 18px; line-height: 1.2; }
.plan-progress-track { height: 5px; background: #234047; border-radius: 4px; margin-top: 8px; overflow: hidden; }
.plan-progress-track i { display: block; height: 100%; background: var(--teal); border-radius: 4px; transition: width 0.25s ease; }
.focus-card { background: linear-gradient(135deg, rgba(64,217,194,0.16), rgba(255,139,104,0.09)); border: 1px solid rgba(64,217,194,0.45); border-radius: 14px; padding: 16px 18px; margin: 12px 0; }
.focus-card strong { display: block; color: #effffc; font-family: 'Syne', sans-serif; font-size: 18px; margin: 5px 0; }
.focus-card p { color: #b7cecb; margin: 0; font-size: 13px; }
.plan-section-title { border-bottom: 1px solid var(--line); padding: 16px 0 8px; margin: 6px 0 10px; }
.plan-section-title strong { display: block; color: var(--text); font-family: 'Syne', sans-serif; font-size: 16px; margin-top: 3px; }
[data-testid="stExpander"] { background: #0c1220 !important; border: 1px solid #1a2235 !important; border-radius: 12px !important; }
[data-testid="stExpander"] details summary p { color: #d9eeea !important; font-weight: 600 !important; }
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] li { color: #c4d6d5 !important; line-height: 1.65 !important; }
[data-testid="stMetric"] { background: #0c1220 !important; border: 1px solid #1a2235 !important; border-radius: 10px !important; padding: 12px !important; }
</style>
""", unsafe_allow_html=True)


# ── Helper Functions ──────────────────────────────────────────────────────────

def api_post(endpoint, data=None, files=None):
    """Send POST request to Django API."""
    try:
        session, csrf_token = get_backend_session()
        r = session.post(
            f"{API_BASE}/{endpoint}/",
            json=data,
            files=files,
            headers={"X-CSRFToken": csrf_token},
            timeout=30,
        )
        payload = r.json()
        if not r.ok:
            return {"error": payload.get("error", f"Request failed ({r.status_code}).")}
        return payload
    except requests.RequestException as error:
        return {"error": f"Backend request failed: {error}"}
    except ValueError:
        return {"error": "Backend returned an invalid response."}


def api_get(endpoint):
    """Send GET request to Django API."""
    try:
        session, _ = get_backend_session()
        response = session.get(f"{API_BASE}/{endpoint}/", timeout=10)
        payload = response.json()
        if not response.ok:
            return {"error": payload.get("error", f"Request failed ({response.status_code}).")}
        return payload
    except requests.RequestException as error:
        return {"error": f"Backend request failed: {error}"}
    except ValueError:
        return {"error": "Backend returned an invalid response."}


def api_delete(endpoint):
    """Send DELETE request to Django API."""
    try:
        session, csrf_token = get_backend_session()
        response = session.delete(
            f"{API_BASE}/{endpoint}/",
            headers={"X-CSRFToken": csrf_token},
            timeout=10,
        )
        payload = response.json()
        if not response.ok:
            return {"error": payload.get("error", f"Request failed ({response.status_code}).")}
        return payload
    except requests.RequestException as error:
        return {"error": f"Backend request failed: {error}"}
    except ValueError:
        return {"error": "Backend returned an invalid response."}


def subject_badge(subject):
    """Return colored badge for subject."""
    colors = {
        "Math":    "#38bdf8",
        "Science": "#34d399",
        "History": "#fbbf24",
        "English": "#a78bfa",
        "General": "#94a3b8"
    }
    color = colors.get(subject, "#94a3b8")
    return f'<span class="badge" style="background:rgba(100,116,139,0.15);color:{color};">{subject}</span>'


def show_result(color, title, title_color, content):
    """Display a styled result card."""
    st.markdown(f"""
    <div class="rc {color}">
        <div style="font-family:Syne,sans-serif;font-weight:700;color:{title_color};font-size:15px;margin-bottom:12px;">{title}</div>
        <div style="font-size:14px;line-height:1.9;color:#cbd5e1;white-space:pre-wrap;">{content}</div>
    </div>
    """, unsafe_allow_html=True)


def parse_study_plan(plan: str) -> dict:
    """Split an AI study plan into sections that are easier to scan."""
    headings = re.compile(
        r"(?im)^\s*(?:#{1,6}\s*)?(OVERVIEW|DAILY SCHEDULE|REVISION DAYS|TIPS(?: FOR SUCCESS)?)\s*:?.*$"
    )
    matches = list(headings.finditer(plan))
    sections = {"overview": "", "daily": [], "revision": "", "tips": ""}

    if not matches:
        sections["overview"] = plan.strip()
        return sections

    for index, match in enumerate(matches):
        content = plan[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(plan)].strip()
        section_name = match.group(1).lower()
        if section_name == "overview":
            sections["overview"] = content
        elif section_name == "daily schedule":
            day_matches = list(re.finditer(r"(?im)^\s*(?:#{1,6}\s*)?Day\s+(\d+)\s*:?\s*(.*?)\s*$", content))
            for day_index, day_match in enumerate(day_matches):
                day_content = content[day_match.end():day_matches[day_index + 1].start() if day_index + 1 < len(day_matches) else len(content)].strip()
                sections["daily"].append({
                    "number": day_match.group(1),
                    "title": day_match.group(2).strip(" -*"),
                    "content": day_content,
                })
        elif section_name == "revision days":
            sections["revision"] = content
        else:
            sections["tips"] = content

    return sections


def render_study_plan(plan: str):
    """Render a generated plan as a compact student dashboard."""
    sections = parse_study_plan(plan)
    overview = sections["overview"] or "Your personalized study plan is ready."
    overview_lines = [line.strip(" -*") for line in overview.splitlines() if line.strip()]
    metric_lines = [line for line in overview_lines if ":" in line][:3]
    days = sections["daily"]
    completed_days = st.session_state.study_plan_done
    completed_count = sum(completed_days.get(day["number"], False) for day in days)
    progress = int((completed_count / len(days)) * 100) if days else 0

    st.markdown('<div class="plan-header"><span class="plan-kicker">YOUR STUDY ROADMAP</span><h2>Study plan at a glance</h2><p>Turn the AI plan into small, trackable study sessions.</p></div>', unsafe_allow_html=True)
    if metric_lines:
        metric_columns = st.columns(len(metric_lines) + 1)
        for column, metric in zip(metric_columns, metric_lines):
            label, value = metric.split(":", 1)
            with column:
                st.markdown(f'<div class="plan-metric"><span>{label.strip()}</span><strong>{value.strip()}</strong></div>', unsafe_allow_html=True)
        with metric_columns[-1]:
            st.markdown(f'<div class="plan-metric plan-progress"><span>Progress</span><strong>{completed_count}/{len(days) or 0} days</strong><div class="plan-progress-track"><i style="width:{progress}%"></i></div></div>', unsafe_allow_html=True)

    if days:
        focus_options = [f'Day {day["number"]} · {day["title"] or "Study session"}' for day in days]
        focus_index = min(max(st.session_state.study_plan_focus, 0), len(focus_options) - 1)
        focus_choice = st.selectbox("Focus session", focus_options, index=focus_index, key="study_plan_focus_select")
        st.session_state.study_plan_focus = focus_options.index(focus_choice)
        focus_day = days[st.session_state.study_plan_focus]
        st.markdown(f'<div class="focus-card"><span class="plan-kicker">FOCUS MODE</span><strong>Day {focus_day["number"]}: {focus_day["title"] or "Study session"}</strong><p>Complete this session before moving to the next one.</p></div>', unsafe_allow_html=True)
        focus_done = st.checkbox("Mark focus day as complete", value=completed_days.get(focus_day["number"], False), key=f"focus_done_{focus_day["number"]}")
        completed_days[focus_day["number"]] = focus_done

        action_columns = st.columns([1, 1, 1])
        with action_columns[0]:
            st.download_button("⬇️ Download plan", data=plan, file_name="studyai-study-plan.txt", mime="text/plain", use_container_width=True)
        with action_columns[1]:
            if st.button("Reset progress", use_container_width=True):
                st.session_state.study_plan_done = {}
                st.rerun()
        with action_columns[2]:
            st.caption("Your progress is saved during this session.")

    with st.expander("Overview and strategy", expanded=True):
        st.markdown(overview)

    st.markdown('<div class="plan-section-title"><span>DAILY SCHEDULE</span><strong>Small sessions, steady progress</strong></div>', unsafe_allow_html=True)
    if days:
        for day in days:
            status = "✓" if completed_days.get(day["number"], False) else "○"
            with st.expander(f'{status}  Day {day["number"]}  ·  {day["title"] or "Study session"}', expanded=day["number"] == focus_day["number"]):
                st.markdown(day["content"])
                st.checkbox("Completed", value=completed_days.get(day["number"], False), key=f"day_done_{day["number"]}")
                completed_days[day["number"]] = st.session_state[f"day_done_{day["number"]}"]
    else:
        st.info("The plan did not include separate day headings. Review the overview above for the generated schedule.")

    if sections["revision"]:
        with st.expander("Revision days", expanded=True):
            st.markdown(sections["revision"])
    if sections["tips"]:
        with st.expander("Tips for success"):
            st.markdown(sections["tips"])


# ── Session State ─────────────────────────────────────────────────────────────

defaults = {
    "flashcards":     [],
    "flash_index":    0,
    "show_answer":    False,
    "quiz_questions": [],
    "quiz_index":     0,
    "quiz_score":     0,
    "quiz_answered":  False,
    "quiz_active":    False,
    "study_plan":     "",
    "study_plan_done": {},
    "study_plan_focus": 0,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🎓 StudyAI")
    st.markdown("9 AI-powered study tools")
    st.divider()

    # Check if Django backend is running
    try:
        r = requests.get(f"{API_BASE}/history/", timeout=3)
        if r.status_code == 200:
            st.success("✅ Backend connected")
        else:
            st.error("❌ Backend error")
    except requests.RequestException:
        st.error("❌ Start Django server first")

    st.divider()

    # Show stats
    hist = api_get("history")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Solved", hist.get("count", 0))
    with col2:
        st.metric("Cards", len(st.session_state.flashcards))

    st.divider()

    # Clear history button
    if st.button("🗑️ Clear History"):
        result = api_delete("history/clear")
        if result.get("success"):
            st.session_state.flashcards = []
            st.rerun()

    st.divider()
    st.caption("Django · Gemini · Streamlit")
    st.caption("By Tooba Nadeem")


# ── Hero Section ──────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
    <div class="hero-badge">Powered by Google Gemini · Django REST API</div>
    <div class="hero-title">Your AI <span>Study</span> Companion</div>
    <div class="hero-sub">Solve · Scan · Flashcards · Quiz · Study Planner · Summarizer · Formula Sheet · ELI5 · History</div>
</div>
""", unsafe_allow_html=True)


# ── Mode Selector ─────────────────────────────────────────────────────────────

st.markdown('<span class="lbl">Choose Mode</span>', unsafe_allow_html=True)

mode = st.radio("mode", [
    "🔍 Solve",
    "📷 Scan Image",
    "🃏 Flashcards",
    "🧠 Quiz",
    "📅 Study Planner",
    "📝 Summarizer",
    "🔢 Formula Sheet",
    "👶 Explain ELI5",
    "📚 History"
], horizontal=True, label_visibility="collapsed")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# MODE 1 — SOLVE PROBLEM
# ════════════════════════════════════════════════════════════════════════════

if mode == "🔍 Solve":

    st.markdown('<span class="lbl">Enter Your Problem</span>', unsafe_allow_html=True)

    problem = st.text_area(
        "problem",
        height=130,
        label_visibility="collapsed",
        placeholder="Type any problem...\n• Solve: 2x² + 5x - 3 = 0\n• What caused World War I?\n• Explain photosynthesis step by step\n• Write a paragraph about climate change"
    )

    if st.button("✨ Get AI Solution"):
        if not problem.strip():
            st.warning("Please enter a problem first.")
        else:
            with st.spinner("🤖 AI is solving your problem..."):
                result = api_post("solve", {"problem": problem})

            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                solution = result.get("solution", "")
                subject  = result.get("subject", "General")

                st.markdown(f"""
                <div class="rc a">
                    <div style="display:flex;align-items:center;margin-bottom:12px;">
                        <span style="font-family:Syne,sans-serif;font-weight:700;color:#fff;font-size:15px;">AI Solution</span>
                        {subject_badge(subject)}
                    </div>
                    <div style="font-size:14px;line-height:1.9;color:#cbd5e1;white-space:pre-wrap;">{solution}</div>
                </div>
                """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# MODE 2 — SCAN IMAGE
# ════════════════════════════════════════════════════════════════════════════

elif mode == "📷 Scan Image":

    st.markdown('<span class="lbl">Upload Problem Image</span>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload image",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed"
    )

    if uploaded:
        col1, col2 = st.columns([1, 1])

        with col1:
            st.image(uploaded, caption="Uploaded problem", use_container_width=True)

        with col2:
            st.markdown('<span class="lbl">Extracted Text</span>', unsafe_allow_html=True)

            with st.spinner("Reading image..."):
                ocr_result = api_post("ocr", files={"image": uploaded})

            if ocr_result.get("success"):
                extracted = ocr_result.get("text", "")
                edited = st.text_area(
                    "Edit if needed",
                    value=extracted,
                    height=160,
                    label_visibility="collapsed"
                )
                st.success(f"✅ {ocr_result.get('char_count', 0)} characters extracted")
            else:
                st.warning("Could not extract text. Type manually:")
                edited = st.text_area(
                    "Type problem manually",
                    height=160,
                    label_visibility="collapsed",
                    placeholder="Type the problem from the image..."
                )

        if st.button("✨ Solve This Problem"):
            if not edited.strip():
                st.warning("No text to solve.")
            else:
                with st.spinner("🤖 Solving..."):
                    result = api_post("solve", {"problem": edited})

                if "error" in result:
                    st.error(result["error"])
                else:
                    show_result(
                        "a",
                        f'AI Solution {subject_badge(result.get("subject", "General"))}',
                        "#fff",
                        result.get("solution", "")
                    )
    else:
        st.markdown("""
        <div class="rc" style="text-align:center;padding:3rem;">
            <div style="font-size:3rem;margin-bottom:1rem;">📸</div>
            <div style="font-size:15px;color:#64748b;">Upload a photo of your homework problem</div>
            <div style="font-size:12px;color:#334155;margin-top:8px;">Supports JPG, PNG, WebP</div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# MODE 3 — FLASHCARDS
# ════════════════════════════════════════════════════════════════════════════

elif mode == "🃏 Flashcards":

    tab1, tab2 = st.tabs(["📝 Generate New", "📖 Study Cards"])

    # ── Tab 1: Generate flashcards from notes ────────────────────────────────
    with tab1:
        col1, col2 = st.columns([3, 1])
        with col2:
            topic = st.text_input(
                "Topic",
                placeholder="e.g. Biology",
                label_visibility="collapsed"
            )
        with col1:
            notes = st.text_area(
                "notes",
                height=160,
                label_visibility="collapsed",
                placeholder="Paste your notes or textbook content here..."
            )

        if st.button("🃏 Generate Flashcards"):
            if not notes.strip():
                st.warning("Please paste some notes first.")
            else:
                with st.spinner("Creating flashcards..."):
                    result = api_post("flashcards", {
                        "notes": notes,
                        "topic": topic or "General"
                    })

                if "error" in result:
                    st.error(result["error"])
                else:
                    st.session_state.flashcards  = result.get("flashcards", [])
                    st.session_state.flash_index = 0
                    st.session_state.show_answer = False
                    st.success(f"✅ {result.get('count', 0)} flashcards created! Go to Study Cards tab.")

    # ── Tab 2: Study the flashcards ───────────────────────────────────────────
    with tab2:
        if not st.session_state.flashcards:
            st.markdown("""
            <div class="rc" style="text-align:center;padding:2.5rem;">
                <div style="font-size:3rem;">🃏</div>
                <div style="color:#64748b;margin-top:12px;">No flashcards yet — generate from your notes!</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            cards = st.session_state.flashcards
            idx   = st.session_state.flash_index % len(cards)
            card  = cards[idx]
            pct   = int((idx / len(cards)) * 100)

            # Progress bar
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span class="lbl">Card {idx+1} of {len(cards)}</span>
                <span style="font-size:12px;color:#38bdf8;">{pct}% complete</span>
            </div>
            <div class="sb"><div class="sf" style="width:{pct}%"></div></div>
            """, unsafe_allow_html=True)

            # Show question or answer
            if not st.session_state.show_answer:
                st.markdown(f"""
                <div class="fc">
                    <div>
                        <div style="font-size:10px;letter-spacing:0.15em;color:#38bdf8;margin-bottom:12px;font-family:Syne,sans-serif;">QUESTION</div>
                        <div style="font-size:17px;font-weight:600;color:#fff;line-height:1.5;">{card['question']}</div>
                        <div style="font-size:11px;color:#334155;margin-top:14px;">Click Show Answer ↓</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="fc" style="border-color:rgba(56,189,248,0.4);">
                    <div>
                        <div style="font-size:10px;letter-spacing:0.15em;color:#34d399;margin-bottom:12px;font-family:Syne,sans-serif;">ANSWER</div>
                        <div style="font-size:15px;color:#38bdf8;line-height:1.6;">{card['answer']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Navigation buttons
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("👁️ Show Answer" if not st.session_state.show_answer else "🙈 Hide"):
                    st.session_state.show_answer = not st.session_state.show_answer
                    st.rerun()
            with c2:
                if st.button("⬅️ Previous"):
                    st.session_state.flash_index = (idx - 1) % len(cards)
                    st.session_state.show_answer = False
                    st.rerun()
            with c3:
                if st.button("➡️ Next Card"):
                    st.session_state.flash_index = (idx + 1) % len(cards)
                    st.session_state.show_answer = False
                    st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# MODE 4 — QUIZ
# ════════════════════════════════════════════════════════════════════════════

elif mode == "🧠 Quiz":

    # ── Start screen ──────────────────────────────────────────────────────────
    if not st.session_state.quiz_active:

        st.markdown('<span class="lbl">Enter Quiz Topic</span>', unsafe_allow_html=True)

        topic = st.text_input(
            "topic",
            placeholder="e.g. Photosynthesis, World War II, Algebra, Newton's Laws...",
            label_visibility="collapsed"
        )

        question_count = st.number_input(
            "Number of questions",
            min_value=1,
            max_value=20,
            value=5,
            step=1
        )

        if st.button("🧠 Start Quiz"):
            if not topic.strip():
                st.warning("Please enter a topic first.")
            else:
                with st.spinner("Generating quiz questions..."):
                    result = api_post("quiz", {"topic": topic, "count": int(question_count)})

                if "error" in result:
                    st.error(result["error"])
                else:
                    st.session_state.quiz_questions = result.get("questions", [])
                    st.session_state.quiz_index     = 0
                    st.session_state.quiz_score     = 0
                    st.session_state.quiz_answered  = False
                    st.session_state.quiz_active    = True
                    st.rerun()

    # ── Quiz in progress ──────────────────────────────────────────────────────
    else:
        questions = st.session_state.quiz_questions
        idx       = st.session_state.quiz_index

        # ── Results screen ────────────────────────────────────────────────────
        if idx >= len(questions):
            score = st.session_state.quiz_score
            total = len(questions)
            pct   = int((score / total) * 100)
            emoji = "🏆" if pct >= 80 else "📚" if pct >= 60 else "💪"
            msg   = "Excellent! You mastered this topic." if pct >= 80 else "Good effort! Review what you missed." if pct >= 60 else "Keep studying! Practice makes perfect."

            st.markdown(f"""
            <div class="rc a" style="text-align:center;padding:2rem;">
                <div style="font-size:3rem;">{emoji}</div>
                <div style="font-family:Syne,sans-serif;font-size:1.8rem;font-weight:800;color:#fff;margin-top:12px;">{score}/{total} Correct</div>
                <div style="font-size:2rem;color:#38bdf8;font-weight:700;">{pct}%</div>
                <div style="font-size:13px;color:#64748b;margin-top:6px;">{msg}</div>
                <div class="sb" style="margin-top:14px;">
                    <div class="sf" style="width:{pct}%"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔄 Take Another Quiz"):
                st.session_state.quiz_active    = False
                st.session_state.quiz_questions = []
                st.rerun()

        # ── Question screen ───────────────────────────────────────────────────
        else:
            q   = questions[idx]
            pct = int((idx / len(questions)) * 100)

            # Progress
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span class="lbl">Question {idx+1} of {len(questions)}</span>
                <span style="font-size:12px;color:#38bdf8;">Score: {st.session_state.quiz_score}/{idx}</span>
            </div>
            <div class="sb" style="margin-bottom:14px;">
                <div class="sf" style="width:{pct}%"></div>
            </div>
            """, unsafe_allow_html=True)

            # Question card
            st.markdown(f"""
            <div class="rc a">
                <div style="font-size:16px;font-weight:600;color:#fff;line-height:1.5;">{q['question']}</div>
            </div>
            """, unsafe_allow_html=True)

            # Answer options
            if not st.session_state.quiz_answered:
                for opt in q["options"]:
                    if st.button(opt, key=f"q{idx}_{opt}"):
                        st.session_state.quiz_answered = True
                        if opt == q["correct"]:
                            st.session_state.quiz_score += 1
                            st.success(f"✅ Correct! {q.get('explanation', '')}")
                        else:
                            st.error(f"❌ Wrong. Correct answer: {q['correct']}\n\n{q.get('explanation', '')}")
                        st.rerun()
            else:
                # Show correct/wrong after answering
                for opt in q["options"]:
                    cls = "qc" if opt == q["correct"] else "qo"
                    st.markdown(f'<div class="{cls}" style="padding:11px 15px;border-radius:10px;margin-bottom:7px;">{"✅ " if opt == q["correct"] else ""}{opt}</div>', unsafe_allow_html=True)

                # Show explanation
                st.markdown(f"""
                <div class="rc" style="margin-top:8px;">
                    <span style="color:#38bdf8;font-weight:600;">💡 Explanation: </span>
                    <span style="color:#94a3b8;">{q.get('explanation', '')}</span>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Next Question →"):
                    st.session_state.quiz_index   += 1
                    st.session_state.quiz_answered = False
                    st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# MODE 5 — STUDY PLANNER
# ════════════════════════════════════════════════════════════════════════════

elif mode == "📅 Study Planner":

    st.markdown('<span class="lbl">Create Your Personalized Study Plan</span>', unsafe_allow_html=True)

    # Three columns — topics, exam date, hours per day
    col1, col2, col3 = st.columns([3, 1.5, 1])

    with col1:
        topics = st.text_area(
            "topics",
            height=100,
            label_visibility="collapsed",
            placeholder="Topics to study...\ne.g. Calculus, Thermodynamics, Organic Chemistry, World History"
        )

    with col2:
        exam_date = st.date_input(
            "Exam date",
            label_visibility="collapsed"
        )

    with col3:
        hours = st.selectbox(
            "Hours per day",
            ["1", "2", "3", "4", "5", "6"],
            index=1,
            label_visibility="collapsed"
        )

    if st.button("📅 Generate Study Plan"):
        if not topics.strip():
            st.warning("Please enter topics to study first.")
        else:
            with st.spinner("🤖 Creating your personalized study plan..."):
                result = api_post("study-plan", {
                    "topics":        topics,
                    "exam_date":     str(exam_date),
                    "hours_per_day": hours
                })

            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                st.session_state.study_plan = result.get("plan", "")
                st.session_state.study_plan_done = {}
                st.session_state.study_plan_focus = 0

    if st.session_state.study_plan:
        render_study_plan(st.session_state.study_plan)

# ════════════════════════════════════════════════════════════════════════════
# MODE 6 — SUMMARIZER
# ════════════════════════════════════════════════════════════════════════════

elif mode == "📝 Summarizer":

    st.markdown('<span class="lbl">Paste Text to Summarize</span>', unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])

    with col2:
        length = st.selectbox(
            "Summary length",
            ["short", "medium", "long"],
            index=1,
            label_visibility="collapsed"
        )

    with col1:
        text = st.text_area(
            "text",
            height=180,
            label_visibility="collapsed",
            placeholder="Paste lecture notes, textbook chapters, articles...\n\nAI will extract the key points into a clean summary."
        )

    if st.button("📝 Summarize"):
        if not text.strip():
            st.warning("Please paste some text first.")
        else:
            with st.spinner("🤖 Summarizing..."):
                result = api_post("summarize", {
                    "text":   text,
                    "length": length
                })

            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                show_result(
                    "y",
                    f"📝 Summary ({length})",
                    "#fbbf24",
                    result.get("summary", "")
                )


# ════════════════════════════════════════════════════════════════════════════
# MODE 7 — FORMULA SHEET
# ════════════════════════════════════════════════════════════════════════════

elif mode == "🔢 Formula Sheet":

    st.markdown('<span class="lbl">Paste Your Notes</span>', unsafe_allow_html=True)

    notes = st.text_area(
        "fnotes",
        height=180,
        label_visibility="collapsed",
        placeholder="Paste your notes or textbook content...\n\nAI will extract ALL formulas, equations, and key rules into a clean cheat sheet.\nWorks for Math, Physics, Chemistry, Economics — any subject!"
    )

    if st.button("🔢 Generate Formula Sheet"):
        if not notes.strip():
            st.warning("Please paste some notes first.")
        else:
            with st.spinner("🤖 Extracting formulas..."):
                result = api_post("formulas", {"notes": notes})

            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                show_result(
                    "a",
                    "🔢 Formula Sheet",
                    "#38bdf8",
                    result.get("formulas", "")
                )


# ════════════════════════════════════════════════════════════════════════════
# MODE 8 — EXPLAIN LIKE I'M 5
# ════════════════════════════════════════════════════════════════════════════

elif mode == "👶 Explain ELI5":

    st.markdown('<span class="lbl">What do you want explained simply?</span>', unsafe_allow_html=True)

    col1, col2 = st.columns([4, 1])

    with col2:
        audience = st.selectbox(
            "Explain to",
            ["child", "teen", "simple"],
            format_func=lambda x: {
                "child":  "10-yr-old",
                "teen":   "Teenager",
                "simple": "Non-technical"
            }[x],
            label_visibility="collapsed"
        )

    with col1:
        topic = st.text_input(
            "eli5topic",
            placeholder="e.g. How does the internet work? What is machine learning? What is DNA?",
            label_visibility="collapsed"
        )

    if st.button("👶 Explain Simply"):
        if not topic.strip():
            st.warning("Please enter a topic first.")
        else:
            with st.spinner("🤖 Making it super simple..."):
                result = api_post("explain", {
                    "topic":     topic,
                    "age_group": audience
                })

            if "error" in result:
                st.error(f"Error: {result['error']}")
            else:
                label = {
                    "child":  "10-year-old",
                    "teen":   "Teenager",
                    "simple": "Non-technical adult"
                }[audience]

                show_result(
                    "p",
                    f"👶 Explained for a {label}",
                    "#a78bfa",
                    result.get("explanation", "")
                )


# ════════════════════════════════════════════════════════════════════════════
# MODE 9 — HISTORY
# ════════════════════════════════════════════════════════════════════════════

elif mode == "📚 History":

    result = api_get("history")

    if "error" in result:
        st.error(f"Could not load history: {result['error']}")

    elif result.get("count", 0) == 0:
        st.markdown("""
        <div class="rc" style="text-align:center;padding:3rem;">
            <div style="font-size:3rem;">📚</div>
            <div style="color:#64748b;margin-top:12px;">No problems solved yet — start with Solve mode!</div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown(f'<span class="lbl">{result["count"]} problems solved</span>', unsafe_allow_html=True)

        for item in result["history"]:
            with st.expander(f"[{item['subject']}] {item['problem'][:80]}... — {item['created_at']}"):
                st.markdown(f"**Problem:** {item['problem']}")
                st.divider()
                st.markdown(f"**Solution:**\n\n{item['solution']}")
