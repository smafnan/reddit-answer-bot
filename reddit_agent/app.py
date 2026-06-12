import streamlit as st
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(__file__))
from orchestrator import run_pipeline

st.set_page_config(
    page_title="Reddit Intelligence Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Theme state ──
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
if "win98_start" not in st.session_state:
    st.session_state.win98_start = False
if "result" not in st.session_state:
    st.session_state.result = None
if "query" not in st.session_state:
    st.session_state.query = ""
if "running" not in st.session_state:
    st.session_state.running = False

theme = st.session_state.theme

# ───────────────────────────────────────────────
# THEME CSS
# ───────────────────────────────────────────────

LIGHT_CSS = """
:root {
    --bg: #f5f5f5;
    --bg-card: #ffffff;
    --bg-input: #ffffff;
    --text: #1a1a2e;
    --text-dim: #666;
    --border: #ddd;
    --accent: #2563eb;
    --accent-hover: #1d4ed8;
    --shadow: 0 2px 8px rgba(0,0,0,0.08);
    --radius: 12px;
    --success: #16a34a;
    --warning: #d97706;
    --danger: #dc2626;
}
.stApp { background: var(--bg); color: var(--text); }
input, textarea { background: var(--bg-input) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
"""

DARK_CSS = """
:root {
    --bg: #0e1117;
    --bg-card: #1a1a2e;
    --bg-input: #1e1e2e;
    --text: #e0e0e0;
    --text-dim: #888;
    --border: #2a2a3e;
    --accent: #60a5fa;
    --accent-hover: #3b82f6;
    --shadow: 0 2px 8px rgba(0,0,0,0.3);
    --radius: 12px;
    --success: #4ade80;
    --warning: #facc15;
    --danger: #ef4444;
}
.stApp { background: var(--bg); color: var(--text); }
input, textarea { background: var(--bg-input) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
"""

WIN98_CSS = """
:root {
    --bg: #008080;
    --bg-card: #c0c0c0;
    --bg-input: #ffffff;
    --text: #000000;
    --text-dim: #666;
    --border: #808080;
    --border-light: #dfdfdf;
    --border-dark: #404040;
    --accent: #000080;
    --accent-hover: #0000a0;
    --shadow: none;
    --radius: 0px;
    --success: #008000;
    --warning: #808000;
    --danger: #800000;
    --title-bg: linear-gradient(90deg, #000080, #1084d0);
    --title-text: #ffffff;
    --btn-face: #c0c0c0;
    --btn-shadow: #808080;
    --btn-highlight: #ffffff;
    --btn-dark: #404040;
}
.stApp { background: var(--bg); color: var(--text); }
.stApp > header { display: none !important; }
#MainMenu { display: none !important; }
.stDeployButton { display: none !important; }
section.main > div { padding: 0 !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
input, textarea, select, button {
    font-family: 'Microsoft Sans Serif', 'MS Sans Serif', 'Courier New', monospace !important;
    font-size: 11px !important;
    background: var(--bg-input) !important;
    color: var(--text) !important;
    border: 2px solid !important;
    border-color: var(--border-light) var(--border-dark) var(--border-dark) var(--border-light) !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
.stTextInput > div > div > input {
    border: 2px solid !important;
    border-color: var(--border-dark) var(--border-light) var(--border-light) var(--border-dark) !important;
    padding: 2px 4px !important;
}
.stButton > button {
    background: var(--btn-face) !important;
    color: #000 !important;
    font-family: 'Microsoft Sans Serif', monospace !important;
    font-size: 11px !important;
    padding: 2px 12px !important;
    border: 2px solid !important;
    border-color: var(--border-light) var(--border-dark) var(--border-dark) var(--border-light) !important;
    box-shadow: 1px 1px 0 0 #000 !important;
    cursor: pointer !important;
    min-height: unset !important;
    line-height: 1.2 !important;
}
.stButton > button:active {
    border-color: var(--border-dark) var(--border-light) var(--border-light) var(--border-dark) !important;
    box-shadow: inset 1px 1px 0 0 #000 !important;
}
.stButton > button:hover { filter: brightness(1.05); }
.win98-window {
    background: var(--bg-card);
    border: 2px solid;
    border-color: var(--border-light) var(--border-dark) var(--border-dark) var(--border-light);
    margin: 4px 0;
    box-shadow: 1px 1px 0 0 #000;
}
.win98-title {
    background: var(--title-bg);
    color: var(--title-text);
    font-family: 'Microsoft Sans Serif', monospace;
    font-size: 11px;
    font-weight: bold;
    padding: 2px 4px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    user-select: none;
}
.win98-title-buttons { display: flex; gap: 2px; }
.win98-title-btn {
    width: 14px; height: 14px;
    background: var(--btn-face);
    border: 1px solid;
    border-color: var(--border-light) var(--border-dark) var(--border-dark) var(--border-light);
    display: flex; align-items: center; justify-content: center;
    font-size: 8px; font-weight: bold; color: #000;
    cursor: pointer; line-height: 1;
}
.win98-body { padding: 8px; }
.win98-desktop-icon {
    text-align: center;
    padding: 8px;
    cursor: pointer;
    display: inline-block;
    width: 80px;
}
.win98-desktop-icon:hover { background: rgba(0,0,128,0.1); }
.win98-desktop-icon span { display: block; color: #fff; font-size: 11px; margin-top: 4px; text-shadow: 1px 1px 0 #000; }
.win98-taskbar {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    height: 32px;
    background: #c0c0c0;
    border-top: 2px solid #fff;
    display: flex;
    align-items: center;
    padding: 0 2px;
    z-index: 9999;
    gap: 2px;
}
.win98-start {
    background: #c0c0c0;
    border: 2px solid;
    border-color: #fff #808080 #808080 #fff;
    padding: 2px 8px;
    font-family: 'Microsoft Sans Serif', monospace;
    font-size: 11px;
    font-weight: bold;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 4px;
    height: 24px;
}
.win98-start:active {
    border-color: #808080 #fff #fff #808080;
}
.win98-taskbar-divider {
    width: 2px;
    height: 22px;
    background: #808080;
    border-right: 1px solid #fff;
    margin: 0 2px;
}
.win98-taskbar-item {
    background: #c0c0c0;
    border: 2px solid;
    border-color: #808080 #fff #fff #808080;
    padding: 2px 8px;
    font-size: 11px;
    font-family: 'Microsoft Sans Serif', monospace;
    height: 22px;
    display: flex;
    align-items: center;
    cursor: pointer;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}
.win98-taskbar-item.active {
    border-color: #fff #808080 #808080 #fff;
    background: #d0d0d0;
}
.win98-taskbar-time {
    margin-left: auto;
    font-size: 11px;
    font-family: 'Microsoft Sans Serif', monospace;
    padding: 2px 6px;
    border: 1px solid;
    border-color: #808080 #fff #fff #808080;
    height: 22px;
    display: flex;
    align-items: center;
}
.win98-popup {
    position: fixed;
    bottom: 34px; left: 2px;
    background: #c0c0c0;
    border: 2px solid;
    border-color: #fff #808080 #808080 #fff;
    box-shadow: 2px 2px 0 0 #000;
    z-index: 10000;
    min-width: 160px;
    padding: 2px;
}
.win98-popup-item {
    padding: 4px 16px;
    font-family: 'Microsoft Sans Serif', monospace;
    font-size: 11px;
    cursor: pointer;
    color: #000;
}
.win98-popup-item:hover {
    background: #000080;
    color: #fff;
}
.win98-separator {
    height: 2px;
    border-top: 1px solid #808080;
    border-bottom: 1px solid #fff;
    margin: 2px 4px;
}
.stProgress > div > div > div { background: var(--accent) !important; }
div[data-testid="stDecoration"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
footer { display: none !important; }
"""

CSS = LIGHT_CSS if theme == "light" else DARK_CSS if theme == "dark" else WIN98_CSS
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ───────────────────────────────────────────────
# SIDEBAR THEME SELECTOR
# ───────────────────────────────────────────────

THEME_LABEL_MAP = {"dark": "dark", "light": "light", "win98": "windows 98"}

with st.sidebar:
    st.markdown("### Appearance")
    current_label = THEME_LABEL_MAP.get(theme, "dark")
    selected_label = st.radio(
        "Theme",
        ["dark", "light", "windows 98"],
        index=["dark", "light", "windows 98"].index(current_label),
        label_visibility="collapsed",
        key="theme_radio",
    )
    new_theme_id = {"dark": "dark", "light": "light", "windows 98": "win98"}[selected_label]
    if new_theme_id != theme:
        st.session_state.theme = new_theme_id
        st.rerun()

# ───────────────────────────────────────────────
# CONTENT
# ───────────────────────────────────────────────

# Windows 98 desktop area
if theme == "win98":
    st.markdown('<div style="padding-top:4px;padding-bottom:36px;min-height:100vh">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1,1,1,1])
    with col1:
        st.markdown('<div class="win98-desktop-icon">🔍<span>Reddit Engine</span></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="win98-desktop-icon">📁<span>My Queries</span></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="win98-desktop-icon">💾<span>Saved</span></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="win98-desktop-icon">♻️<span>Recycle Bin</span></div>', unsafe_allow_html=True)

    # Main window
    st.markdown('<div class="win98-window">', unsafe_allow_html=True)
    st.markdown(
        '<div class="win98-title">'
        '<span>🔍 Reddit Intelligence Engine</span>'
        '<div class="win98-title-buttons">'
        '<div class="win98-title-btn">_</div>'
        '<div class="win98-title-btn">□</div>'
        '<div class="win98-title-btn" style="font-weight:bold">✕</div>'
        '</div></div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="win98-body">', unsafe_allow_html=True)
    WINDOW_OPEN = True
else:
    WINDOW_OPEN = False

# ── Title ──
if theme != "win98":
    st.markdown(
        f'<h1 style="color:var(--accent);font-size:2rem;margin-bottom:4px">'
        f'🔍 Reddit Intelligence Engine</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p style="color:var(--text-dim);margin-top:0">Multi-agent Reddit research system</p>',
        unsafe_allow_html=True,
    )

# ── Quick selects ──
quick_questions = [
    "MacBook vs Windows for programming",
    "Is a CS degree worth it in 2026?",
    "Best budget laptop for AI engineering",
    "How to learn Python effectively",
]

if theme == "win98":
    st.markdown(f'<div style="display:flex;gap:4px;flex-wrap:wrap;margin:8px 0">', unsafe_allow_html=True)
    for q in quick_questions:
        if st.button(q, key=f"qq_{q}", use_container_width=True):
            st.session_state.query = q
    st.markdown('</div>', unsafe_allow_html=True)
else:
    cols = st.columns(4)
    for i, q in enumerate(quick_questions):
        with cols[i]:
            if st.button(q, key=f"qq_{q}", use_container_width=True):
                st.session_state.query = q

# ── Search input ──
query = st.text_input(
    "Ask a question",
    value=st.session_state.query,
    placeholder="e.g., MacBook vs Windows for programming",
    label_visibility="collapsed",
    key="search_input",
)

col1, col2, col3 = st.columns([3, 1, 1])
with col2:
    go = st.button(
        "🔍 Research" if theme != "win98" else "🔍 OK",
        type="primary" if theme != "win98" else "secondary",
        use_container_width=True,
    )

if theme != "win98":
    with col3:
        if st.button("🗑 Clear", use_container_width=True):
            st.session_state.query = ""
            st.session_state.result = None
            st.rerun()

# ── Run pipeline ──
if go and query:
    st.session_state.running = True
    st.session_state.result = None

    agent_names = [
        "Query Expansion",
        "Reddit Retrieval",
        "Spam Filtering",
        "Credibility Scoring",
        "Contradiction Detection",
        "Perspective Generation",
        "Knowledge Graph",
        "Summarization",
        "Fact Check",
    ]
    agent_icons = ["🌐", "📡", "🧹", "⭐", "⚡", "👥", "🔗", "📋", "✅"]

    status_ph = st.empty()
    progress_ph = st.empty()
    result_ph = st.empty()

    progress_bar = progress_ph.progress(0, text="Starting agents...")

    status_ph.markdown("""
    <style>
    .agent-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 12px 0; }
    .agent-item {
        padding: 8px 12px; border-radius: 8px; font-size: 13px;
        transition: all 0.3s ease; text-align: center;
    }
    .agent-pending { background: #1a1a1a; color: #555; }
    .agent-running { background: #1a2a3a; color: #60a5fa; border: 1px solid #60a5fa; animation: pulse 1.5s infinite; }
    .agent-done { background: #1a3a2a; color: #4ade80; }
    @keyframes pulse { 0% { opacity: 0.7; } 50% { opacity: 1; } 100% { opacity: 0.7; } }
    .win98-agent { font-family:'Microsoft Sans Serif',monospace; font-size:11px; border:2px solid; }
    .win98-agent-pending { background:#c0c0c0; color:#000; border-color:#808080 #fff #fff #808080; }
    .win98-agent-running { background:#000080; color:#fff; border-color:#fff #000080 #000080 #fff; }
    .win98-agent-done { background:#008000; color:#fff; border-color:#fff #008000 #008000 #fff; }
    </style>
    """, unsafe_allow_html=True)

    agent_container = status_ph.container()
    with agent_container:
        cols = st.columns(3)
        for i, (name, icon) in enumerate(zip(agent_names, agent_icons)):
            with cols[i % 3]:
                st.markdown(
                    f'<div class="agent-item agent-pending" id="agent-{i}">⏳ {icon} {name}</div>',
                    unsafe_allow_html=True,
                )

    original_print = __builtins__["print"]

    class Capture:
        def __init__(self):
            self.current = 0
        def write(self, text):
            if "Expanding" in text:
                self.current = 0
            elif "Retrieving" in text:
                self.current = 1
            elif "Filtering" in text:
                self.current = 2
            elif "Scoring" in text:
                self.current = 3
            elif "Detecting" in text:
                self.current = 4
            elif "Generating" in text:
                self.current = 5
            elif "Extracting" in text:
                self.current = 6
            elif "Synthesizing" in text:
                self.current = 7
            elif "Fact" in text:
                self.current = 8

            progress_ph.progress(
                (self.current + 0.5) / len(agent_names),
                text=agent_names[self.current],
            )

            with agent_container:
                cols = st.columns(3)
                for i, (name, icon) in enumerate(zip(agent_names, agent_icons)):
                    with cols[i % 3]:
                        if i < self.current:
                            st.markdown(
                                f'<div class="agent-item agent-done">✅ {icon} {name}</div>',
                                unsafe_allow_html=True,
                            )
                        elif i == self.current:
                            st.markdown(
                                f'<div class="agent-item agent-running">🔄 {icon} {name}</div>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f'<div class="agent-item agent-pending">⏳ {icon} {name}</div>',
                                unsafe_allow_html=True,
                            )

    capture = Capture()
    import builtins
    builtins.__dict__["print"] = capture.write

    try:
        result = run_pipeline(query)

        progress_ph.progress(1.0, text="Complete!")

        with agent_container:
            cols = st.columns(3)
            for i, (name, icon) in enumerate(zip(agent_names, agent_icons)):
                with cols[i % 3]:
                    st.markdown(
                        f'<div class="agent-item agent-done">✅ {icon} {name}</div>',
                        unsafe_allow_html=True,
                    )

        builtins.__dict__["print"] = original_print
        st.session_state.result = result
        st.session_state.running = False

    except Exception as e:
        builtins.__dict__["print"] = original_print
        st.session_state.running = False
        st.error(f"Error: {e}")

# ── Display results ──
result = st.session_state.result
if result and not st.session_state.running:
    if "error" in result:
        st.error(result["error"])
    else:
        summary = result.get("summary", {})
        contradictions = result.get("contradictions", {})
        fact_check = result.get("fact_check", {})
        kg = result.get("knowledge_graph", {})
        perspectives = result.get("perspectives", [])
        posts = result.get("scored_posts", [])

        # ── Answer Window ──
        if theme == "win98":
            st.markdown('<div class="win98-window" style="margin-top:12px">', unsafe_allow_html=True)
            st.markdown(
                '<div class="win98-title">'
                '<span>📋 Answer</span>'
                '<div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div>'
                '</div>',
                unsafe_allow_html=True
            )
            st.markdown('<div class="win98-body">', unsafe_allow_html=True)

        consensus = summary.get("consensus", "No consensus available")

        if theme == "win98":
            st.markdown(
                f'<div style="background:#fff;border:2px inset #ddd;padding:8px;font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;line-height:1.4">{consensus}</div>',
                unsafe_allow_html=True
            )
        else:
            border_color = "var(--accent)"
            st.markdown(
                f'<div style="background:var(--bg-card);border:1px solid var(--border);border-left:4px solid {border_color};'
                f'border-radius:12px;padding:20px;font-size:16px;line-height:1.7;margin:12px 0;box-shadow:var(--shadow)">'
                f'{consensus}</div>',
                unsafe_allow_html=True
            )

        # ── Key Insights & Recommendations ──
        if theme == "win98":
            st.markdown('</div></div>', unsafe_allow_html=True)
            cols = st.columns(2)
            with cols[0]:
                st.markdown('<div class="win98-window">', unsafe_allow_html=True)
                st.markdown('<div class="win98-title"><span>💡 Key Insights</span><div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div></div><div class="win98-body">', unsafe_allow_html=True)
                for ins in summary.get("key_insights", []):
                    st.markdown(f'<div style="font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;padding:2px 0">• {ins}</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)
            with cols[1]:
                st.markdown('<div class="win98-window">', unsafe_allow_html=True)
                st.markdown('<div class="win98-title"><span>🎯 Recommendations</span><div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div></div><div class="win98-body">', unsafe_allow_html=True)
                for r in summary.get("recommendations", []):
                    st.markdown(f'<div style="font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;padding:2px 0">• {r}</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)
        else:
            col1, col2 = st.columns(2)
            with col1:
                with st.container():
                    st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow);height:100%">', unsafe_allow_html=True)
                    st.markdown(f'<h3 style="color:var(--accent);margin:0 0 8px 0;font-size:1.1rem">💡 Key Insights</h3>', unsafe_allow_html=True)
                    for ins in summary.get("key_insights", []):
                        st.markdown(f'<div style="padding:4px 0;font-size:14px;color:var(--text)">• {ins}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                with st.container():
                    st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow);height:100%">', unsafe_allow_html=True)
                    st.markdown(f'<h3 style="color:var(--accent);margin:0 0 8px 0;font-size:1.1rem">🎯 Recommendations</h3>', unsafe_allow_html=True)
                    for r in summary.get("recommendations", []):
                        st.markdown(f'<div style="padding:4px 0;font-size:14px;color:var(--text)">• {r}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

        # ── Contradictions / Community Sentiment ──
        if contradictions.get("has_contradictions") or contradictions.get("consensus"):
            if theme == "win98":
                st.markdown('<div class="win98-window" style="margin-top:8px">', unsafe_allow_html=True)
                st.markdown('<div class="win98-title"><span>⚡ Community Sentiment</span><div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div></div><div class="win98-body">', unsafe_allow_html=True)
                if contradictions.get("has_contradictions"):
                    view_cols = st.columns(len(contradictions.get("viewpoints", [1])))
                    for i, v in enumerate(contradictions.get("viewpoints", [])):
                        pct = v.get("percentage", 0)
                        with view_cols[i]:
                            st.markdown(
                                f'<div style="text-align:center;border:2px inset #ddd;padding:8px;background:#fff;font-family:\'Microsoft Sans Serif\',monospace;font-size:11px">'
                                f'<div style="font-size:24px;font-weight:bold">{pct}%</div>'
                                f'<div style="font-weight:bold;margin:4px 0">{v.get("stance", "")}</div>'
                                f'<div style="color:#555;font-size:10px">{v.get("summary", "")[:100]}</div></div>',
                                unsafe_allow_html=True
                            )
                else:
                    st.markdown(f'<div style="font-size:11px;font-family:\'Microsoft Sans Serif\',monospace">Consensus: {contradictions.get("consensus", "")}</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)
            else:
                if contradictions.get("has_contradictions"):
                    st.markdown(f'<h3 style="color:var(--accent);margin:16px 0 8px 0;font-size:1.1rem">⚡ Community Sentiment</h3>', unsafe_allow_html=True)
                    view_cols = st.columns(len(contradictions.get("viewpoints", [1])))
                    for i, v in enumerate(contradictions.get("viewpoints", [])):
                        pct = v.get("percentage", 0)
                        color = "#4ade80" if pct > 50 else "#facc15" if pct > 25 else "#ef4444"
                        with view_cols[i]:
                            st.markdown(
                                f'<div style="text-align:center;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow)">'
                                f'<div style="font-size:32px;font-weight:bold;color:{color}">{pct}%</div>'
                                f'<div style="font-weight:bold;margin:8px 0;color:var(--text)">{v.get("stance", "")}</div>'
                                f'<div style="font-size:13px;color:var(--text-dim)">{v.get("summary", "")[:120]}</div></div>',
                                unsafe_allow_html=True
                            )
                else:
                    st.info(f"Consensus: {contradictions.get('consensus', '')}")

        # ── Perspectives ──
        if perspectives:
            if theme == "win98":
                st.markdown('<div class="win98-window" style="margin-top:8px">', unsafe_allow_html=True)
                st.markdown('<div class="win98-title"><span>👥 Perspectives</span><div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div></div><div class="win98-body">', unsafe_allow_html=True)
                cols = st.columns(3)
                for i, p in enumerate(perspectives):
                    with cols[i % 3]:
                        st.markdown(
                            f'<div style="border:2px inset #ddd;padding:6px;background:#fff;margin:2px 0;font-family:\'Microsoft Sans Serif\',monospace;font-size:11px;height:60px">'
                            f'<strong>{p.get("group", "")}</strong><br>'
                            f'<span style="color:#555;font-size:10px">{p.get("angle", "")}</span></div>',
                            unsafe_allow_html=True
                        )
                st.markdown('</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<h3 style="color:var(--accent);margin:16px 0 8px 0;font-size:1.1rem">👥 Stakeholder Perspectives</h3>', unsafe_allow_html=True)
                cols = st.columns(3)
                for i, p in enumerate(perspectives):
                    with cols[i % 3]:
                        st.markdown(
                            f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:12px;box-shadow:var(--shadow);margin:4px 0;height:80px">'
                            f'<strong style="color:var(--text)">{p.get("group", "")}</strong><br>'
                            f'<span style="font-size:13px;color:var(--text-dim)">{p.get("angle", "")}</span></div>',
                            unsafe_allow_html=True
                        )

        # ── Knowledge Graph ──
        if kg.get("entities"):
            if theme == "win98":
                st.markdown('<div class="win98-window" style="margin-top:8px">', unsafe_allow_html=True)
                st.markdown('<div class="win98-title"><span>🔗 Knowledge Graph</span><div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div></div><div class="win98-body">', unsafe_allow_html=True)
                cols = st.columns(2)
                with cols[0]:
                    st.markdown('<b style="font-size:11px">Entities</b>', unsafe_allow_html=True)
                    for e in kg["entities"][:6]:
                        c = {"positive":"🟢","negative":"🔴","neutral":"🟡"}.get(e.get("sentiment",""),"⚪")
                        st.markdown(f'<div style="font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;padding:2px 0">{c} <b>{e.get("name","")}</b> <span style="color:#555">({e.get("type","")})</span></div>', unsafe_allow_html=True)
                with cols[1]:
                    if kg.get("relationships"):
                        st.markdown('<b style="font-size:11px">Relationships</b>', unsafe_allow_html=True)
                        for rel in kg["relationships"][:4]:
                            st.markdown(f'<div style="font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;padding:2px 0"><b>{rel.get("source","")}</b> → <i>{rel.get("relation","")}</i> → <b>{rel.get("target","")}</b></div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<h3 style="color:var(--accent);margin:16px 0 8px 0;font-size:1.1rem">🔗 Knowledge Graph</h3>', unsafe_allow_html=True)
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow)">', unsafe_allow_html=True)
                    st.markdown(f'<strong style="color:var(--text)">Entities</strong>', unsafe_allow_html=True)
                    for e in kg["entities"][:6]:
                        c = {"positive":"🟢","negative":"🔴","neutral":"🟡"}.get(e.get("sentiment",""),"⚪")
                        st.markdown(f'<div style="padding:4px 0;font-size:13px;color:var(--text)">{c} <strong>{e.get("name","")}</strong> <span style="color:var(--text-dim)">({e.get("type","")})</span></div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                with cols[1]:
                    if kg.get("relationships"):
                        st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow)">', unsafe_allow_html=True)
                        st.markdown(f'<strong style="color:var(--text)">Relationships</strong>', unsafe_allow_html=True)
                        for rel in kg["relationships"][:4]:
                            st.markdown(f'<div style="padding:4px 0;font-size:13px;color:var(--text)"><strong>{rel.get("source","")}</strong> → <em>{rel.get("relation","")}</em> → <strong>{rel.get("target","")}</strong></div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

        # ── Fact Check ──
        fc = fact_check
        if fc.get("overall_assessment"):
            if theme == "win98":
                st.markdown('<div class="win98-window" style="margin-top:8px">', unsafe_allow_html=True)
                st.markdown('<div class="win98-title"><span>✅ Fact Check</span><div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div></div><div class="win98-body">', unsafe_allow_html=True)
                assessment = fc.get("overall_assessment", "")
                icons = {"reddit_is_generally_correct": "🟢 Generally correct",
                         "reddit_has_mixed_accuracy": "🟡 Mixed accuracy",
                         "reddit_is_misleading": "🔴 Misleading"}
                label = icons.get(assessment, "⚪ Unknown")
                st.markdown(f'<div style="font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;padding:4px 0"><b>{label}</b></div>', unsafe_allow_html=True)
                if fc.get("recommendation"):
                    st.markdown(f'<div style="font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;padding:2px 0;color:#555">{fc["recommendation"]}</div>', unsafe_allow_html=True)
                if fc.get("questionable_claims"):
                    for c in fc["questionable_claims"]:
                        st.warning(c)
                st.markdown('</div></div>', unsafe_allow_html=True)
            else:
                assessment = fc.get("overall_assessment", "")
                color_map = {
                    "reddit_is_generally_correct": ("🟢", "Generally correct", "success"),
                    "reddit_has_mixed_accuracy": ("🟡", "Mixed accuracy", "warning"),
                    "reddit_is_misleading": ("🔴", "Misleading", "danger"),
                }
                emoji, label, _ = color_map.get(assessment, ("⚪", "Unknown", "info"))
                st.info(f"{emoji} **{label}** — {fc.get('recommendation', '')}")
                if fc.get("questionable_claims"):
                    for c in fc["questionable_claims"]:
                        st.warning(c)

        # ── Sources ──
        if theme == "win98":
            st.markdown('<div class="win98-window" style="margin-top:8px">', unsafe_allow_html=True)
            st.markdown(
                f'<div class="win98-title"><span>📚 Sources ({len(posts)})</span>'
                f'<div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div></div>',
                unsafe_allow_html=True
            )
            st.markdown('<div class="win98-body">', unsafe_allow_html=True)
            for i, p in enumerate(posts[:8], 1):
                cred = p.get("credibility", "")
                cred_str = f" • Credibility: {cred}/10" if cred else ""
                st.markdown(
                    f'<div style="border:2px inset #ddd;padding:6px;background:#fff;margin:4px 0">'
                    f'<a href="{p["url"]}" target="_blank" style="color:#000080;font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;font-weight:bold;text-decoration:underline">{p["title"]}</a>'
                    f'<br><span style="color:#555;font-size:10px">r/{p["subreddit"]}{cred_str}</span></div>',
                    unsafe_allow_html=True
                )
            st.markdown('</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<h3 style="color:var(--accent);margin:16px 0 8px 0;font-size:1.1rem">📚 Sources ({len(posts)})</h3>',
                unsafe_allow_html=True
            )
            for i, p in enumerate(posts[:8], 1):
                cred = p.get("credibility", "")
                cred_str = f" • Credibility: {cred}/10" if cred else ""
                st.markdown(
                    f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:12px 16px;margin:6px 0;box-shadow:var(--shadow)">'
                    f'<a href="{p["url"]}" target="_blank" style="color:var(--accent);text-decoration:none;font-weight:bold;font-size:14px">{p["title"]}</a>'
                    f'<br><span style="color:var(--text-dim);font-size:13px">r/{p["subreddit"]}{cred_str}</span></div>',
                    unsafe_allow_html=True
                )

        # ── Caveats (collapsible) ──
        if summary.get("caveats"):
            if theme == "win98":
                st.markdown('<div class="win98-window" style="margin-top:8px">', unsafe_allow_html=True)
                st.markdown('<div class="win98-title"><span>⚠️ Caveats</span><div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div></div><div class="win98-body">', unsafe_allow_html=True)
                for c in summary["caveats"]:
                    st.markdown(f'<div style="font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;padding:2px 0">• {c}</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)
            else:
                with st.expander("⚠️ Caveats"):
                    for c in summary["caveats"]:
                        st.markdown(f"- {c}")

# ── Close Win98 body ──
if theme == "win98" and WINDOW_OPEN:
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)  # close desktop area

    # ── Windows 98 Taskbar ──
    now = time.strftime("%I:%M %p").lstrip("0").replace("  ", " ")
    start_label = "🔍 Reddit Engine"
    if st.session_state.result:
        task_label = "📋 Answer"
    else:
        task_label = "Ready"

    st.markdown(f"""
    <div class="win98-taskbar">
        <div class="win98-start" id="win98-start-btn" onclick="document.getElementById('win98-popup').style.display=document.getElementById('win98-popup').style.display==='none'?'block':'none'">
            <span style="font-size:14px">🖥</span> Start
        </div>
        <div class="win98-taskbar-divider"></div>
        <div class="win98-taskbar-item active">{task_label}</div>
        <div class="win98-taskbar-time">{now}</div>
    </div>
    <div class="win98-popup" id="win98-popup" style="display:none">
        <div class="win98-popup-item" onclick="document.getElementById('win98-popup').style.display='none'">🔍 Reddit Intelligence Engine</div>
        <div class="win98-popup-item" onclick="document.getElementById('win98-popup').style.display='none'">📁 My Queries</div>
        <div class="win98-separator"></div>
        <div class="win98-popup-item" onclick="document.getElementById('win98-popup').style.display='none'">💾 Saved Reports</div>
        <div class="win98-separator"></div>
        <div class="win98-popup-item" onclick="document.getElementById('win98-popup').style.display='none'">⚙ Settings</div>
        <div class="win98-popup-item" onclick="document.getElementById('win98-popup').style.display='none'">❓ Help</div>
    </div>
    <script>
        document.addEventListener('click', function(e) {{
            var popup = document.getElementById('win98-popup');
            var btn = document.getElementById('win98-start-btn');
            if (popup && btn && !btn.contains(e.target) && !popup.contains(e.target)) {{
                popup.style.display = 'none';
            }}
        }});
    </script>
    """, unsafe_allow_html=True)
