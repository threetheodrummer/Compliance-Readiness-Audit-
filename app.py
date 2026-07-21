"""
Compliance Readiness Audit — Streamlit edition
A self-assessment tool covering GDPR, DPDP Act 2023, and NIS2, with independent
50-question banks per mode plus a combined view. Generates a downloadable PDF report.

Visual system: "Modernist" — flat/architectural, zero border-radius, thick 2px
dividers, Archivo type, single red accent on off-white (light) / near-black (dark).
"""

import json
import io
import datetime
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

# ---------------------------------------------------------------------------
# Data loading (UNCHANGED — same data.json, same schema)
# ---------------------------------------------------------------------------
DATA_PATH = Path(__file__).parent / "data.json"
DATA = json.loads(DATA_PATH.read_text(encoding="utf-8"))

BANKS = {
    "GDPR": ("CATEGORIES_GDPR", "QUESTIONS_GDPR"),
    "DPDP": ("CATEGORIES_DPDP", "QUESTIONS_DPDP"),
    "NIS2": ("CATEGORIES_NIS2", "QUESTIONS_NIS2"),
    "BOTH": ("CATEGORIES_BOTH", "QUESTIONS_BOTH"),
    "ALL": ("CATEGORIES_ALL", "QUESTIONS_ALL"),
}

MODE_LABELS = {
    "GDPR": "GDPR",
    "DPDP": "DPDP",
    "NIS2": "NIS2",
    "BOTH": "GDPR & DPDP",
    "ALL": "All three",
}

MODE_KICKER = {
    "GDPR": "EU · Data protection",
    "DPDP": "India · Data protection",
    "NIS2": "EU · Cybersecurity",
    "BOTH": "EU + India · Combined",
    "ALL": "EU + India · Comprehensive",
}

MODE_DESC = {
    "GDPR": "General Data Protection Regulation — governs how EU personal data is collected, processed, and stored.",
    "DPDP": "Digital Personal Data Protection Act, 2023 — consent, rights, and breach obligations for personal data in India.",
    "NIS2": "Network and Information Security Directive 2 — cybersecurity risk management for essential and important entities.",
    "BOTH": "GDPR and DPDP assessed together, side by side, for organizations spanning both the EU and India.",
    "ALL": "GDPR, DPDP, and NIS2 combined into one representative cross-framework readiness check.",
}

FRAMEWORK_TEXT = {
    "GDPR": "the EU GDPR only",
    "DPDP": "India's DPDP Act, 2023 only",
    "NIS2": "the EU NIS2 Directive only (cybersecurity risk management, not personal data)",
    "BOTH": "both India's DPDP Act 2023 and the EU GDPR, side by side",
    "ALL": "GDPR, DPDP, and NIS2 together — a representative cross-framework set",
}

ASSESSED_LABEL = {
    "GDPR": "EU GDPR",
    "DPDP": "DPDP Act, 2023",
    "NIS2": "EU NIS2 Directive",
    "BOTH": "DPDP Act 2023 & EU GDPR",
    "ALL": "GDPR, DPDP Act 2023 & NIS2 Directive",
}

# Company-profile questions. Each maps to the "requires" tag on questions in data.json.
# A question tagged with a key here is only shown if that profile flag is True.
# Untagged (requires: null) questions are always shown, regardless of profile.
PROFILE_FIELDS = [
    ("children_data", "Does your organization process children's or minors' personal data?"),
    ("special_category_data", "Does it process special category / sensitive data (health, biometric, genetic, financial, sexual orientation, etc.)?"),
    ("automated_decision_making", "Does it use automated decision-making or profiling that significantly affects individuals?"),
    ("cross_border_transfer", "Does it transfer personal data across international borders?"),
    ("third_party_vendors", "Does it use third-party vendors, processors, or cloud suppliers to handle personal data?"),
    ("non_eu_established", "Is it established outside the EU while offering goods/services to, or monitoring, individuals in the EU?"),
    ("significant_entity", "Would it likely qualify as a Significant Data Fiduciary (DPDP), large-scale processor, or an Essential/Important Entity (NIS2)?"),
    ("critical_sector", "Does it operate in a sector treated as critical or important under NIS2 (energy, health, transport, banking, digital infrastructure, water, waste management, public administration, etc.)?"),
    ("sectoral_data_india", "Does it process payment, financial, telecom, or insurance data subject to India-specific sectoral localization rules (e.g. RBI, telecom, insurance)?"),
    ("physical_premises", "Does it operate physical premises or on-premises servers (i.e. not fully cloud-based)?"),
]

OPTIONS = ["Yes", "Partial", "No", "N/A"]
OPTION_VAL = {"Yes": 1.0, "Partial": 0.5, "No": 0.0, "N/A": None}

STEP_DEFS = [
    ("intro", "1. Framework"),
    ("profile", "2. Company"),
    ("wizard", "3. Questionnaire"),
    ("results", "4. Results"),
]

# ---------------------------------------------------------------------------
# Design tokens — "Modernist": flat, zero-radius, single red accent
# ---------------------------------------------------------------------------
ACCENT = "#ec3013"
ACCENT_600 = "#dd2b0f"
ACCENT_700 = "#ae1800"
ACCENT_800 = "#7c1405"
ACCENT_400 = "#ff9783"
ACCENT_300 = "#ffc4b8"
ACCENT_100 = "#fff2ef"

# Traffic-light semantic colors (severity / pass-fail), independent of the brand accent
GREEN = "#1e8f4e"
GREEN_LIGHT = "#e6f4ec"
GREEN_DARK = "#155c33"
YELLOW = "#e6a817"
YELLOW_LIGHT = "#fdf3e0"
RED = "#ec3013"       # same as ACCENT — the brand color IS red, so critical reuses it
RED_LIGHT = "#fff2ef"


def theme_tokens(dark: bool) -> dict:
    if dark:
        return dict(
            bg="#161413", surface="#201e1d", surface2="#2a2726", text="#f3f2f2",
            divider="rgba(243,242,242,0.35)", muted="rgba(243,242,242,0.55)",
            neutral_300="#3a3736", neutral_400="#5a5654",
        )
    return dict(
        bg="#f3f2f2", surface="#eae9e9", surface2="#e0dedd", text="#201e1d",
        divider="rgba(32,30,29,0.4)", muted="rgba(32,30,29,0.55)",
        neutral_300="#d7d3d3", neutral_400="#bab6b6",
    )


PDF_TEXT = (32 / 255, 30 / 255, 29 / 255)
PDF_MUTED = (100 / 255, 96 / 255, 96 / 255)
PDF_ACCENT = (236 / 255, 48 / 255, 19 / 255)
PDF_ACCENT_700 = (174 / 255, 24 / 255, 0 / 255)
PDF_ACCENT_400 = (255 / 255, 151 / 255, 131 / 255)
PDF_GREEN = (30 / 255, 143 / 255, 78 / 255)
PDF_YELLOW = (230 / 255, 168 / 255, 23 / 255)
PDF_RED = (236 / 255, 48 / 255, 19 / 255)
PDF_NEUTRAL = (186 / 255, 182 / 255, 182 / 255)

# Lucide-style inline icons (24x24, stroke-based) used inside raw HTML blocks
ICON_CHECK = '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'
ICON_X = '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'
ICON_ALERT = '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
ICON_MINUS = '<svg width="{s}" height="{s}" viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>'


def grade_for(score: float):
    """UNCHANGED thresholds/letters (data logic) — colors now traffic-light (green/yellow/red)."""
    if score >= 90:
        return "A", GREEN, PDF_GREEN
    if score >= 80:
        return "B", GREEN, PDF_GREEN
    if score >= 70:
        return "C", YELLOW, PDF_YELLOW
    if score >= 60:
        return "D", RED, PDF_RED
    return "F", RED, PDF_RED


def format_ref(ref) -> str:
    if isinstance(ref, str):
        return ref
    return f"DPDP {ref.get('DPDP', '—')} · GDPR {ref.get('GDPR', '—')}"


def get_categories(mode):
    return DATA[BANKS[mode][0]]


def get_questions(mode):
    return DATA[BANKS[mode][1]]


def applicable_questions(mode):
    """Questions relevant to the current company profile: untagged questions always
    included; tagged questions included only if that profile flag is checked True."""
    profile = st.session_state.get("profile", {})
    return [
        q for q in get_questions(mode)
        if not q.get("requires") or profile.get(q["requires"], True)
    ]


def questions_by_category(mode):
    cats = get_categories(mode)
    qs = applicable_questions(mode)
    return {c["id"]: [q for q in qs if q["cat"] == c["id"]] for c in cats}


def active_categories(mode):
    """Categories that still have at least one applicable question for this profile,
    with weights renormalized to sum to 1 so scoring stays fair when categories drop out."""
    by_cat = questions_by_category(mode)
    cats = [c for c in get_categories(mode) if by_cat[c["id"]]]
    total_weight = sum(c["weight"] for c in cats) or 1
    return [{**c, "weight": c["weight"] / total_weight} for c in cats]


# ---------------------------------------------------------------------------
# Session state (UNCHANGED, + "dark" for the new theme toggle)
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "screen": "intro",
        "mode": None,
        "org_name": "",
        "answers": {},   # {mode: {qid: option_str}}
        "cat_index": 0,
        "profile": {key: True for key, _ in PROFILE_FIELDS},  # inclusive by default
        "dark": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_answers():
    return st.session_state["answers"].setdefault(st.session_state["mode"], {})


def compute_results(mode):
    """UNCHANGED scoring logic."""
    cats = active_categories(mode)
    by_cat = questions_by_category(mode)
    answers = st.session_state["answers"].get(mode, {})

    per_category = []
    for c in cats:
        qs = by_cat[c["id"]]
        scored = [OPTION_VAL[answers[q["id"]]] for q in qs if q["id"] in answers and OPTION_VAL[answers[q["id"]]] is not None]
        score = (sum(scored) / len(scored) * 100) if scored else 0.0
        per_category.append({**c, "score": score})

    overall = sum(c["score"] * c["weight"] for c in per_category)

    gaps = []
    for q in applicable_questions(mode):
        ans = answers.get(q["id"])
        if ans in ("No", "Partial"):
            cat = next(c for c in cats if c["id"] == q["cat"])
            severity = ("Critical" if cat["weight"] >= 0.2 else "High") if ans == "No" else "Medium"
            gaps.append({**q, "severity": severity, "cat_label": cat["label"]})
    sev_order = {"Critical": 0, "High": 1, "Medium": 2}
    gaps.sort(key=lambda g: sev_order[g["severity"]])

    return per_category, overall, gaps


def status_breakdown(mode):
    """Passed/Warning/Failed/Not-applicable counts across the FULL 50-question bank,
    matching the reference design's 'Results breakdown' panel."""
    all_qs = get_questions(mode)
    applicable_ids = {q["id"] for q in applicable_questions(mode)}
    answers = st.session_state["answers"].get(mode, {})
    counts = {"Passed": 0, "Warning": 0, "Failed": 0, "Not applicable": 0}
    for q in all_qs:
        if q["id"] not in applicable_ids:
            counts["Not applicable"] += 1
            continue
        ans = answers.get(q["id"])
        if ans == "Yes":
            counts["Passed"] += 1
        elif ans == "Partial":
            counts["Warning"] += 1
        elif ans == "No":
            counts["Failed"] += 1
        else:
            counts["Not applicable"] += 1
    return counts


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
def inject_css():
    t = theme_tokens(st.session_state["dark"])
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700;800&display=swap');

    * {{ border-radius: 0 !important; }}
    .stApp {{ background-color: {t['bg']}; color: {t['text']}; font-family: 'Archivo', system-ui, sans-serif; }}
    h1, h2, h3, h4 {{ font-family: 'Archivo', system-ui, sans-serif !important; font-weight: 800 !important;
                       color: {t['text']} !important; letter-spacing: -0.015em; line-height: 1.12; }}
    p, li, label, span, div {{ font-family: 'Archivo', system-ui, sans-serif; }}

    .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1360px; }}
    header[data-testid="stHeader"] {{ display: none !important; }}
    div[data-testid="stToolbar"] {{ display: none !important; }}

    .kicker {{ font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: {ACCENT}; margin-bottom: 4px; }}
    .muted {{ color: {t['muted']}; }}
    .lede {{ color: {t['muted']}; font-size: 15px; line-height: 1.6; }}
    .mono {{ font-family: 'Archivo', monospace; font-variant-numeric: tabular-nums; }}
    .ledger-hr {{ height: 2px; border: 0; margin: 18px 0; background: {t['divider']}; }}

    /* — nav bar — */
    .nav-brand {{ font-size: 20px; font-weight: 800; letter-spacing: -0.02em; padding-top: 4px; }}

    /* — buttons: flat, zero radius — */
    div.stButton > button, div.stDownloadButton > button {{
        font-family: 'Archivo', sans-serif !important; font-weight: 800 !important; font-size: 14px !important;
        border-radius: 0 !important; padding: 10px 18px !important; transition: background-color .15s ease;
    }}
    [data-testid="stBaseButton-primary"], [data-testid="baseButton-primary"] {{
        background-color: {ACCENT} !important; color: {t['bg']} !important; border: 1px solid {ACCENT} !important;
    }}
    [data-testid="stBaseButton-primary"]:hover, [data-testid="baseButton-primary"]:hover {{ background-color: {ACCENT_600} !important; }}
    [data-testid="stBaseButton-secondary"], [data-testid="baseButton-secondary"] {{
        background-color: transparent !important; color: {t['text']} !important; border: 1px solid {t['divider']} !important;
    }}
    [data-testid="stBaseButton-secondary"]:hover, [data-testid="baseButton-secondary"]:hover {{
        background-color: {t['surface']} !important;
    }}
    [class*="st-key-navghost_"] button {{
        background: transparent !important; border: none !important; color: {t['muted']} !important;
        font-weight: 600 !important; padding: 4px 8px !important; font-size: 14px !important;
    }}
    [class*="st-key-navghost_"] button:hover {{ color: {ACCENT} !important; background: transparent !important; }}

    [class*="st-key-darktoggle_wrap"] button {{
        background: transparent !important; border: 1px solid {t['divider']} !important; color: {t['text']} !important;
        font-size: 22px !important; line-height: 1 !important; padding: 0 !important;
        width: 46px !important; height: 46px !important; min-height: 46px !important; min-width: 46px !important;
    }}
    [class*="st-key-darktoggle_wrap"] button:hover {{ background: {t['surface']} !important; border-color: {ACCENT} !important; }}

    /* — step tracker — */
    .step-track {{ display: flex; gap: 22px; font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase;
                    padding: 14px 0; border-bottom: 2px solid {t['divider']}; margin-bottom: 26px; }}
    .step-done {{ color: {t['muted']}; }}
    .step-current {{ color: {ACCENT}; font-weight: 800; }}
    .step-upcoming {{ color: {t['neutral_400']}; }}

    /* — framework/mode card grid (shared dividers, zero gap) — */
    [class*="st-key-fwcard_"] {{
        border: 1px solid {t['divider']}; border-left: none; padding: 20px 18px; transition: all .2s ease;
        display: flex; flex-direction: column; min-height: 230px;
    }}
    [class*="st-key-fwcard_"]:hover {{ background: {t['surface']}; }}
    [class*="st-key-fwgroup_"] {{ border-left: 1px solid {t['divider']}; }}
    .card-title {{ font-size: 19px; font-weight: 800; margin: 2px 0 8px 0; }}
    .card-body {{ font-size: 13px; opacity: 0.8; flex: 1; margin-bottom: 10px; line-height: 1.5; }}
    .card-meta {{ font-size: 11px; color: {t['muted']}; margin-bottom: 12px; }}

    /* — custom checkboxes: square, flat, accent fill — */
    [data-testid="stCheckbox"] label span:first-child {{
        border-radius: 0 !important; border: 1.5px solid {t['divider']} !important; width: 18px !important; height: 18px !important;
        background: transparent !important;
    }}
    [data-testid="stCheckbox"] input:checked + div span:first-child,
    [data-testid="stCheckbox"] label div[data-checked="true"] span:first-child {{
        background: {ACCENT} !important; border-color: {ACCENT} !important;
    }}
    [data-testid="stCheckbox"] p {{ font-size: 13.5px !important; color: {t['muted']}; }}

    /* — radio rows: bordered row + dot, vertical stack — */
    [data-testid="stRadio"] > div {{ gap: 0 !important; flex-direction: column !important; }}
    [data-testid="stRadio"] label {{
        border: 1px solid {t['divider']}; padding: 12px 14px !important; margin: -1px 0 0 0 !important;
        width: 100%; transition: background-color .12s ease;
    }}
    [data-testid="stRadio"] label:hover {{ background: {t['surface']}; }}
    [data-testid="stRadio"] label p {{ font-size: 14px !important; color: {t['text']} !important; }}

    /* — progress bar — */
    div[data-testid="stProgress"] > div > div {{ background: {t['neutral_300']} !important; height: 4px !important; }}
    div[data-testid="stProgress"] > div > div > div {{ background: {ACCENT} !important; }}

    /* — info popover, subtle button + FORCED readable panel colors — */
    [class*="st-key-info_"] button {{
        background: transparent !important; border: 1px solid transparent !important; color: {t['muted']} !important;
        width: 22px !important; height: 22px !important; min-height: 22px !important; min-width: 22px !important;
        padding: 0 !important; font-size: 10px !important; opacity: 0.7 !important;
    }}
    [class*="st-key-info_"] button:hover {{ opacity: 1 !important; color: {ACCENT} !important; border-color: {ACCENT} !important; }}
    [class*="st-key-info_"] [data-testid="stIconMaterial"],
    [class*="st-key-info_"] [data-testid*="chevron"] {{ display: none !important; }}
    div[data-baseweb="popover"], div[data-baseweb="popover"] * {{
        background-color: {t['surface']} !important;
    }}
    div[data-baseweb="popover"] {{ border: 1px solid {t['divider']} !important; border-radius: 0 !important; }}
    div[data-baseweb="popover"] p, div[data-baseweb="popover"] div, div[data-baseweb="popover"] span {{
        color: {t['text']} !important;
    }}
    div[data-baseweb="popover"] .kicker {{ color: {ACCENT} !important; }}

    /* — bars (score bar, breakdown bars, category bars) — */
    .bar-track {{ height: 8px; background: {t['neutral_300']}; overflow: hidden; }}
    .bar-fill {{ height: 100%; transition: width .5s ease; }}
    .score-track {{ height: 10px; background: {t['neutral_300']}; overflow: hidden; margin: 10px 0 24px 0; }}
    .score-fill {{ height: 100%; background: {ACCENT}; transition: width .6s ease; }}

    /* — tags — */
    .ftag {{ display: inline-flex; align-items: center; gap: 5px; font-size: 11px; padding: 3px 10px; letter-spacing: 0.02em; }}
    .tag-passed {{ background: {GREEN_LIGHT}; color: {GREEN_DARK}; }}
    .tag-warning {{ background: {YELLOW_LIGHT}; color: #8a6200; border: 1px solid {YELLOW}; }}
    .tag-failed {{ background: {RED}; color: {t['bg']}; }}
    .tag-na {{ background: {t['neutral_300']}; color: {t['muted']}; }}

    /* — findings rows — */
    .finding-row {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 14px;
                     padding: 12px 0; border-bottom: 1px solid {t['divider']}; }}

    /* — grade chip — */
    .grade-chip {{ display: inline-flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 800;
                    width: 58px; height: 58px; }}

    @keyframes screenFadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    [class*="st-key-screen_"] {{ animation: screenFadeIn 0.4s cubic-bezier(0.2,0.7,0.3,1); }}
    </style>
    """, unsafe_allow_html=True)


def grade_chip_html(letter, color):
    tint = {GREEN: GREEN_LIGHT, YELLOW: YELLOW_LIGHT, RED: RED_LIGHT}.get(color, RED_LIGHT)
    return f'<div class="grade-chip" style="background:{tint};color:{color}">{letter}</div>'


# ---------------------------------------------------------------------------
# Nav bar + step tracker
# ---------------------------------------------------------------------------
def render_nav_and_steps():
    t = theme_tokens(st.session_state["dark"])
    col1, col2, col3 = st.columns([6, 1, 1])
    with col1:
        st.markdown('<div class="nav-brand">COMPLIANCE READINESS AUDIT</div>', unsafe_allow_html=True)
    with col2:
        if st.session_state["screen"] != "intro":
            with st.container(key="navghost_restart"):
                if st.button("Start over", key="restart_top"):
                    _reset_all()
                    st.rerun()
    with col3:
        with st.container(key="darktoggle_wrap"):
            icon = "☀" if st.session_state["dark"] else "☾"
            if st.button(icon, key="dark_toggle"):
                st.session_state["dark"] = not st.session_state["dark"]
                st.rerun()
    st.markdown('<hr class="ledger-hr" style="margin-top:6px;">', unsafe_allow_html=True)

    steps_html = '<div class="step-track">'
    order = ["intro", "profile", "wizard", "results"]
    current_idx = order.index(st.session_state["screen"])
    for i, (key, label) in enumerate(STEP_DEFS):
        cls = "step-current" if i == current_idx else ("step-done" if i < current_idx else "step-upcoming")
        steps_html += f'<div class="{cls}">{label}</div>'
    steps_html += "</div>"
    st.markdown(steps_html, unsafe_allow_html=True)


def _reset_all():
    st.session_state["screen"] = "intro"
    st.session_state["mode"] = None
    st.session_state["org_name"] = ""
    st.session_state["answers"] = {}
    st.session_state["cat_index"] = 0


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------
def render_intro():
    st.markdown("# Which regulation are you checking against?")
    st.markdown('<p class="lede">Pick a framework to start a guided compliance questionnaire — '
                 'each is its own dedicated 50-question set.</p>', unsafe_allow_html=True)

    st.session_state["org_name"] = st.text_input(
        "Company name", value=st.session_state["org_name"], placeholder="Acme Inc.", key="org_name_intro"
    )
    st.write("")

    order = ["GDPR", "DPDP", "NIS2", "BOTH", "ALL"]
    cols = st.columns(len(order), gap="small")
    for i, (col, key) in enumerate(zip(cols, order)):
        with col:
            with st.container(key=f"fwcard_{key}"):
                st.markdown(f'<div class="kicker">{MODE_KICKER[key]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="card-title">{MODE_LABELS[key]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="card-body">{MODE_DESC[key]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="card-meta">50 questions · ~15 min</div>', unsafe_allow_html=True)
                if st.button(f"Select {MODE_LABELS[key]}", key=f"select_{key}", type="primary", use_container_width=True):
                    st.session_state["mode"] = key
                    st.session_state["screen"] = "profile"
                    st.rerun()


def render_profile():
    mode = st.session_state["mode"]
    _, mid, _ = st.columns([1, 10, 1])
    with mid:
        st.markdown("# Company brief")
        st.markdown(
            f'<p class="lede">Checking against <strong style="color:{ACCENT}">{MODE_LABELS[mode]}</strong> '
            "— tick what applies to your organization so we only ask about the relevant rules.</p>",
            unsafe_allow_html=True,
        )

        st.session_state["org_name"] = st.text_input(
            "Company name", value=st.session_state["org_name"], placeholder="Acme Inc.", key="org_name_profile"
        )
        st.markdown('<hr class="ledger-hr">', unsafe_allow_html=True)

        for key, label in PROFILE_FIELDS:
            st.session_state["profile"][key] = st.checkbox(
                label, value=st.session_state["profile"].get(key, True), key=f"profile_{key}"
            )

        q_count = len(applicable_questions(mode))
        c_count = len(active_categories(mode))
        st.markdown(
            f'<p class="lede">Based on this profile, you\'ll answer <span class="mono" '
            f'style="color:{ACCENT}">{q_count}</span> of 50 questions across '
            f'<span class="mono" style="color:{ACCENT}">{c_count}</span> control areas.</p>',
            unsafe_allow_html=True,
        )

        st.write("")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Back", key="profile_back"):
                st.session_state["screen"] = "intro"
                st.rerun()
        with col2:
            if st.button("Start questionnaire", key="profile_continue", type="primary"):
                st.session_state["screen"] = "wizard"
                st.session_state["cat_index"] = 0
                st.session_state["answers"][mode] = {}
                st.rerun()


def render_wizard():
    mode = st.session_state["mode"]
    cats = active_categories(mode)
    by_cat = questions_by_category(mode)
    idx = st.session_state["cat_index"]
    cat = cats[idx]
    qs = by_cat[cat["id"]]
    answers = get_answers()

    _, mid, _ = st.columns([1, 10, 1])
    with mid:
        st.markdown(f'<div class="kicker">SECTION {idx + 1} OF {len(cats)}</div>', unsafe_allow_html=True)
        st.progress((idx + 1) / len(cats))
        st.markdown(f"## {cat['label']}")

        for q in qs:
            key = f"ans_{mode}_{q['id']}"
            current = answers.get(q["id"])
            col_q, col_i = st.columns([0.92, 0.08])
            with col_q:
                st.markdown(f"**{q['text']}**")
                st.markdown(f'<div class="muted mono" style="font-size:11px;margin-bottom:6px">{format_ref(q["ref"])}</div>', unsafe_allow_html=True)
            with col_i:
                with st.popover("i", key=f"info_{mode}_{q['id']}", width="stretch"):
                    st.markdown('<div class="kicker">WHAT THIS MEANS</div>', unsafe_allow_html=True)
                    for para in q.get("explain", "").split("\n\n"):
                        st.markdown(f'<p class="lede" style="font-size:13px">{para}</p>', unsafe_allow_html=True)
            choice = st.radio(
                label=q["id"], options=OPTIONS, index=OPTIONS.index(current) if current in OPTIONS else None,
                key=key, label_visibility="collapsed",
            )
            if choice:
                answers[q["id"]] = choice
            st.write("")

        all_answered = all(q["id"] in answers for q in qs)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Back", key="back"):
                if idx > 0:
                    st.session_state["cat_index"] -= 1
                else:
                    st.session_state["screen"] = "profile"
                st.rerun()
        with col2:
            label = "See results" if idx == len(cats) - 1 else "Next"
            if st.button(label, key="next", disabled=not all_answered, type="primary"):
                if idx < len(cats) - 1:
                    st.session_state["cat_index"] += 1
                else:
                    st.session_state["screen"] = "results"
                st.rerun()
        if not all_answered:
            st.caption("Answer every question in this section to continue.")


def render_radar(per_category, line_color, t):
    labels = [c["label"].split(" ")[0] for c in per_category]
    scores = [round(c["score"]) for c in per_category]
    lr, lg, lb = (int(line_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores + [scores[0]], theta=labels + [labels[0]], fill="toself",
        fillcolor=f"rgba({lr},{lg},{lb},0.22)", line=dict(color=line_color, width=2),
        marker=dict(color=line_color, size=6),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor=t["bg"],
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor=t["divider"]),
            angularaxis=dict(gridcolor=t["divider"], tickfont=dict(color=t["text"], size=11, family="Archivo")),
        ),
        showlegend=False, paper_bgcolor=t["bg"], plot_bgcolor=t["bg"],
        margin=dict(l=40, r=40, t=30, b=30), height=340,
        font=dict(family="Archivo"),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_results():
    mode = st.session_state["mode"]
    t = theme_tokens(st.session_state["dark"])
    per_category, overall, gaps = compute_results(mode)
    letter, hex_color, _ = grade_for(overall)
    applied_count = len(applicable_questions(mode))
    counts = status_breakdown(mode)

    col1, col2, col3 = st.columns([1, 6, 2])
    with col1:
        st.markdown(grade_chip_html(letter, hex_color), unsafe_allow_html=True)
    with col2:
        st.markdown(f"# {st.session_state['org_name'] or 'Unnamed Organization'}")
        st.markdown(
            f'<p class="lede">{ASSESSED_LABEL[mode]} · {applied_count} of 50 questions answered</p>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div style="text-align:right"><span style="font-size:34px;font-weight:800">{round(overall)}</span>'
            f'<span class="muted" style="font-size:16px">/100</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="score-track"><div class="score-fill" style="width:{overall}%"></div></div>',
        unsafe_allow_html=True,
    )

    # Results breakdown panel
    total_findings = sum(counts.values()) or 1
    bar_colors = {"Passed": GREEN, "Warning": YELLOW, "Failed": RED, "Not applicable": t["neutral_400"]}
    st.markdown(f'<div style="background:{t["surface"]}; padding:20px;">', unsafe_allow_html=True)
    st.markdown('<div class="kicker">RESULTS BREAKDOWN</div>', unsafe_allow_html=True)
    for label in ["Passed", "Warning", "Failed", "Not applicable"]:
        c = counts[label]
        width = (c / total_findings) * 100
        st.markdown(
            f'<div style="display:grid;grid-template-columns:110px 1fr 40px;align-items:center;gap:12px;margin-bottom:10px">'
            f'<div style="font-size:13px">{label}</div>'
            f'<div class="bar-track" style="height:6px"><div class="bar-fill" style="width:{width}%;background:{bar_colors[label]}"></div></div>'
            f'<div style="font-weight:800;text-align:right">{c}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<hr class="ledger-hr">', unsafe_allow_html=True)

    st.markdown("### Category breakdown")
    render_radar(per_category, hex_color, t)

    st.markdown('<hr class="ledger-hr">', unsafe_allow_html=True)

    # Per-category weighted score (kept — core to the actual scoring model)
    st.markdown("### Score by control area")
    for c in per_category:
        _, bar_color, _ = grade_for(c["score"])
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">'
            f'<span>{c["label"]} <span class="muted" style="font-size:12px">({round(c["weight"]*100)}% weight)</span></span>'
            f'<span class="mono muted">{round(c["score"])}</span></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{c["score"]}%;background:{bar_color}"></div></div>'
            f'<div style="height:14px"></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="ledger-hr">', unsafe_allow_html=True)

    # Remediation / findings — gaps only (see note to user on this adaptation)
    st.markdown("### Remediation priorities")
    if not gaps:
        st.markdown('<p class="lede">No gaps flagged — every applicable control is answered Yes. Nice work.</p>', unsafe_allow_html=True)
    else:
        icon_map = {"Critical": (ICON_X, RED), "High": (ICON_ALERT, RED), "Medium": (ICON_ALERT, YELLOW)}
        for g in gaps:
            icon_tpl, icon_color = icon_map[g["severity"]]
            tag_class = "tag-failed" if g["severity"] in ("Critical", "High") else "tag-warning"
            st.markdown(
                f'<div class="finding-row">'
                f'<div style="display:flex;gap:10px;flex:1">{icon_tpl.format(s=16, c=icon_color)}'
                f'<div><div class="muted mono" style="font-size:11px;margin-bottom:3px">{g["cat_label"]} · {format_ref(g["ref"])}</div>'
                f'<div style="font-size:14px">{g["fix"]}</div></div></div>'
                f'<span class="ftag {tag_class}">{g["severity"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.write("")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Start a new check", key="restart_bottom"):
            _reset_all()
            st.rerun()
    with col2:
        pdf_bytes = build_pdf(mode, st.session_state["org_name"], per_category, overall, gaps, letter, applied_count, counts)
        safe_name = "".join(c if c.isalnum() else "_" for c in (st.session_state["org_name"] or "compliance")).strip("_") or "compliance"
        st.download_button("Download PDF report", data=pdf_bytes,
                            file_name=f"{safe_name}_readiness_report.pdf", mime="application/pdf", type="primary")


# ---------------------------------------------------------------------------
# PDF generation (structure unchanged, recolored to match the new palette)
# ---------------------------------------------------------------------------
def wrap_text(text, font, size, max_width):
    words = text.split()
    lines, current = [], ""
    for w in words:
        trial = f"{current} {w}".strip()
        if stringWidth(trial, font, size) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def build_pdf(mode, org_name, per_category, overall, gaps, letter, applied_count, counts):
    buf = io.BytesIO()
    doc = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    margin = 48
    max_w = page_w - margin * 2
    y = [page_h - margin]

    def ensure_space(h):
        if y[0] - h < margin:
            doc.showPage()
            y[0] = page_h - margin

    doc.setFont("Helvetica-Bold", 20)
    doc.setFillColorRGB(*PDF_TEXT)
    doc.drawString(margin, y[0], "Compliance Readiness Audit")
    y[0] -= 26

    doc.setFont("Helvetica", 11)
    doc.setFillColorRGB(*PDF_MUTED)
    doc.drawString(margin, y[0], f"Organization: {org_name or 'Unnamed Organization'}")
    y[0] -= 16
    doc.drawString(margin, y[0], f"Assessed against: {ASSESSED_LABEL[mode]}")
    y[0] -= 16
    doc.drawString(margin, y[0], f"Tailored to company profile: {applied_count} of 50 questions applied")
    y[0] -= 16
    doc.drawString(margin, y[0], f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y[0] -= 30

    _, _, pdf_color = grade_for(overall)
    doc.setFillColorRGB(0.878, 0.878, 0.878)
    doc.rect(margin, y[0] - 30, 40, 40, stroke=0, fill=1)
    doc.setFont("Helvetica-Bold", 20)
    doc.setFillColorRGB(*pdf_color)
    doc.drawCentredString(margin + 20, y[0] - 18, letter)
    doc.setFont("Helvetica-Bold", 26)
    doc.setFillColorRGB(*pdf_color)
    doc.drawString(margin + 56, y[0] - 12, f"{round(overall)}/100")
    doc.setFont("Helvetica", 10.5)
    doc.setFillColorRGB(*PDF_MUTED)
    doc.drawString(margin + 56, y[0] - 28, "overall readiness score")
    y[0] -= 58

    ensure_space(80)
    doc.setFont("Helvetica-Bold", 13)
    doc.setFillColorRGB(*PDF_TEXT)
    doc.drawString(margin, y[0], "Results breakdown")
    y[0] -= 20
    total_findings = sum(counts.values()) or 1
    bucket_colors = {"Passed": PDF_GREEN, "Warning": PDF_YELLOW, "Failed": PDF_RED, "Not applicable": PDF_NEUTRAL}
    for label in ["Passed", "Warning", "Failed", "Not applicable"]:
        c = counts[label]
        ensure_space(20)
        doc.setFont("Helvetica", 10.5)
        doc.setFillColorRGB(0.16, 0.16, 0.16)
        doc.drawString(margin, y[0], label)
        doc.drawRightString(page_w - margin, y[0], str(c))
        bar_x, bar_y, bar_w, bar_h = margin + 90, y[0] - 5, max_w - 140, 6
        doc.setFillColorRGB(0.878, 0.878, 0.878)
        doc.rect(bar_x, bar_y, bar_w, bar_h, stroke=0, fill=1)
        doc.setFillColorRGB(*bucket_colors[label])
        doc.rect(bar_x, bar_y, bar_w * (c / total_findings), bar_h, stroke=0, fill=1)
        y[0] -= 20
    y[0] -= 14

    ensure_space(24)
    doc.setFont("Helvetica-Bold", 13)
    doc.setFillColorRGB(*PDF_TEXT)
    doc.drawString(margin, y[0], "Score by control area")
    y[0] -= 20

    for c in per_category:
        ensure_space(24)
        doc.setFont("Helvetica", 10.5)
        doc.setFillColorRGB(0.16, 0.16, 0.16)
        doc.drawString(margin, y[0], f"{c['label']} ({round(c['weight']*100)}%)")
        doc.drawRightString(page_w - margin, y[0], f"{round(c['score'])}")
        bar_x, bar_y, bar_w, bar_h = margin, y[0] - 9, max_w - 50, 6
        doc.setFillColorRGB(0.878, 0.878, 0.878)
        doc.rect(bar_x, bar_y, bar_w, bar_h, stroke=0, fill=1)
        _, _, fill_pdf_color = grade_for(c["score"])
        doc.setFillColorRGB(*fill_pdf_color)
        doc.rect(bar_x, bar_y, bar_w * (c["score"] / 100), bar_h, stroke=0, fill=1)
        y[0] -= 24
    y[0] -= 12

    ensure_space(24)
    doc.setFont("Helvetica-Bold", 13)
    doc.setFillColorRGB(*PDF_TEXT)
    doc.drawString(margin, y[0], "Remediation priorities")
    y[0] -= 20

    if not gaps:
        doc.setFont("Helvetica", 11)
        doc.setFillColorRGB(0.16, 0.16, 0.16)
        doc.drawString(margin, y[0], "No gaps flagged — every applicable control was answered Yes.")
        y[0] -= 16
    else:
        for g in gaps:
            ensure_space(46)
            sev_color = PDF_YELLOW if g["severity"] == "Medium" else PDF_RED
            doc.setFont("Helvetica-Bold", 10)
            doc.setFillColorRGB(*sev_color)
            doc.drawString(margin, y[0], f"[{g['severity']}]")
            doc.setFont("Helvetica", 9.5)
            doc.setFillColorRGB(*PDF_MUTED)
            doc.drawString(margin + 58, y[0], f"{g['cat_label']} · {format_ref(g['ref'])}")
            y[0] -= 15
            doc.setFont("Helvetica", 10.5)
            doc.setFillColorRGB(0.12, 0.12, 0.12)
            lines = wrap_text(g["fix"], "Helvetica", 10.5, max_w)
            ensure_space(len(lines) * 13)
            for line in lines:
                doc.drawString(margin, y[0], line)
                y[0] -= 13
            y[0] -= 10

    doc.save()
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Compliance Readiness Audit", page_icon="■", layout="wide")
    init_state()
    inject_css()
    render_nav_and_steps()

    screen = st.session_state["screen"]
    with st.container(key=f"screen_{screen}"):
        if screen == "intro":
            render_intro()
        elif screen == "profile":
            render_profile()
        elif screen == "wizard":
            render_wizard()
        else:
            render_results()


if __name__ == "__main__":
    main()
