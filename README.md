# Compliance Readiness Audit (Python / Streamlit)

A self-assessment tool covering GDPR, India's DPDP Act 2023, and the EU NIS2 Directive,
with five independent 50-question modes. Generates a downloadable PDF report based on
live answers.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens the app in your browser at http://localhost:8501

## Files

- `app.py` — the full application (UI, scoring engine, radar chart, PDF generation)
- `data.json` — all 5 question banks (GDPR, DPDP, NIS2, GDPR+DPDP, All three), 50 questions each
- `requirements.txt` — Python dependencies

## Modes

| Mode | Questions | Categories |
|---|---|---|
| EU GDPR only | 50 | 7 |
| DPDP Act, 2023 only | 50 | 7 |
| NIS2 Directive only | 50 | 5 |
| GDPR & DPDP (both) | 50 | 9 |
| All three, together | 50 | 6 |
