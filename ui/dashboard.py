import streamlit as st
import sys, os, random, math
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mentor import review_code
from memory.store import save_session, get_past_mistakes, get_weakness_summary

# ── helpers ──────────────────────────────────────────────────────
def extract_weak_spot(text):
    for line in text.lower().split("\n"):
        if "weak spot" in line:
            parts = line.split(":")
            if len(parts) > 1:
                return parts[1].strip()[:40].rstrip(")")
    return "general"

def score_from_review(text):
    """Rough quality score 0-100 based on issue count in review."""
    issues = text.lower().count("issue") + text.lower().count("problem") + text.lower().count("error")
    return max(30, min(95, 95 - (issues * 8)))

def score_ring_svg(score):
    r = 44
    circ = 2 * math.pi * r
    offset = circ * (1 - score / 100)
    color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 55 else "#ef4444"
    return f"""
    <svg width="120" height="120" viewBox="0 0 120 120" style="display:block;margin:0 auto">
      <circle cx="60" cy="60" r="{r}" fill="none" stroke="#e4e1d9" stroke-width="7"/>
      <circle cx="60" cy="60" r="{r}" fill="none" stroke="{color}" stroke-width="7"
        stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"
        stroke-linecap="round" transform="rotate(-90 60 60)"
        style="transition:stroke-dashoffset 1s ease"/>
      <text x="60" y="55" text-anchor="middle"
        font-family="DM Mono,monospace" font-size="24" font-weight="500" fill="#1a1916">{score}</text>
      <text x="60" y="72" text-anchor="middle"
        font-family="DM Sans,sans-serif" font-size="10" fill="#9c9890">/ 100</text>
    </svg>"""

FACTS = [
    "Llama 3.1 8B was trained on 15 trillion tokens.",
    "ChromaDB finds meaning, not just matching words.",
    "RAG was invented at Meta in 2020.",
    "all-MiniLM compresses any sentence into 384 numbers.",
    "Running locally = zero API cost, zero privacy risk.",
    "Cosine similarity: 'similar' means geometrically close.",
    "LangChain's pipe (|) is inspired by Unix shell pipes.",
    "Llama 3.1 beats GPT-3.5 on most benchmarks.",
    "'Attention Is All You Need' (2017) changed everything.",
    "Your ChromaDB stores the semantic DNA of your mistakes.",
]

REVIEW_MODES = {
    "🔥 Roast me":      "Be brutally honest. Call out every flaw aggressively but constructively.",
    "🎓 Mentor":        "Be warm and educational. Explain the *why* behind every suggestion.",
    "⚡ Speed":         "Ultra-concise. Bullet points only. 5 lines max.",
    "🔒 Security":      "Focus only on security vulnerabilities and unsafe patterns.",
    "📐 Architecture":  "Focus on design patterns, SOLID principles, structural issues.",
    "🧪 Tests":         "Suggest unit tests and point out untestable code.",
}

LANG_EXT = {
    "Python":"py","JavaScript":"js","TypeScript":"ts",
    "Java":"java","C++":"cpp","Go":"go","Rust":"rs","Swift":"swift",
}
LANG_COL = {
    "Python":"#3b82f6","JavaScript":"#f59e0b","TypeScript":"#3b82f6",
    "Java":"#ef4444","C++":"#8b5cf6","Go":"#06b6d4","Rust":"#f97316","Swift":"#f43f5e",
}

# ── session state ─────────────────────────────────────────────────
for k,v in [("fact_idx",0),("mode","🔥 Roast me"),("score",None),
             ("review_result",None),("session_log",[])]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── page config ───────────────────────────────────────────────────
st.set_page_config(page_title="AI Coding Mentor",page_icon="🧠",
                   layout="wide",initial_sidebar_state="collapsed")

# ── CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&family=DM+Mono:wght@400;500&display=swap');

:root {
  --bg:#f5f4f1; --surface:#faf9f7; --surface2:#f0eee9;
  --border:#e4e1d9; --border2:#d4d0c8;
  --text:#1a1916; --text2:#6b6860; --text3:#9c9890;
  --accent:#7c3aed; --accent-light:#ede9fe;
  --shadow-sm:0 1px 3px rgba(26,25,22,.06),0 2px 8px rgba(26,25,22,.04);
  --shadow-md:0 2px 12px rgba(26,25,22,.08),0 8px 32px rgba(26,25,22,.06);
  --shadow-lg:0 4px 24px rgba(26,25,22,.1),0 16px 48px rgba(26,25,22,.08);
}

html,body,[class*="css"] { font-family:'DM Sans',sans-serif !important; }
.stApp { background:var(--bg) !important; }
.block-container { padding:0 !important; max-width:100% !important; }
section[data-testid="stSidebar"] { display:none }
#MainMenu,footer,header { visibility:hidden }

/* ── text area → editor chrome ── */
div[data-testid="stTextArea"] { margin:0 !important; }
div[data-testid="stTextArea"] label { display:none !important; }
.stTextArea textarea {
  background:var(--surface) !important;
  border:none !important;
  border-radius:0 0 14px 14px !important;
  color:var(--text) !important;
  font-family:'DM Mono',monospace !important;
  font-size:13px !important;
  line-height:1.8 !important;
  padding:16px 18px !important;
  box-shadow:none !important;
  caret-color:var(--accent) !important;
  resize:vertical !important;
}
.stTextArea textarea:focus {
  box-shadow:none !important;
  outline:none !important;
  border:none !important;
}
.stTextArea textarea::placeholder { color:var(--text3) !important; }

/* ── run button ── */
.stButton > button {
  width:100% !important;
  background:var(--accent) !important;
  color:#fff !important;
  border:none !important;
  border-radius:10px !important;
  padding:12px 20px !important;
  font-family:'DM Sans',sans-serif !important;
  font-size:14px !important;
  font-weight:500 !important;
  letter-spacing:-.01em !important;
  box-shadow:0 2px 8px rgba(124,58,237,.25),0 1px 2px rgba(124,58,237,.15) !important;
  transition:all .18s ease !important;
}
.stButton > button:hover {
  transform:translateY(-1px) !important;
  box-shadow:0 4px 16px rgba(124,58,237,.3),0 2px 4px rgba(124,58,237,.2) !important;
  background:var(--accent) !important;
}
.stButton > button:active { transform:translateY(0) !important; }

/* ── select box ── */
.stSelectbox > div > div {
  background:var(--surface) !important;
  border:1px solid var(--border) !important;
  border-radius:10px !important;
  color:var(--text) !important;
  font-family:'DM Sans',sans-serif !important;
  box-shadow:var(--shadow-sm) !important;
}

/* ── radio (mode selector) ── */
.stRadio > div { flex-direction:row !important; flex-wrap:wrap !important; gap:6px !important; }
.stRadio > div > label {
  background:var(--surface) !important;
  border:1px solid var(--border) !important;
  border-radius:10px !important;
  padding:8px 14px !important;
  font-size:12px !important;
  color:var(--text2) !important;
  cursor:pointer !important;
  transition:all .15s !important;
  box-shadow:var(--shadow-sm) !important;
}
.stRadio > div > label:has(input:checked) {
  background:var(--accent-light) !important;
  border-color:rgba(124,58,237,.3) !important;
  color:var(--accent) !important;
}
.stRadio > div > label > div:first-child { display:none !important; }
.stRadio [data-testid="stMarkdownContainer"] p { font-size:12px !important; margin:0 !important; }

/* ── expander ── */
.streamlit-expanderHeader {
  background:var(--surface2) !important;
  border:1px solid var(--border) !important;
  border-radius:10px !important;
  font-family:'DM Mono',monospace !important;
  font-size:12px !important;
  color:var(--text2) !important;
}

/* ── spinner ── */
.stSpinner > div { border-top-color:var(--accent) !important; }

/* ── shared card shell ── */
.card {
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:14px;
  box-shadow:var(--shadow-md);
  overflow:hidden;
}
.sec-lbl {
  font-size:10px;font-weight:500;letter-spacing:.1em;
  text-transform:uppercase;color:var(--text3);
  margin:18px 0 10px;font-family:'DM Mono',monospace;
  display:flex;align-items:center;gap:8px;
}
.sec-lbl::after { content:'';flex:1;height:1px;background:var(--border); }

.stat-pill {
  background:var(--surface2);border:1px solid var(--border);
  border-radius:99px;padding:5px 13px;
  display:inline-flex;align-items:center;gap:7px;
  font-size:12px;color:var(--text2);
}
.stat-dot { width:6px;height:6px;border-radius:50%;display:inline-block; }
.stat-val { font-family:'DM Mono',monospace;font-size:11px;font-weight:500;color:var(--text); }

.heat-item { margin-bottom:14px; }
.heat-row  { display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px; }
.heat-name { font-size:12px;color:var(--text2); }
.heat-cnt  { font-size:11px;font-family:'DM Mono',monospace;color:var(--text3); }
.heat-bg   { height:4px;background:var(--surface2);border-radius:99px;overflow:hidden;border:1px solid var(--border); }
.heat-fill { height:100%;border-radius:99px;background:var(--accent); }

.sess-row {
  display:flex;align-items:center;gap:8px;padding:7px 0;
  border-bottom:1px solid var(--border);font-size:12px;
}
.sess-row:last-child { border-bottom:none; }
.lang-badge {
  padding:2px 7px;border-radius:5px;font-size:10px;font-weight:500;
  font-family:'DM Mono',monospace;
  background:var(--accent-light);color:var(--accent);
}
.sess-spot { color:var(--text2);flex:1; }
.sess-time { font-size:10px;font-family:'DM Mono',monospace;color:var(--text3); }

.review-card {
  background:var(--surface);border:1px solid var(--border);
  border-radius:14px;padding:28px;margin-top:20px;
  box-shadow:var(--shadow-lg);
}
.review-card p,.review-card li { color:var(--text) !important;font-size:14px !important; }
.review-card strong { color:var(--accent) !important; }
.review-card code {
  background:var(--accent-light) !important;color:var(--accent) !important;
  padding:1px 6px;border-radius:4px;font-family:'DM Mono',monospace !important;
}

.foot-bar {
  display:grid;grid-template-columns:repeat(4,1fr);
  border-top:1px solid var(--border);background:var(--surface2);
  margin-top:24px;
}
.foot-cell {
  padding:12px 20px;border-right:1px solid var(--border);
  display:flex;align-items:center;gap:9px;
}
.foot-cell:last-child { border-right:none; }
.foot-name { font-size:12px;font-weight:500;color:var(--text); }
.foot-type { font-size:10px;font-family:'DM Mono',monospace;color:var(--text3); }

.fact-bar {
  display:flex;align-items:center;gap:12px;padding:10px 28px;
  background:var(--surface2);border-bottom:1px solid var(--border);
}
.fact-badge {
  font-size:9px;font-weight:500;letter-spacing:.08em;
  background:var(--accent);color:#fff;
  padding:3px 10px;border-radius:99px;white-space:nowrap;
  font-family:'DM Mono',monospace;
}
.fact-text { font-size:12px;color:var(--text2);font-style:italic;flex:1; }
</style>
""", unsafe_allow_html=True)

# ── DATA ──────────────────────────────────────────────────────────
summary       = get_weakness_summary()
total_sess    = sum(summary.values())
unique_spots  = len(summary)
sorted_heat   = sorted(summary.items(), key=lambda x: -x[1])

# ── HEADER ────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
  padding:18px 32px;border-bottom:1px solid var(--border);
  background:var(--surface)">
  <div style="display:flex;align-items:center;gap:12px">
    <div style="width:38px;height:38px;border-radius:10px;background:var(--accent);
      display:flex;align-items:center;justify-content:center;font-size:20px;
      box-shadow:0 2px 8px rgba(124,58,237,.3)">🧠</div>
    <div>
      <div style="font-size:17px;font-weight:500;color:var(--text);letter-spacing:-.02em">
        AI Coding Mentor</div>
      <div style="font-size:11px;font-family:'DM Mono',monospace;color:var(--text3);margin-top:1px">
        llama3.1@localhost:11434 · chromadb · v2.0.0</div>
    </div>
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <span class="stat-pill">
      <span class="stat-dot" style="background:#22c55e"></span>
      model online <span class="stat-val">8B</span>
    </span>
    <span class="stat-pill">
      <span class="stat-dot" style="background:#7c3aed"></span>
      sessions <span class="stat-val">{total_sess}</span>
    </span>
    <span class="stat-pill">
      <span class="stat-dot" style="background:#f59e0b"></span>
      patterns <span class="stat-val">{unique_spots}</span>
    </span>
    <span class="stat-pill">
      <span class="stat-dot" style="background:#9c9890"></span>
      api cost <span class="stat-val">$0.00</span>
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── FACT BAR ──────────────────────────────────────────────────────
fact = FACTS[st.session_state.fact_idx % len(FACTS)]
fc1, fc2 = st.columns([8, 1])
with fc1:
    st.markdown(f"""
    <div class="fact-bar">
      <span class="fact-badge">DID YOU KNOW</span>
      <span class="fact-text">{fact}</span>
    </div>""", unsafe_allow_html=True)
with fc2:
    if st.button("next →"):
        st.session_state.fact_idx += 1
        st.rerun()

# ── MAIN LAYOUT ───────────────────────────────────────────────────
left, right = st.columns([3, 2], gap="medium")

with left:
    st.markdown('<div style="padding:8px 8px 0 24px">', unsafe_allow_html=True)

    st.markdown('<div class="sec-lbl">language</div>', unsafe_allow_html=True)
    language = st.selectbox("", list(LANG_EXT.keys()), label_visibility="collapsed")

    st.markdown('<div class="sec-lbl">review mode</div>', unsafe_allow_html=True)
    mode = st.radio("", list(REVIEW_MODES.keys()),
                    index=list(REVIEW_MODES.keys()).index(st.session_state.mode),
                    horizontal=True, label_visibility="collapsed")
    st.session_state.mode = mode

    ext = LANG_EXT.get(language, "py")
    st.markdown(f"""
    <div class="sec-lbl">editor</div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:7px;padding:11px 16px;
        border-bottom:1px solid var(--border);background:var(--surface2)">
        <div style="width:11px;height:11px;border-radius:50%;background:#ff5f57"></div>
        <div style="width:11px;height:11px;border-radius:50%;background:#febc2e"></div>
        <div style="width:11px;height:11px;border-radius:50%;background:#28c840"></div>
        <span style="margin-left:auto;font-size:11px;font-family:'DM Mono',monospace;color:var(--text3)">
          mentor.{ext} · {language} · {mode.split()[1]}
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    code_input = st.text_area("", height=280,
        placeholder=f"# Paste your {language} code here...",
        label_visibility="collapsed")

    run = st.button(f"Analyse with Llama 3.1 →")
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div style="padding:8px 24px 0 8px">', unsafe_allow_html=True)

    # Score ring
    score = st.session_state.score or 0
    ring_label = "awaiting first review" if not st.session_state.score else "code quality score"
    st.markdown(f"""
    <div style="background:var(--surface2);border:1px solid var(--border);
      border-radius:14px;padding:20px;margin-bottom:4px;text-align:center;
      box-shadow:var(--shadow-sm)">
      {score_ring_svg(score) if st.session_state.score else
       score_ring_svg(0).replace('stroke="#22c55e"','stroke="#e4e1d9"')}
      <div style="font-size:11px;font-family:'DM Mono',monospace;color:var(--text3);margin-top:8px">
        {ring_label}</div>
    </div>""", unsafe_allow_html=True)

    # Heatmap
    st.markdown('<div class="sec-lbl">weakness heatmap</div>', unsafe_allow_html=True)
    if not sorted_heat:
        st.markdown(f"""
        <div style="background:var(--surface2);border:1px solid var(--border);
          border-radius:12px;padding:28px;text-align:center;color:var(--text3);
          font-size:12px;font-family:'DM Mono',monospace">
          submit a review to start tracking
        </div>""", unsafe_allow_html=True)
    else:
        mx = sorted_heat[0][1]
        rows = ""
        for i, (spot, count) in enumerate(sorted_heat[:6]):
            pct = int((count / mx) * 100)
            op  = max(0.25, 1 - i * 0.18)
            rows += f"""
            <div class="heat-item">
              <div class="heat-row">
                <span class="heat-name">{spot}</span>
                <span class="heat-cnt">{count}×</span>
              </div>
              <div class="heat-bg">
                <div class="heat-fill" style="width:{pct}%;opacity:{op:.2f}"></div>
              </div>
            </div>"""
        st.markdown(f'<div style="padding:2px 0">{rows}</div>', unsafe_allow_html=True)

    # Session log
    st.markdown('<div class="sec-lbl">recent sessions</div>', unsafe_allow_html=True)
    sessions = st.session_state.session_log
    if not sessions:
        st.markdown(f"""<div style="color:var(--text3);font-size:12px;
          font-family:'DM Mono',monospace;padding:12px 0">no sessions yet</div>""",
          unsafe_allow_html=True)
    else:
        rows = ""
        for s in reversed(sessions[-5:]):
            lc = LANG_COL.get(s['lang'], '#7c3aed')
            rows += f"""<div class="sess-row">
              <span class="lang-badge" style="background:{lc}18;color:{lc}">
                {s['lang'][:2].upper()}</span>
              <span class="sess-spot">{s['spot']}</span>
              <span class="sess-time">just now</span>
            </div>"""
        st.markdown(f"""
        <div style="background:var(--surface);border:1px solid var(--border);
          border-radius:12px;padding:10px 14px;box-shadow:var(--shadow-sm)">{rows}</div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ── REVIEW LOGIC ──────────────────────────────────────────────────
if run:
    if not code_input.strip():
        st.error("Paste some code first.")
    else:
        mode_instr = REVIEW_MODES[st.session_state.mode]
        with st.spinner("Llama 3.1 is thinking..."):
            past = get_past_mistakes(code_input)
            from langchain_core.prompts import PromptTemplate
            from langchain_ollama import OllamaLLM
            llm = OllamaLLM(model="llama3.1", temperature=0.3)
            TEMPLATE = (
                "You are a senior software engineer. Review mode instruction: {mode_instruction}\n\n"
                "Past mistakes context for this developer: {past_mistakes}\n\n"
                "Review this {language} code:\n{code}\n\n"
                "Respond in this format:\n"
                "1. OVERALL: one sentence verdict\n"
                "2. ISSUES: specific problems with line references\n"
                "3. IMPROVEMENTS: concrete fix for each issue\n"
                "4. WEAK SPOT DETECTED: one short topic tag\n"
            )
            prompt = PromptTemplate(
                input_variables=["code","language","past_mistakes","mode_instruction"],
                template=TEMPLATE)
            review = (prompt | llm).invoke({
                "code": code_input, "language": language,
                "past_mistakes": past, "mode_instruction": mode_instr
            })

        spot  = extract_weak_spot(review)
        score = score_from_review(review)
        save_session(code=code_input, review=review, weak_spot=spot)
        st.session_state.score = score
        st.session_state.session_log.append({"lang": language, "spot": spot})

        lc = LANG_COL.get(language, '#7c3aed')
        st.markdown(f"""
        <div class="review-card">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px">
            <div style="font-size:15px;font-weight:500;color:var(--text);letter-spacing:-.01em">
              Code Review
              <span style="font-family:'DM Mono',monospace;font-size:12px;
                color:{lc};margin-left:8px">{language}</span>
            </div>
            <span style="background:var(--accent-light);border:1px solid rgba(124,58,237,.25);
              color:var(--accent);padding:4px 14px;border-radius:99px;
              font-size:11px;font-family:'DM Mono',monospace;font-weight:500">
              ⚠ {spot}
            </span>
          </div>
        """, unsafe_allow_html=True)

        if past and "None yet" not in past:
            with st.expander("memory context injected"):
                st.code(past, language=None)

        st.markdown(review)
        st.markdown('</div>', unsafe_allow_html=True)
        st.rerun()

# ── FOOTER ────────────────────────────────────────────────────────
st.markdown("""
<div class="foot-bar">
  <div class="foot-cell">
    <span style="font-size:15px">🧠</span>
    <div><div class="foot-name">Llama 3.1 8B</div><div class="foot-type">local model</div></div>
  </div>
  <div class="foot-cell">
    <span style="font-size:15px">🗄</span>
    <div><div class="foot-name">ChromaDB</div><div class="foot-type">vector store</div></div>
  </div>
  <div class="foot-cell">
    <span style="font-size:15px">📡</span>
    <div><div class="foot-name">all-MiniLM-L6</div><div class="foot-type">embedder</div></div>
  </div>
  <div class="foot-cell">
    <span style="font-size:15px">⚙</span>
    <div><div class="foot-name">LangChain 0.3</div><div class="foot-type">agent framework</div></div>
  </div>
</div>
""", unsafe_allow_html=True)