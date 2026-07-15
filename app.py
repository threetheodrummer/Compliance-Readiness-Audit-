"""
Compliance Readiness Audit — Streamlit edition
A self-assessment tool covering GDPR, DPDP Act 2023, and NIS2, with independent
50-question banks per mode plus a combined view. Generates a downloadable PDF report.
"""

import json
import io
import textwrap
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

# ---------------------------------------------------------------------------
# Data loading
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
    "GDPR": "EU GDPR only",
    "DPDP": "DPDP Act, 2023 only",
    "NIS2": "NIS2 Directive only",
    "BOTH": "GDPR & DPDP (both)",
    "ALL": "All three, together",
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

OPTIONS = ["Yes", "Partial", "No", "N/A"]
OPTION_VAL = {"Yes": 1.0, "Partial": 0.5, "No": 0.0, "N/A": None}
OPTION_HEX = {"Yes": "#5E9C76", "Partial": "#D9A441", "No": "#C1524A", "N/A": "#8B93B8"}

INK = "#10162B"
INK_PANEL = "#1A2142"
INK_LINE = "#2E3760"
TEXT_COLOR = "#EDEBE3"
MUTED = "#8B93B8"
BRASS = "#C9A05B"
RISK = "#C1524A"
CAUTION = "#D9A441"
SAFE = "#5E9C76"

PDF_INK = (20 / 255, 26 / 255, 50 / 255)
PDF_MUTED = (90 / 255, 90 / 255, 90 / 255)
PDF_BRASS = (138 / 255, 111 / 255, 62 / 255)
PDF_RISK = (169 / 255, 50 / 255, 38 / 255)
PDF_CAUTION = (184 / 255, 134 / 255, 11 / 255)
PDF_SAFE = (63 / 255, 122 / 255, 83 / 255)


def hex_to_unit_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def grade_for(score: float):
    if score >= 90:
        return "A", SAFE, PDF_SAFE
    if score >= 80:
        return "B", SAFE, PDF_SAFE
    if score >= 70:
        return "C", CAUTION, PDF_CAUTION
    if score >= 60:
        return "D", RISK, PDF_RISK
    return "F", RISK, PDF_RISK


def format_ref(ref) -> str:
    if isinstance(ref, str):
        return ref
    return f"DPDP {ref.get('DPDP', '—')} · GDPR {ref.get('GDPR', '—')}"


def get_categories(mode):
    return DATA[BANKS[mode][0]]


def get_questions(mode):
    return DATA[BANKS[mode][1]]


def questions_by_category(mode):
    cats = get_categories(mode)
    qs = get_questions(mode)
    return {c["id"]: [q for q in qs if q["cat"] == c["id"]] for c in cats}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "screen": "intro",
        "mode": "BOTH",
        "org_name": "",
        "answers": {},   # {mode: {qid: option_str}}
        "cat_index": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_answers():
    return st.session_state["answers"].setdefault(st.session_state["mode"], {})


def compute_results(mode):
    cats = get_categories(mode)
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
    for q in get_questions(mode):
        ans = answers.get(q["id"])
        if ans in ("No", "Partial"):
            cat = next(c for c in cats if c["id"] == q["cat"])
            severity = ("Critical" if cat["weight"] >= 0.2 else "High") if ans == "No" else "Medium"
            gaps.append({**q, "severity": severity, "cat_label": cat["label"]})
    sev_order = {"Critical": 0, "High": 1, "Medium": 2}
    gaps.sort(key=lambda g: sev_order[g["severity"]])

    return per_category, overall, gaps


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,500;0,600;1,500&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    .stApp {{ background-color: {INK}; color: {TEXT_COLOR}; font-family: 'Inter', sans-serif; }}
    h1, h2, h3 {{ font-family: 'Lora', serif !important; color: {TEXT_COLOR} !important; }}
    p, li, label, span {{ font-family: 'Inter', sans-serif; }}
    .eyebrow {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 0.14em;
                color: {BRASS}; margin-bottom: 6px; }}
    .lede {{ color: {MUTED}; font-size: 15px; line-height: 1.6; }}
    .mono {{ font-family: 'IBM Plex Mono', monospace; }}

    div.stButton > button {{
        background-color: {BRASS}; color: #1A1206; border: none; border-radius: 6px;
        font-weight: 600; padding: 0.5rem 1.2rem;
    }}
    div.stButton > button:hover {{ background-color: #dcb56f; color: #1A1206; }}
    .secondary button {{ background-color: transparent !important; color: {TEXT_COLOR} !important;
                          border: 1px solid {INK_LINE} !important; }}

    div[data-baseweb="radio"] {{ background-color: {INK_PANEL}; border: 1px solid {INK_LINE};
                                  border-radius: 8px; padding: 14px 18px; margin-bottom: 10px; }}
    .q-ref {{ font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: {MUTED};
              margin-top: -8px; margin-bottom: 8px; }}

    .gap-card {{ display: flex; gap: 14px; background: {INK_PANEL}; border: 1px solid {INK_LINE};
                 border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; align-items: flex-start; }}
    .sev-tag {{ font-family: 'IBM Plex Mono', monospace; font-size: 10px; border: 1px solid;
                border-radius: 4px; padding: 3px 8px; white-space: nowrap; }}
    .bar-track {{ height: 8px; background: {INK_LINE}; border-radius: 4px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 4px; }}
    </style>
    """, unsafe_allow_html=True)


def seal_svg(letter, size, color):
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="46" fill="none" stroke="{color}" stroke-width="2" />
        <circle cx="50" cy="50" r="38" fill="none" stroke="{color}" stroke-width="1" stroke-dasharray="2 3" />
        <text x="50" y="52" text-anchor="middle" dominant-baseline="central" fill="{color}"
              font-family="Lora, serif" font-size="{size * 0.36}" font-weight="600">{letter}</text>
    </svg>"""


# ---------------------------------------------------------------------------
# Screens
# ---------------------------------------------------------------------------
def render_intro():
    st.markdown(f'<div style="text-align:center">{seal_svg("§", 64, BRASS)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow" style="text-align:center">PRIVACY, SECURITY & COMPLIANCE</div>', unsafe_allow_html=True)
    st.markdown('<h1 style="text-align:center">Compliance Readiness Audit</h1>', unsafe_allow_html=True)

    q_count = len(get_questions(st.session_state["mode"]))
    c_count = len(get_categories(st.session_state["mode"]))
    st.markdown(
        f'<p class="lede" style="text-align:center">A {q_count}-question self-assessment across '
        f'{c_count} control areas, currently set to review {FRAMEWORK_TEXT[st.session_state["mode"]]}. '
        f'Answer honestly — the report only helps if it\'s accurate.</p>',
        unsafe_allow_html=True,
    )

    st.session_state["org_name"] = st.text_input(
        "Organization name", value=st.session_state["org_name"], placeholder="e.g. Hamza Hitech Pvt Ltd"
    )

    st.markdown("**Assess against** (each option is its own dedicated 50-question set)")
    cols = st.columns(5)
    for col, key in zip(cols, ["GDPR", "DPDP", "NIS2", "BOTH", "ALL"]):
        with col:
            if st.button(MODE_LABELS[key], key=f"mode_{key}",
                         type="primary" if st.session_state["mode"] == key else "secondary"):
                st.session_state["mode"] = key
                st.rerun()

    st.write("")
    if st.button("Begin assessment →", key="begin"):
        st.session_state["screen"] = "wizard"
        st.session_state["cat_index"] = 0
        st.session_state["answers"][st.session_state["mode"]] = {}
        st.rerun()


def render_wizard():
    mode = st.session_state["mode"]
    cats = get_categories(mode)
    by_cat = questions_by_category(mode)
    idx = st.session_state["cat_index"]
    cat = cats[idx]
    qs = by_cat[cat["id"]]
    answers = get_answers()

    st.progress((idx + 1) / len(cats))
    st.markdown(f'<div class="eyebrow">SECTION {idx + 1} OF {len(cats)}</div>', unsafe_allow_html=True)
    st.markdown(f"## {cat['label']}")

    for q in qs:
        key = f"ans_{mode}_{q['id']}"
        current = answers.get(q["id"])
        st.markdown(f"**{q['text']}**")
        st.markdown(f'<div class="q-ref">{format_ref(q["ref"])}</div>', unsafe_allow_html=True)
        choice = st.radio(
            label=q["id"], options=OPTIONS, index=OPTIONS.index(current) if current in OPTIONS else None,
            horizontal=True, key=key, label_visibility="collapsed",
        )
        if choice:
            answers[q["id"]] = choice

    all_answered = all(q["id"] in answers for q in qs)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back", key="back"):
            if idx > 0:
                st.session_state["cat_index"] -= 1
            else:
                st.session_state["screen"] = "intro"
            st.rerun()
    with col2:
        label = "See report →" if idx == len(cats) - 1 else "Next section →"
        if st.button(label, key="next", disabled=not all_answered):
            if idx < len(cats) - 1:
                st.session_state["cat_index"] += 1
            else:
                st.session_state["screen"] = "results"
            st.rerun()
    if not all_answered:
        st.caption("Answer every question in this section to continue.")


def render_radar(per_category):
    labels = [c["label"].split(" ")[0] for c in per_category]
    scores = [round(c["score"]) for c in per_category]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores + [scores[0]], theta=labels + [labels[0]], fill="toself",
        fillcolor="rgba(201,160,91,0.28)", line=dict(color=BRASS, width=2),
        marker=dict(color=BRASS, size=6),
    ))
    fig.update_layout(
        polar=dict(
            bgcolor=INK,
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, gridcolor=INK_LINE),
            angularaxis=dict(gridcolor=INK_LINE, tickfont=dict(color=MUTED, size=11, family="Inter")),
        ),
        showlegend=False, paper_bgcolor=INK, plot_bgcolor=INK,
        margin=dict(l=40, r=40, t=30, b=30), height=340,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render_results():
    mode = st.session_state["mode"]
    per_category, overall, gaps = compute_results(mode)
    letter, hex_color, _ = grade_for(overall)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="eyebrow">ASSESSMENT REPORT</div>', unsafe_allow_html=True)
        st.markdown(f"# {st.session_state['org_name'] or 'Unnamed Organization'}")
        st.markdown(f'<p class="lede">Assessed against {ASSESSED_LABEL[mode]}</p>', unsafe_allow_html=True)
    with col2:
        st.markdown(seal_svg(letter, 100, hex_color), unsafe_allow_html=True)

    st.markdown(
        f'<span class="mono" style="font-size:44px;color:{hex_color}">{round(overall)}</span>'
        f'<span style="color:{MUTED};font-size:14px"> / 100 overall readiness</span>',
        unsafe_allow_html=True,
    )
    st.write("")
    render_radar(per_category)

    st.write("")
    for c in per_category:
        bar_color = grade_for(c["score"])[1]
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">'
            f'<span>{c["label"]} <span style="color:{MUTED};font-size:12px">'
            f'({round(c["weight"]*100)}% weight)</span></span>'
            f'<span class="mono" style="color:{MUTED}">{round(c["score"])}</span></div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{c["score"]}%;'
            f'background:{bar_color}"></div></div><div style="height:12px"></div>',
            unsafe_allow_html=True,
        )

    st.markdown("## Remediation priorities")
    if not gaps:
        st.markdown('<p class="lede">No gaps flagged — every applicable control is answered Yes. Nice work.</p>',
                    unsafe_allow_html=True)
    else:
        for g in gaps:
            sev_hex = CAUTION if g["severity"] == "Medium" else RISK
            st.markdown(
                f'<div class="gap-card"><div class="sev-tag" style="color:{sev_hex};border-color:{sev_hex}">'
                f'{g["severity"]}</div><div><p class="q-ref" style="margin:0 0 4px 0">'
                f'{g["cat_label"]} · {format_ref(g["ref"])}</p>'
                f'<p style="margin:0">{g["fix"]}</p></div></div>',
                unsafe_allow_html=True,
            )

    st.write("")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("↺ New assessment"):
            st.session_state["screen"] = "intro"
            st.session_state["answers"][mode] = {}
            st.session_state["cat_index"] = 0
            st.rerun()
    with col2:
        pdf_bytes = build_pdf(mode, st.session_state["org_name"], per_category, overall, gaps, letter)
        safe_name = "".join(c if c.isalnum() else "_" for c in (st.session_state["org_name"] or "compliance")).strip("_") or "compliance"
        st.download_button("Download PDF report ↓", data=pdf_bytes,
                            file_name=f"{safe_name}_readiness_report.pdf", mime="application/pdf")


# ---------------------------------------------------------------------------
# PDF generation
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


def build_pdf(mode, org_name, per_category, overall, gaps, letter):
    buf = io.BytesIO()
    doc = canvas.Canvas(buf, pagesize=A4)
    page_w, page_h = A4
    margin = 48
    max_w = page_w - margin * 2
    y = [page_h - margin]  # mutable to allow updates inside nested funcs

    def ensure_space(h):
        if y[0] - h < margin:
            doc.showPage()
            y[0] = page_h - margin

    doc.setFont("Helvetica-Bold", 20)
    doc.setFillColorRGB(*PDF_INK)
    doc.drawString(margin, y[0], "Compliance Readiness Audit")
    y[0] -= 26

    doc.setFont("Helvetica", 11)
    doc.setFillColorRGB(*PDF_MUTED)
    doc.drawString(margin, y[0], f"Organization: {org_name or 'Unnamed Organization'}")
    y[0] -= 16
    doc.drawString(margin, y[0], f"Assessed against: {ASSESSED_LABEL[mode]}")
    y[0] -= 16
    import datetime
    doc.drawString(margin, y[0], f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y[0] -= 30

    # Grade seal + overall score
    _, _, pdf_color = grade_for(overall)
    doc.setStrokeColorRGB(*PDF_BRASS)
    doc.setLineWidth(1.5)
    doc.circle(margin + 24, y[0] - 8, 22, stroke=1, fill=0)
    doc.setFont("Helvetica-Bold", 20)
    doc.setFillColorRGB(*PDF_BRASS)
    doc.drawCentredString(margin + 24, y[0] - 14, letter)
    doc.setFont("Helvetica-Bold", 26)
    doc.setFillColorRGB(*pdf_color)
    doc.drawString(margin + 66, y[0] - 12, f"{round(overall)}/100")
    doc.setFont("Helvetica", 10.5)
    doc.setFillColorRGB(*PDF_MUTED)
    doc.drawString(margin + 66, y[0] - 28, "overall readiness score")
    y[0] -= 58

    ensure_space(24)
    doc.setFont("Helvetica-Bold", 13)
    doc.setFillColorRGB(*PDF_INK)
    doc.drawString(margin, y[0], "Score by control area")
    y[0] -= 20

    for c in per_category:
        ensure_space(24)
        doc.setFont("Helvetica", 10.5)
        doc.setFillColorRGB(0.16, 0.16, 0.16)
        doc.drawString(margin, y[0], f"{c['label']} ({round(c['weight']*100)}%)")
        doc.drawRightString(page_w - margin, y[0], f"{round(c['score'])}")
        bar_x, bar_y, bar_w, bar_h = margin, y[0] - 9, max_w - 50, 6
        doc.setFillColorRGB(228 / 255, 225 / 255, 216 / 255)
        doc.rect(bar_x, bar_y, bar_w, bar_h, stroke=0, fill=1)
        _, _, fill_pdf_color = grade_for(c["score"])
        doc.setFillColorRGB(*fill_pdf_color)
        doc.rect(bar_x, bar_y, bar_w * (c["score"] / 100), bar_h, stroke=0, fill=1)
        y[0] -= 24
    y[0] -= 12

    ensure_space(24)
    doc.setFont("Helvetica-Bold", 13)
    doc.setFillColorRGB(*PDF_INK)
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
            sev_color = PDF_CAUTION if g["severity"] == "Medium" else PDF_RISK
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
    st.set_page_config(page_title="Compliance Readiness Audit", page_icon="§", layout="centered")
    inject_css()
    init_state()

    if st.session_state["screen"] == "intro":
        render_intro()
    elif st.session_state["screen"] == "wizard":
        render_wizard()
    else:
        render_results()


if __name__ == "__main__":
    main()
