import os
import streamlit as st
import pickle
import pandas as pd
from build_graph import MemoryGraph

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH_PATH = os.path.join(BASE_DIR, "memory_graph.pkl")

st.set_page_config(
    layout="wide",
    page_title="Enron Memory Graph",
    page_icon="🕵️",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

/* ── Root palette ── */
:root {
    --bg:        #0f1117;
    --surface:   #161b27;
    --border:    #1e2a3a;
    --accent:    #f0a500;
    --accent2:   #e05252;
    --text:      #c9d1e0;
    --muted:     #5a6a82;
    --mono:      'IBM Plex Mono', monospace;
    --sans:      'IBM Plex Sans', sans-serif;
}

/* ── Global reset ── */
html, body, [class*="css"] {
    font-family: var(--sans);
    background-color: var(--bg);
    color: var(--text);
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem 4rem; max-width: 1400px; }

/* ── Header banner ── */
.enron-header {
    display: flex;
    align-items: center;
    gap: 1.2rem;
    border-bottom: 2px solid var(--accent);
    padding-bottom: 1rem;
    margin-bottom: 2rem;
}
.enron-header .title {
    font-family: var(--mono);
    font-size: 1.6rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin: 0;
}
.enron-header .subtitle {
    font-size: 0.78rem;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 0;
}
.badge {
    background: var(--accent);
    color: #000;
    font-family: var(--mono);
    font-size: 0.65rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 2px;
    letter-spacing: 0.08em;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }
[data-testid="stSidebar"] label {
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    color: var(--muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stMultiSelect > div > div {
    background-color: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.82rem !important;
}
.sidebar-section {
    font-family: var(--mono);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--accent);
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
    margin: 1.4rem 0 0.8rem;
}

/* ── Stat cards ── */
.stat-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
}
.stat-card {
    flex: 1;
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: 2px solid var(--accent);
    padding: 1rem 1.2rem;
    border-radius: 4px;
}
.stat-card .value {
    font-family: var(--mono);
    font-size: 2rem;
    font-weight: 600;
    color: var(--accent);
    line-height: 1;
}
.stat-card .label {
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 4px;
}

/* ── Section headings ── */
.section-heading {
    font-family: var(--mono);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
    margin: 1.8rem 0 1rem;
}

/* ── Claim table ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    overflow: hidden;
}
[data-testid="stDataFrame"] thead th {
    background: var(--surface) !important;
    color: var(--accent) !important;
    font-family: var(--mono) !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
[data-testid="stDataFrame"] tbody tr:hover { background: var(--border) !important; }

/* ── Claim detail panel ── */
.claim-panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 4px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
}
.claim-panel .claim-text {
    font-size: 1.0rem;
    line-height: 1.65;
    color: var(--text);
}
.meta-row {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-top: 0.8rem;
}
.meta-pill {
    font-family: var(--mono);
    font-size: 0.7rem;
    padding: 3px 10px;
    border-radius: 2px;
    letter-spacing: 0.06em;
}
.meta-pill.type  { background: #1a2535; color: #7aadda; border: 1px solid #2a3d56; }
.meta-pill.conf  { background: #1a2a1a; color: #7ac97a; border: 1px solid #2a4a2a; }
.meta-pill.conf-low { background: #2a1a1a; color: var(--accent2); border: 1px solid #4a2a2a; }

/* ── Evidence cards ── */
.evidence-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.7rem;
}
.evidence-card .ev-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 0.6rem;
}
.ev-msg-id {
    font-family: var(--mono);
    font-size: 0.72rem;
    color: var(--accent);
    letter-spacing: 0.06em;
}
.ev-meta {
    font-family: var(--mono);
    font-size: 0.68rem;
    color: var(--muted);
}
.ev-excerpt {
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--text);
    border-left: 2px solid var(--border);
    padding-left: 0.8rem;
    margin-top: 0.5rem;
}

/* ── Confidence bar ── */
.conf-bar-wrap {
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    margin-top: 6px;
    overflow: hidden;
}
.conf-bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.4s ease;
}

/* ── Expander override ── */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
}
[data-testid="stExpander"] summary {
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    color: var(--text) !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.84rem !important;
}

/* ── Slider ── */
[data-testid="stSlider"] .rc-slider-track { background-color: var(--accent) !important; }
[data-testid="stSlider"] .rc-slider-handle {
    border-color: var(--accent) !important;
    background: var(--accent) !important;
}

/* ── Empty state ── */
.empty-state {
    text-align: center;
    padding: 3rem 0;
    color: var(--muted);
    font-family: var(--mono);
    font-size: 0.85rem;
    letter-spacing: 0.1em;
}
.empty-state .icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# ── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="enron-header">
    <div>
        <p class="title">🕵 Enron Memory Graph</p>
        <p class="subtitle">Claim Intelligence Explorer · Forensic Edition</p>
    </div>
    <span class="badge">INTERNAL</span>
</div>
""", unsafe_allow_html=True)


# ── Load graph ───────────────────────────────────────────────────────────────
@st.cache_resource
def load_graph():
    with open(GRAPH_PATH, "rb") as f:
        return pickle.load(f)

graph = load_graph()


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-section">Actor</div>', unsafe_allow_html=True)
    actors = sorted(graph.claim_actor_edges.keys())
    selected_actor = st.selectbox("Select Actor", actors, label_visibility="collapsed")

    st.markdown('<div class="sidebar-section">Claim Type</div>', unsafe_allow_html=True)
    claim_types = sorted(set(c["type"] for c in graph.claims.values()))
    selected_type = st.multiselect("Claim Type", claim_types, default=claim_types, label_visibility="collapsed")

    st.markdown('<div class="sidebar-section">Confidence</div>', unsafe_allow_html=True)
    min_conf = st.slider("Minimum Confidence", 0.0, 1.0, 0.5, label_visibility="collapsed")

    st.markdown('<div class="sidebar-section">Time Filter</div>', unsafe_allow_html=True)
    years = sorted(set(
        ev["timestamp"][:4]
        for c in graph.claims.values()
        for ev in c.get("evidence", [])
        if ev.get("timestamp")
    ))
    selected_year = st.selectbox("Year", ["All"] + years, label_visibility="collapsed", key="year_filter")

    st.markdown("---")
    st.markdown(f'<div style="font-family:var(--mono);font-size:0.65rem;color:#5a6a82;">TOTAL ACTORS: {len(actors)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-family:var(--mono);font-size:0.65rem;color:#5a6a82;">TOTAL CLAIMS: {len(graph.claims)}</div>', unsafe_allow_html=True)


# ── Filter claims ─────────────────────────────────────────────────────────────
claim_ids = graph.claim_actor_edges.get(selected_actor, [])
claims = [graph.claims[cid] for cid in claim_ids]
filtered_claims = []
for c in claims:
    if c["type"] not in selected_type:
        continue
    if c["confidence"] < min_conf:
        continue
    if selected_year != "All":
        if not any(ev.get("timestamp", "")[:4] == selected_year for ev in c.get("evidence", [])):
            continue
    filtered_claims.append(c)


# ── Stat cards ────────────────────────────────────────────────────────────────
avg_conf = round(sum(c["confidence"] for c in filtered_claims) / len(filtered_claims), 2) if filtered_claims else 0
type_counts = {}
for c in filtered_claims:
    type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1
top_type = max(type_counts, key=type_counts.get) if type_counts else "—"

st.markdown(f"""
<div class="stat-row">
    <div class="stat-card">
        <div class="value">{len(filtered_claims)}</div>
        <div class="label">Filtered Claims</div>
    </div>
    <div class="stat-card">
        <div class="value">{avg_conf}</div>
        <div class="label">Avg Confidence</div>
    </div>
    <div class="stat-card">
        <div class="value">{len(type_counts)}</div>
        <div class="label">Claim Types</div>
    </div>
    <div class="stat-card">
        <div class="value" style="font-size:1.1rem;padding-top:4px">{top_type}</div>
        <div class="label">Most Common Claim Type</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Claims table ──────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-heading">Claims by {selected_actor}</div>', unsafe_allow_html=True)

if not filtered_claims:
    st.markdown("""
    <div class="empty-state">
        <div class="icon">⚠</div>
        No claims match the current filters.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

claim_df = pd.DataFrame([
    {
        "Type": c["type"],
        "Content": c["content"][:120] + ("…" if len(c["content"]) > 120 else ""),
        "Confidence": round(c["confidence"], 2),
    }
    for c in filtered_claims
])
st.dataframe(claim_df, use_container_width=True, hide_index=True)


# ── Claim detail ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-heading">Claim Detail & Evidence</div>', unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    selected_index = st.selectbox(
        "Select claim",
        options=list(range(len(filtered_claims))),
        format_func=lambda i: filtered_claims[i]["content"][:100],
        label_visibility="collapsed",
        key="claim_select",
    )

claim = filtered_claims[selected_index]
conf = claim["confidence"]
conf_color = "#7ac97a" if conf >= 0.7 else ("#f0a500" if conf >= 0.4 else "#e05252")
conf_pct = int(conf * 100)

st.markdown(f"""
<div class="claim-panel">
    <div class="claim-text">{claim["content"]}</div>
    <div class="meta-row">
        <span class="meta-pill type">{claim["type"]}</span>
        <span class="meta-pill {'conf' if conf >= 0.5 else 'conf-low'}">confidence: {conf:.2f}</span>
    </div>
    <div class="conf-bar-wrap" style="margin-top:10px">
        <div class="conf-bar-fill" style="width:{conf_pct}%;background:{conf_color}"></div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Evidence ──────────────────────────────────────────────────────────────────
evidence = claim.get("evidence", [])
st.markdown(f'<div class="section-heading">Evidence &nbsp;·&nbsp; {len(evidence)} source{"s" if len(evidence) != 1 else ""}</div>', unsafe_allow_html=True)

if not evidence:
    st.markdown('<div class="empty-state"><div class="icon">📭</div>No evidence records.</div>', unsafe_allow_html=True)
else:
    for ev in evidence:
        st.markdown(f"""
        <div class="evidence-card">
            <div class="ev-header">
                <span class="ev-msg-id">MSG {ev['message_id']}</span>
                <span class="ev-meta">⏱ {ev['timestamp']}</span>
                <span class="ev-meta">🧵 Thread {ev['thread_id']}</span>
            </div>
            <div class="ev-excerpt">{ev['excerpt']}</div>
        </div>
        """, unsafe_allow_html=True)