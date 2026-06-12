import streamlit as st
import sys, os, json, time, uuid, re, datetime

sys.path.insert(0, os.path.dirname(__file__))
from orchestrator import run_pipeline

st.set_page_config(page_title="Reddit Intelligence Engine", page_icon="🔍", layout="wide", initial_sidebar_state="collapsed")

for key in ("theme", "result", "query", "running", "reports"):
    if key not in st.session_state:
        st.session_state[key] = "" if key == "query" else False if key == "running" else [] if key == "reports" else None if key == "result" else "dark"

theme = st.session_state.theme
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ── Load saved reports ──
def load_reports():
    reports = []
    if os.path.exists(DATA_DIR):
        for fn in sorted(os.listdir(DATA_DIR), reverse=True):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(DATA_DIR, fn)) as f:
                        reports.append(json.load(f))
                except:
                    pass
    return reports

def save_report(data):
    rid = str(uuid.uuid4())[:8]
    slug = re.sub(r'[^a-z0-9]+', '-', data["query"].lower()).strip('-') or "report"
    fp = os.path.join(DATA_DIR, f"{slug}-{rid}.json")
    data["id"] = rid
    data["timestamp"] = datetime.datetime.now().isoformat()
    with open(fp, "w") as f:
        json.dump(data, f, indent=2)
    return data

# ───────────────────────────────────────────────
# THEME CSS
# ───────────────────────────────────────────────

LIGHT_CSS = """
:root {
    --bg: #f5f5f5; --bg-card: #ffffff; --bg-input: #ffffff;
    --text: #1a1a2e; --text-dim: #777; --text-bright: #1a1a2e;
    --border: #ddd; --accent: #2563eb; --accent-hover: #1d4ed8;
    --shadow: 0 2px 8px rgba(0,0,0,0.08); --radius: 12px;
    --success: #16a34a; --warning: #d97706; --danger: #dc2626;
    --color-primary: #2563eb; --color-secondary: #0891b2;
}
.stApp { background: var(--bg); color: var(--text); }
input, textarea { background: var(--bg-input) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
"""

DARK_CSS = """
:root {
    --bg: #0e1117; --bg-card: #1a1a2e; --bg-input: #1e1e2e;
    --text: #e0e0e0; --text-dim: #888; --text-bright: #f8fafc;
    --border: #2a2a3e; --accent: #60a5fa; --accent-hover: #3b82f6;
    --shadow: 0 2px 8px rgba(0,0,0,0.3); --radius: 12px;
    --success: #4ade80; --warning: #facc15; --danger: #ef4444;
    --color-primary: #8b5cf6; --color-secondary: #06b6d4;
}
.stApp { background: var(--bg); color: var(--text); }
input, textarea { background: var(--bg-input) !important; color: var(--text) !important; border: 1px solid var(--border) !important; }
"""

WIN98_CSS = """
:root {
    --bg: #008080; --bg-card: #c0c0c0; --bg-input: #ffffff;
    --text: #000000; --text-dim: #666; --text-bright: #000000;
    --border: #808080; --border-light: #dfdfdf; --border-dark: #404040;
    --accent: #000080; --accent-hover: #0000a0;
    --radius: 0px; --shadow: none;
    --success: #008000; --warning: #808000; --danger: #800000;
    --color-primary: #000080; --color-secondary: #008080;
    --title-bg: linear-gradient(90deg, #000080, #1084d0);
    --title-text: #ffffff; --btn-face: #c0c0c0;
    --btn-highlight: #ffffff; --btn-dark: #404040;
}
.stApp { background: var(--bg); color: var(--text); }
.stApp > header, #MainMenu, .stDeployButton { display: none !important; }
section.main > div { padding: 0 !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
input, textarea, select, button {
    font-family: 'Microsoft Sans Serif', 'MS Sans Serif', 'Courier New', monospace !important;
    font-size: 11px !important;
    background: var(--bg-input) !important; color: var(--text) !important;
    border: 2px solid !important;
    border-color: var(--border-light) var(--border-dark) var(--border-dark) var(--border-light) !important;
    border-radius: 0 !important; box-shadow: none !important;
}
.stTextInput > div > div > input {
    border: 2px solid !important;
    border-color: var(--border-dark) var(--border-light) var(--border-light) var(--border-dark) !important;
    padding: 2px 4px !important;
}
.stButton > button {
    background: var(--btn-face) !important; color: #000 !important;
    border: 2px solid !important;
    border-color: var(--border-light) var(--border-dark) var(--border-dark) var(--border-light) !important;
    box-shadow: 1px 1px 0 0 #000 !important; cursor: pointer !important;
    min-height: unset !important; line-height: 1.2 !important;
}
.stButton > button:active {
    border-color: var(--border-dark) var(--border-light) var(--border-light) var(--border-dark) !important;
    box-shadow: inset 1px 1px 0 0 #000 !important;
}
.stProgress > div > div > div { background: #000080 !important; }
footer, div[data-testid="stDecoration"], div[data-testid="stToolbar"] { display: none !important; }
.win98-window { background: var(--bg-card); border: 2px solid; border-color: var(--border-light) var(--border-dark) var(--border-dark) var(--border-light); margin: 4px 0; }
.win98-title { background: var(--title-bg); color: var(--title-text); font-family: 'Microsoft Sans Serif', monospace; font-size: 11px; font-weight: bold; padding: 2px 4px; display: flex; justify-content: space-between; align-items: center; }
.win98-title-buttons { display: flex; gap: 2px; }
.win98-title-btn { width: 14px; height: 14px; background: var(--btn-face); border: 1px solid; border-color: var(--border-light) var(--border-dark) var(--border-dark) var(--border-light); display: flex; align-items: center; justify-content: center; font-size: 8px; cursor: pointer; }
.win98-body { padding: 8px; }
.win98-taskbar { position: fixed; bottom: 0; left: 0; right: 0; height: 32px; background: #c0c0c0; border-top: 2px solid #fff; display: flex; align-items: center; padding: 0 2px; z-index: 9999; gap: 2px; }
.win98-start { background: #c0c0c0; border: 2px solid; border-color: #fff #808080 #808080 #fff; padding: 2px 8px; font-size: 11px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 4px; height: 24px; }
.win98-start:active { border-color: #808080 #fff #fff #808080; }
.win98-taskbar-divider { width: 2px; height: 22px; background: #808080; border-right: 1px solid #fff; margin: 0 2px; }
.win98-taskbar-item { background: #c0c0c0; border: 2px solid; border-color: #808080 #fff #fff #808080; padding: 2px 8px; font-size: 11px; height: 22px; display: flex; align-items: center; cursor: pointer; }
.win98-taskbar-item.active { border-color: #fff #808080 #808080 #fff; background: #d0d0d0; }
.win98-taskbar-time { margin-left: auto; font-size: 11px; padding: 2px 6px; border: 1px solid; border-color: #808080 #fff #fff #808080; height: 22px; display: flex; align-items: center; }
.win98-popup { position: fixed; bottom: 34px; left: 2px; background: #c0c0c0; border: 2px solid; border-color: #fff #808080 #808080 #fff; box-shadow: 2px 2px 0 0 #000; z-index: 10000; min-width: 160px; padding: 2px; }
.win98-popup-item { padding: 4px 16px; font-size: 11px; cursor: pointer; color: #000; }
.win98-popup-item:hover { background: #000080; color: #fff; }
.win98-separator { height: 2px; border-top: 1px solid #808080; border-bottom: 1px solid #fff; margin: 2px 4px; }
.win98-desktop-icon { text-align: center; padding: 8px; cursor: pointer; display: inline-block; width: 80px; }
.win98-desktop-icon:hover { background: rgba(0,0,128,0.1); }
.win98-desktop-icon span { display: block; color: #fff; font-size: 11px; margin-top: 4px; text-shadow: 1px 1px 0 #000; }
"""

CSS = LIGHT_CSS if theme == "light" else DARK_CSS if theme == "dark" else WIN98_CSS
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ── Helper functions ──
def render_force_graph(nodes, edges, width=600, height=350):
    import random, math
    positions = {}
    cx, cy = width / 2, height / 2
    for n in nodes:
        positions[n["id"]] = {"x": cx + random.uniform(-100, 100), "y": cy + random.uniform(-100, 100), "vx": 0, "vy": 0}
    for _ in range(80):
        for n in nodes:
            p = positions[n["id"]]
            p["vx"] += (cx - p["x"]) * 0.02
            p["vy"] += (cy - p["y"]) * 0.02
        for i, a in enumerate(nodes):
            for j, b in enumerate(nodes):
                if i >= j: continue
                p1, p2 = positions[a["id"]], positions[b["id"]]
                dx, dy = p2["x"] - p1["x"], p2["y"] - p1["y"]
                d = math.sqrt(dx*dx + dy*dy) + 0.1
                f = 2000 / (d * d)
                if d < 200:
                    p1["vx"] -= (dx/d) * f
                    p1["vy"] -= (dy/d) * f
                    p2["vx"] += (dx/d) * f
                    p2["vy"] += (dy/d) * f
        edge_set = set()
        for e in edges:
            edge_set.add((e["source"], e["target"]))
        for s, t in edge_set:
            if s in positions and t in positions:
                p1, p2 = positions[s], positions[t]
                dx, dy = p2["x"] - p1["x"], p2["y"] - p1["y"]
                d = math.sqrt(dx*dx + dy*dy) + 0.1
                f = (d - 90) * 0.04
                p1["vx"] += (dx/d) * f
                p1["vy"] += (dy/d) * f
                p2["vx"] -= (dx/d) * f
                p2["vy"] -= (dy/d) * f
        for n in nodes:
            p = positions[n["id"]]
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vx"] *= 0.8
            p["vy"] *= 0.8
            p["x"] = max(20, min(width-20, p["x"]))
            p["y"] = max(20, min(height-20, p["y"]))
    type_colors = {"Hardware": "#f97316", "Software": "#10b981", "Concept": "#0ea5e9", "Organization": "#ec4899"}
    svg = f'<svg width="{width}" height="{height}" style="background:rgba(0,0,0,0.03);border-radius:8px;width:100%">'
    svg += '<defs><marker id="arr" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255,255,255,0.2)"/></marker></defs>'
    for e in edges:
        if e["source"] in positions and e["target"] in positions:
            s, t = positions[e["source"]], positions[e["target"]]
            mx, my = (s["x"]+t["x"])/2, (s["y"]+t["y"])/2
            svg += f'<line x1="{s["x"]}" y1="{s["y"]}" x2="{t["x"]}" y2="{t["y"]}" stroke="rgba(255,255,255,0.15)" stroke-width="1.5" marker-end="url(#arr)"/>'
            svg += f'<text x="{mx}" y="{my-4}" fill="rgba(255,255,255,0.3)" font-size="11" text-anchor="middle" font-family="sans-serif">{e.get("label","")}</text>'
    for n in nodes:
        p = positions[n["id"]]
        col = type_colors.get(n.get("type",""), "#8b5cf6")
        svg += f'<circle cx="{p["x"]}" cy="{p["y"]}" r="8" fill="{col}" stroke="rgba(255,255,255,0.3)" stroke-width="1.5"/>'
        svg += f'<text x="{p["x"]+14}" y="{p["y"]+4}" fill="var(--text-bright)" font-size="12" font-family="sans-serif">{n.get("label","")}</text>'
    svg += '</svg>'
    return svg

def render_md(text):
    lines = text.split('\n')
    parts = []
    for line in lines:
        if line.startswith('### '): parts.append(f'<h4 style="color:var(--color-secondary);margin:16px 0 8px 0">{line[4:]}</h4>')
        elif line.startswith('## '): parts.append(f'<h4 style="color:var(--color-primary);margin:16px 0 8px 0">{line[3:]}</h4>')
        elif line.startswith('* ') or line.startswith('- '): parts.append(f'<li style="margin:4px 0">{line[2:]}</li>')
        elif line.strip() == '': parts.append('<br>')
        elif '**' in line:
            parts.append(f'<p>{line.replace("**", "<strong>", 1).replace("**", "</strong>", 1)}</p>')
        else: parts.append(f'<p>{line}</p>')
    return ''.join(parts)

# ── Sidebar ──
with st.sidebar:
    theme_label = {"dark": "dark", "light": "light", "win98": "windows 98"}
    sel = st.radio("Theme", ["dark", "light", "windows 98"],
                   index=["dark", "light", "windows 98"].index(theme_label[theme]),
                   label_visibility="collapsed", key="theme_radio")
    new_id = {"dark": "dark", "light": "light", "windows 98": "win98"}[sel]
    if new_id != theme:
        st.session_state.theme = new_id
        st.rerun()

    st.markdown("---")
    st.markdown("### Saved Reports")
    saved = load_reports()
    if saved:
        for r in saved[-10:]:
            q = r.get("query", "?")[:50]
            conf = r.get("summary", {}).get("confidence_score", 0)
            if st.button(f"{'🟢' if conf > 0.7 else '🟡' if conf > 0.4 else '🔴'} {q}", key=f"r_{r.get('id','')}", use_container_width=True):
                st.session_state.result = r
                st.session_state.running = False
                st.rerun()
    else:
        st.caption("No saved reports yet.")

# ── Win98 Desktop ──
if theme == "win98":
    st.markdown('<div style="padding-top:4px;padding-bottom:36px;min-height:100vh">', unsafe_allow_html=True)
    cols = st.columns(4)
    icons = ["🔍", "📁", "💾", "♻️"]
    labels = ["Reddit Engine", "My Queries", "Saved", "Recycle Bin"]
    for i, (ico, lab) in enumerate(zip(icons, labels)):
        cols[i].markdown(f'<div class="win98-desktop-icon">{ico}<span>{lab}</span></div>', unsafe_allow_html=True)

    wtitle = "🔍 Reddit Intelligence Engine"
    st.markdown('<div class="win98-window">', unsafe_allow_html=True)
    st.markdown(f'<div class="win98-title"><span>{wtitle}</span><div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn" style="font-weight:bold">✕</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="win98-body">', unsafe_allow_html=True)
    WINDOW_OPEN = True
else:
    WINDOW_OPEN = False

# ── Title ──
if theme != "win98":
    st.markdown(f'<h1 style="color:var(--accent);font-size:2rem;margin-bottom:4px">🔍 Reddit Intelligence Engine</h1>', unsafe_allow_html=True)
    st.markdown(f'<p style="color:var(--text-dim);margin-top:0">Multi-agent Reddit research system — combines 9 analysis agents with interactive visualization</p>', unsafe_allow_html=True)

# ── Search ──
quick = ["MacBook vs Windows for programming", "Is a CS degree worth it in 2026?", "Best budget laptop for AI engineering", "What do you think about the RTX 5060?"]
if theme == "win98":
    st.markdown('<div style="display:flex;gap:4px;flex-wrap:wrap;margin:8px 0">', unsafe_allow_html=True)
    for q in quick:
        if st.button(q, key=f"qq_{q}", use_container_width=False):
            st.session_state.query = q
    st.markdown('</div>', unsafe_allow_html=True)
else:
    cols = st.columns(4)
    for i, q in enumerate(quick):
        if cols[i].button(q, key=f"qq_{q}", use_container_width=True):
            st.session_state.query = q

query = st.text_input("Ask a question", value=st.session_state.query, placeholder="e.g., MacBook vs Windows for programming", label_visibility="collapsed", key="search_input")
c1, c2, c3 = st.columns([3, 1, 1])
with c2:
    go = st.button("🔍 Research" if theme != "win98" else "🔍 OK", type="primary" if theme != "win98" else "secondary", use_container_width=True)
if theme != "win98":
    with c3:
        if st.button("🗑 Clear", use_container_width=True):
            st.session_state.query = ""
            st.session_state.result = None
            st.rerun()

# ── Run Pipeline ──
if go and query:
    st.session_state.running = True
    st.session_state.result = None
    progress_bar = st.progress(0, text="Starting agents...")
    status_area = st.empty()
    result_area = st.empty()

    AGENTS = [
        ("🌐", "Query Expansion"), ("📡", "Reddit Retrieval"), ("🧹", "Spam Filter"),
        ("⭐", "Credibility Scoring"), ("⚡", "Contradiction Detection"), ("👥", "Perspectives"),
        ("🔗", "Knowledge Graph"), ("📋", "Synthesis"), ("✅", "Fact Check"),
    ]

    def render_agents(current_idx, status_area):
        style_base = "padding:6px 10px;border-radius:8px;font-size:13px;text-align:center;transition:all 0.3s"
        html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:8px 0">'
        for i, (icon, name) in enumerate(AGENTS):
            if i < current_idx:
                style = f'{style_base};background:#1a3a2a;color:#4ade80'
                label = f"✅ {icon} {name}"
            elif i == current_idx:
                style = f'{style_base};background:#1a2a3a;color:#60a5fa;border:1px solid #60a5fa;animation:pulse 1.5s infinite'
                label = f"🔄 {icon} {name}"
            else:
                style = f'{style_base};background:#1a1a1a;color:#555'
                label = f"⏳ {icon} {name}"
            html += f'<div style="{style}">{label}</div>'
        html += '</div><style>@keyframes pulse { 0% { opacity: 0.7; } 50% { opacity: 1; } 100% { opacity: 0.7; } }</style>'
        if theme == "win98":
            status_area.markdown(html.replace("1a3a2a", "c0c0c0").replace("4ade80", "#000").replace("1a2a3a", "c0c0c0").replace("60a5fa", "#000").replace("1a1a1a", "c0c0c0").replace("#555", "#000"), unsafe_allow_html=True)
        else:
            status_area.markdown(html, unsafe_allow_html=True)

    current_step = -1
    result_data = None
    step_map = {
        "query_expansion": 0, "retrieval": 1, "spam_filtering": 2,
        "credibility_scoring": 3, "contradiction_detection": 4, "perspective_generation": 5,
        "knowledge_graph": 6, "synthesis": 7, "fact_check": 8,
    }

    for update in run_pipeline(query):
        if update["step"] == "failed":
            st.error(update.get("error", "Pipeline failed"))
            st.session_state.running = False
            result_data = None
            break
        elif update["step"] == "completed":
            result_data = update.get("data")
            progress_bar.progress(1.0, text="Complete!")
            render_agents(9, status_area)
        else:
            idx = step_map.get(update["step"], -1)
            if idx > current_step:
                current_step = idx
                progress_bar.progress((idx + 0.5) / len(AGENTS), text=update.get("message", ""))
                render_agents(idx, status_area)

    st.session_state.running = False
    if result_data:
        saved_data = save_report(result_data)
        saved_data["id"] = result_data.get("query", "?")
        st.session_state.result = saved_data
        st.rerun()

# ── Display Results ──
result = st.session_state.result
if result and not st.session_state.running:
    summary = result.get("summary", {})
    contradictions = result.get("contradictions", {})
    fc = result.get("fact_check", {})
    kg = result.get("knowledge_graph", {})
    perspectives = result.get("perspectives", [])
    posts = result.get("scored_posts", [])

    # Tabs
    tab = st.radio("View", ["📋 Summary", "👥 Perspectives", "⚡ Debates", "✅ Fact Check", "🔗 Entity Graph", "📚 Sources"],
                   horizontal=True, label_visibility="collapsed")

    with st.container():
        if "Summary" in tab:
            if theme == "win98":
                st.markdown('<div class="win98-window"><div class="win98-title"><span>📋 Answer</span><div class="win98-title-buttons"><div class="win98-title-btn">_</div><div class="win98-title-btn">□</div><div class="win98-title-btn">✕</div></div></div><div class="win98-body">', unsafe_allow_html=True)
                st.markdown(f'<div style="background:#fff;border:2px inset #ddd;padding:8px;font-size:11px;font-family:\'Microsoft Sans Serif\',monospace;line-height:1.4">{summary.get("consensus", "No data")}</div>', unsafe_allow_html=True)
                st.markdown('</div></div>', unsafe_allow_html=True)
            else:
                conf = summary.get("confidence_score", 0)
                st.markdown(
                    f'<div style="background:var(--bg-card);border:1px solid var(--border);border-left:4px solid var(--color-primary);'
                    f'border-radius:var(--radius);padding:24px;font-size:16px;line-height:1.7;margin:12px 0;box-shadow:var(--shadow)">'
                    f'<div style="display:flex;align-items:center;gap:16px;margin-bottom:16px">'
                    f'<div style="flex:1;font-size:1.1rem;font-weight:600;color:var(--text-bright)">Community Consensus</div>'
                    f'<div style="text-align:right"><div style="font-size:0.7rem;color:var(--text-dim)">Confidence</div>'
                    f'<div style="display:flex;align-items:center;gap:8px"><span style="font-size:1.5rem;font-weight:700;color:var(--text-bright)">{round(conf*100)}%</span>'
                    f'<div style="width:80px;height:8px;background:rgba(255,255,255,0.05);border-radius:4px;overflow:hidden">'
                    f'<div style="height:100%;width:{conf*100}%;background:linear-gradient(to right,var(--color-primary),var(--color-secondary));border-radius:4px"></div></div></div></div></div>'
                    f'{summary.get("consensus", "No data")}</div>',
                    unsafe_allow_html=True
                )

                if summary.get("detailed_synthesis"):
                    st.markdown(
                        f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:24px;margin:12px 0;box-shadow:var(--shadow)">'
                        f'<h3 style="color:var(--color-primary);margin:0 0 16px 0">📝 Detailed Synthesis</h3>'
                        f'<div style="line-height:1.7;font-size:15px">{render_md(summary["detailed_synthesis"])}</div></div>',
                        unsafe_allow_html=True
                    )

                # Key Insights + Recommendations side by side
                ki = summary.get("key_insights", [])
                rec = summary.get("recommendations", [])
                if ki or rec:
                    cols = st.columns(2)
                    with cols[0]:
                        if ki:
                            st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin:8px 0;box-shadow:var(--shadow)"><h4 style="color:var(--color-secondary);margin:0 0 8px 0">💡 Key Insights</h4>', unsafe_allow_html=True)
                            for ins in ki[:5]:
                                st.markdown(f'<div style="padding:3px 0;font-size:14px">• {ins}</div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                    with cols[1]:
                        if rec:
                            st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin:8px 0;box-shadow:var(--shadow)"><h4 style="color:var(--color-secondary);margin:0 0 8px 0">🎯 Recommendations</h4>', unsafe_allow_html=True)
                            for r in rec[:5]:
                                st.markdown(f'<div style="padding:3px 0;font-size:14px">• {r}</div>', unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)

        elif "Perspectives" in tab:
            if perspectives:
                cols = st.columns(3)
                for i, p in enumerate(perspectives):
                    with cols[i % 3]:
                        st.markdown(
                            f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin:4px 0;box-shadow:var(--shadow)">'
                            f'<h4 style="color:var(--color-secondary);margin:0 0 8px 0">{p.get("group","")}</h4>'
                            f'<p style="font-size:13px;color:var(--text-dim)">{p.get("angle","")}</p></div>',
                            unsafe_allow_html=True
                        )
            else:
                st.info("No perspectives identified.")

        elif "Debates" in tab:
            vps = contradictions.get("viewpoints", [])
            if vps:
                cols = st.columns(len(vps))
                for i, v in enumerate(vps):
                    pct = v.get("percentage", 0)
                    color = "#4ade80" if pct > 50 else "#facc15" if pct > 25 else "#ef4444"
                    with cols[i]:
                        st.markdown(
                            f'<div style="text-align:center;background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;box-shadow:var(--shadow)">'
                            f'<div style="font-size:32px;font-weight:bold;color:{color}">{pct}%</div>'
                            f'<div style="font-weight:bold;margin:8px 0;color:var(--text-bright)">{v.get("stance","")}</div>'
                            f'<div style="font-size:13px;color:var(--text-dim)">{v.get("summary","")[:150]}</div></div>',
                            unsafe_allow_html=True
                        )
            else:
                st.info(f"Consensus: {contradictions.get('consensus', 'No contradictions found.')}")

        elif "Fact Check" in tab:
            st.markdown(
                f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:20px;margin:8px 0;box-shadow:var(--shadow)">'
                f'<h4 style="color:var(--color-primary);margin:0 0 12px 0">Overall Assessment</h4>'
                f'<div style="font-size:1.1rem;font-weight:600;color:var(--text-bright)">{fc.get("overall_assessment","N/A")}</div>'
                f'<p style="margin-top:8px">{fc.get("recommendation","")}</p></div>',
                unsafe_allow_html=True
            )
            verified = fc.get("verified_claims", [])
            questionable = fc.get("questionable_claims", [])
            if verified:
                st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin:8px 0;box-shadow:var(--shadow)"><h5 style="color:var(--success)">✅ Verified Claims</h5>', unsafe_allow_html=True)
                for claim in verified:
                    st.markdown(f'<div style="padding:2px 0;font-size:14px">• {claim}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            if questionable:
                st.markdown(f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin:8px 0;box-shadow:var(--shadow);border-left:3px solid var(--danger)"><h5 style="color:var(--danger)">⚠️ Questionable Claims</h5>', unsafe_allow_html=True)
                for claim in questionable:
                    st.markdown(f'<div style="padding:2px 0;font-size:14px">• {claim}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

        elif "Entity Graph" in tab:
            nodes = kg.get("nodes", [])
            edges = kg.get("edges", [])
            if nodes:
                st.markdown(f'<div style="margin-bottom:8px;font-size:13px;color:var(--text-dim)">{len(nodes)} entities, {len(edges)} relationships</div>', unsafe_allow_html=True)
                graph_svg = render_force_graph(nodes, edges)
                st.markdown(graph_svg, unsafe_allow_html=True)
                # Legend
                cols = st.columns(4)
                for c, label in [(cols[0], ("#f97316","Hardware")), (cols[1], ("#10b981","Software")), (cols[2], ("#0ea5e9","Concept")), (cols[3], ("#ec4899","Org"))]:
                    color, name = label
                    c.markdown(f'<div style="display:flex;align-items:center;gap:6px;font-size:12px"><div style="width:10px;height:10px;border-radius:50%;background:{color}"></div>{name}</div>', unsafe_allow_html=True)
            else:
                st.info("No entities extracted for knowledge graph.")

        elif "Sources" in tab:
            st.markdown(f'<h4 style="color:var(--color-primary)">📚 Source Threads ({len(posts)})</h4>', unsafe_allow_html=True)
            for i, p in enumerate(posts[:10], 1):
                cred = p.get("credibility", "")
                cred_str = f" • Credibility: {cred}/10" if cred else ""
                st.markdown(
                    f'<div style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:12px 16px;margin:6px 0;box-shadow:var(--shadow)">'
                    f'<div style="font-weight:600;color:var(--text-bright);font-size:14px">{p.get("title","")}</div>'
                    f'<div style="font-size:13px;color:var(--text-dim)">r/{p.get("subreddit","")}{cred_str}</div>'
                    f'<div style="font-size:12px;margin-top:4px"><a href="{p.get("url","")}" target="_blank" style="color:var(--accent)">Open thread ↗</a></div></div>',
                    unsafe_allow_html=True
                )

        # Caveats
        if summary.get("caveats"):
            with st.expander("⚠️ Caveats"):
                for c in summary["caveats"]:
                    st.markdown(f"- {c}")

# ── Close Win98 ──
if theme == "win98" and WINDOW_OPEN:
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    now_t = time.strftime("%I:%M %p").lstrip("0").replace("  ", " ")
    task_label = "📋 Answer" if st.session_state.result else "Ready"
    st.markdown(f"""
    <div class="win98-taskbar">
        <div class="win98-start" onclick="var p=document.getElementById('wpopup');p.style.display=p.style.display==='none'?'block':'none'">
            <span style="font-size:14px">🖥</span> Start
        </div>
        <div class="win98-taskbar-divider"></div>
        <div class="win98-taskbar-item active">{task_label}</div>
        <div class="win98-taskbar-time">{now_t}</div>
    </div>
    <div class="win98-popup" id="wpopup" style="display:none">
        <div class="win98-popup-item" onclick="document.getElementById('wpopup').style.display='none'">🔍 Reddit Intelligence Engine</div>
        <div class="win98-popup-item" onclick="document.getElementById('wpopup').style.display='none'">📁 My Queries</div>
        <div class="win98-separator"></div>
        <div class="win98-popup-item" onclick="document.getElementById('wpopup').style.display='none'">💾 Saved Reports</div>
        <div class="win98-separator"></div>
        <div class="win98-popup-item" onclick="document.getElementById('wpopup').style.display='none'">⚙ Settings</div>
        <div class="win98-popup-item" onclick="document.getElementById('wpopup').style.display='none'">❓ Help</div>
    </div>
    <script>
        document.addEventListener('click',function(e){{var p=document.getElementById('wpopup');var b=document.querySelector('.win98-start');if(p&&b&&!b.contains(e.target)&&!p.contains(e.target))p.style.display='none';}});
    </script>
    """, unsafe_allow_html=True)


