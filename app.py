import streamlit as st
from openai import OpenAI
import json
import io

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Job Fit Analyzer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { padding: 2rem 3rem; }
    .stTextArea textarea { font-size: 14px; }
    .metric-card {
        background: #f8f9ff;
        border: 1px solid #e0e4ff;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .score-circle { font-size: 2.5rem; font-weight: 700; line-height: 1; }
    .score-label  { font-size: 0.8rem; color: #666; margin-top: 4px; }
    .skill-tag {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 13px;
        margin: 3px;
    }
    .tag-have    { background: #d1fae5; color: #065f46; }
    .tag-missing { background: #fee2e2; color: #991b1b; }
    .tag-partial { background: #fef3c7; color: #92400e; }
    .section-header {
        font-size: 1rem;
        font-weight: 600;
        color: #1e1b4b;
        margin: 1.2rem 0 0.5rem;
        padding-bottom: 4px;
        border-bottom: 2px solid #e0e4ff;
    }
    div[data-testid="stProgress"] > div { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)


# ── OpenAI client ──────────────────────────────────────────────────────────────
OPENAI_API_KEY = "YOUR_OPENAI_KEY_HERE"   

@st.cache_resource
def get_client():
    import os
    return OpenAI(api_key="YOUR_OPENAI_KEY_HERE")



# ── PDF text extractor ─────────────────────────────────────────────────────────
def extract_pdf_text(uploaded_file) -> str:
    file_bytes = uploaded_file.read()
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts).strip()


# ── AI analysis ────────────────────────────────────────────────────────────────
def analyze_fit(resume_text: str, jd_text: str) -> dict:
    client = get_client()

    system_prompt = """You are an expert technical recruiter with 15 years of experience.
Analyze the resume against the job description with precision and honesty.

Respond with ONLY valid JSON — no extra text, no markdown fences.

Use this exact structure:
{
  "overall_score": <integer 0-100>,
  "verdict": "<Strong Match | Good Match | Partial Match | Weak Match>",
  "verdict_reason": "<2 sentences>",
  "skills": {
    "matched": ["skill1", "skill2"],
    "missing": ["skill1", "skill2"],
    "partial": ["skill1", "skill2"]
  },
  "experience_match": { "score": <0-100>, "comment": "<1-2 sentences>" },
  "education_match":  { "score": <0-100>, "comment": "<1-2 sentences>" },
  "strengths":  ["<point 1>", "<point 2>", "<point 3>"],
  "gaps":       ["<gap 1>",   "<gap 2>",   "<gap 3>"],
  "resume_improvements": [
    {"point": "<what to change>", "reason": "<why it matters>"},
    {"point": "<what to change>", "reason": "<why it matters>"},
    {"point": "<what to change>", "reason": "<why it matters>"}
  ],
  "interview_prep": ["<topic 1>", "<topic 2>", "<topic 3>"],
  "one_liner": "<honest one-line recruiter verdict>"
}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1500,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": f"RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{jd_text}\n\nReturn ONLY the JSON."}
        ]
    )
    return json.loads(response.choices[0].message.content.strip())


# ── Color helpers ──────────────────────────────────────────────────────────────
def score_color(s):
    return "#059669" if s >= 75 else "#d97706" if s >= 50 else "#dc2626"

def verdict_color(v):
    return {"Strong Match":"#059669","Good Match":"#0284c7",
            "Partial Match":"#d97706","Weak Match":"#dc2626"}.get(v,"#6b7280")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🎯 AI Job Fit Analyzer")
st.markdown("Upload your resume and paste a job description — get an instant match score, skill gap analysis, and resume tips.")
st.markdown("---")

# pdfplumber check
if not PDF_SUPPORT:
    st.error("pdfplumber not installed. Run:  `pip install pdfplumber`  then restart the app.")
    st.stop()

# ── Input section ──────────────────────────────────────────────────────────────
col1, col2 = st.columns(2, gap="large")

resume_text = ""   # will be filled below

with col1:
    st.markdown("**📄 Your Resume**")

    mode = st.radio(
        "input_mode",
        ["📤 Upload PDF", "📋 Paste Text"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if mode == "📤 Upload PDF":
        pdf_file = st.file_uploader(
            "upload_resume",
            type=["pdf"],
            label_visibility="collapsed"
        )
        if pdf_file is not None:
            with st.spinner("Reading PDF..."):
                try:
                    resume_text = extract_pdf_text(pdf_file)
                    if resume_text:
                        st.success(f"✅ Resume loaded — {len(resume_text.split())} words extracted")
                        with st.expander("Preview extracted text"):
                            st.text(resume_text[:600] + "...")
                    else:
                        st.error("No text found in PDF. It may be a scanned image — please use 'Paste Text' instead.")
                except Exception as e:
                    st.error(f"Could not read PDF: {e}")
    else:
        resume_text = st.text_area(
            "paste_resume",
            placeholder="Paste your full resume text here...",
            height=340,
            label_visibility="collapsed"
        )

with col2:
    st.markdown("**📝 Job Description**")
    jd_text = st.text_area(
        "paste_jd",
        placeholder="Paste the full job description here...",
        height=380,
        label_visibility="collapsed"
    )

st.markdown("")
btn = st.button("🔍 Analyze My Fit", use_container_width=True, type="primary")

# ── Run analysis ───────────────────────────────────────────────────────────────
if btn:
    if not resume_text or not resume_text.strip():
        st.warning("Please upload your resume PDF or paste your resume text.")
        st.stop()
    if not jd_text.strip():
        st.warning("Please paste the job description.")
        st.stop()

    with st.spinner("Analyzing... this takes ~10 seconds"):
        try:
            result = analyze_fit(resume_text, jd_text)
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    # ── Results ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Your Results")

    # Score cards
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (result["overall_score"],               "Overall Match"),
        (result["experience_match"]["score"],    "Experience Match"),
        (result["education_match"]["score"],     "Education Match"),
    ]
    with c1:
        sc = score_color(result["overall_score"])
        st.markdown(f'<div class="metric-card"><div class="score-circle" style="color:{sc}">{result["overall_score"]}%</div><div class="score-label">Overall Match</div></div>', unsafe_allow_html=True)
    with c2:
        vc = verdict_color(result["verdict"])
        st.markdown(f'<div class="metric-card"><div class="score-circle" style="color:{vc};font-size:1.3rem">{result["verdict"]}</div><div class="score-label">Verdict</div></div>', unsafe_allow_html=True)
    with c3:
        ec = score_color(result["experience_match"]["score"])
        st.markdown(f'<div class="metric-card"><div class="score-circle" style="color:{ec}">{result["experience_match"]["score"]}%</div><div class="score-label">Experience Match</div></div>', unsafe_allow_html=True)
    with c4:
        edc = score_color(result["education_match"]["score"])
        st.markdown(f'<div class="metric-card"><div class="score-circle" style="color:{edc}">{result["education_match"]["score"]}%</div><div class="score-label">Education Match</div></div>', unsafe_allow_html=True)

    st.markdown("")
    st.info(f"**Recruiter's take:** {result['one_liner']}")
    st.caption(result["verdict_reason"])
    st.markdown("")

    # Two-column breakdown
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown('<div class="section-header">🛠 Skills Breakdown</div>', unsafe_allow_html=True)
        matched = result["skills"].get("matched", [])
        missing = result["skills"].get("missing", [])
        partial = result["skills"].get("partial", [])
        total   = len(matched) + len(missing) + len(partial)
        pct     = int(len(matched) / total * 100) if total else 0
        st.progress(pct / 100, text=f"{len(matched)} of {total} skills matched")
        st.markdown("")
        if matched:
            st.markdown("**You have:**")
            st.markdown("".join(f'<span class="skill-tag tag-have">✓ {s}</span>' for s in matched), unsafe_allow_html=True)
        if partial:
            st.markdown("**Partial:**")
            st.markdown("".join(f'<span class="skill-tag tag-partial">~ {s}</span>' for s in partial), unsafe_allow_html=True)
        if missing:
            st.markdown("**You need:**")
            st.markdown("".join(f'<span class="skill-tag tag-missing">✗ {s}</span>' for s in missing), unsafe_allow_html=True)

        st.markdown("")
        st.markdown('<div class="section-header">📋 Experience & Education</div>', unsafe_allow_html=True)
        st.markdown(f"**Experience:** {result['experience_match']['comment']}")
        st.markdown(f"**Education:**  {result['education_match']['comment']}")

    with right:
        st.markdown('<div class="section-header">✅ Strengths</div>', unsafe_allow_html=True)
        for s in result.get("strengths", []):
            st.markdown(f"- {s}")

        st.markdown('<div class="section-header">⚠️ Key Gaps</div>', unsafe_allow_html=True)
        for g in result.get("gaps", []):
            st.markdown(f"- {g}")

        st.markdown('<div class="section-header">🎤 Interview Prep Topics</div>', unsafe_allow_html=True)
        for t in result.get("interview_prep", []):
            st.markdown(f"- {t}")

    st.markdown("")
    st.markdown('<div class="section-header">✏️ Resume Improvement Suggestions</div>', unsafe_allow_html=True)
    for i, tip in enumerate(result.get("resume_improvements", []), 1):
        with st.expander(f"Suggestion {i}: {tip['point']}"):
            st.markdown(f"**Why it matters:** {tip['reason']}")

    st.markdown("")
    st.success("✅ Analysis complete!")
    st.markdown("---------------------------------------------------------------------")
    
