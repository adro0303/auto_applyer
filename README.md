# Auto Applyer

🌍 Language: English | [Español](README.es.md)

## Overview

Auto Applyer is a local Python tool for safe job outreach automation. It helps import leads, generate email drafts, review and approve drafts manually, run dry-run checks, send approved emails through SMTP, view reports, and manage safety controls through both CLI and a local Streamlit dashboard.

Designed for careful, human-reviewed, low-volume outreach for junior/graduate roles — not spam.

## Features

- Apollo CSV import
- Lead cleaning, scoring, and contact type detection
- Template-based email generation
- Manual approval workflow before any send
- SMTP sending with Gmail App Password
- Dry-run and live-send reports
- Uncertain SMTP status handling + `mark-sent` helper
- Local Streamlit dashboard with English/Spanish UI

## Safety-first workflow

1. Import leads locally.
2. Generate drafts and review them manually.
3. Approve only reviewed drafts.
4. Run dry-run before any live send.
5. Enable live sending only when ready (`AUTO_SEND_ENABLED=true`).
6. In Streamlit, live sending still requires typing `SEND LIVE`.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.cli init-env
```

Copy `.env.example` to `.env` and fill local values only.

## Environment variables

Use `.env.example` placeholders. Important variables:

- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_APP_PASSWORD`
- Sender: `SENDER_EMAIL`, `SENDER_NAME`
- CV: `CV_PATH`
- Safety: `DRY_RUN`, `AUTO_SEND_ENABLED`
- Limits: `DAILY_SEND_LIMIT`, `SEND_DELAY_MIN_SECONDS`, `SEND_DELAY_MAX_SECONDS`
- Optional APIs: `OPENAI_API_KEY`, `HUNTER_API_KEY`

Never commit `.env`, credentials, API keys, real contacts, CV files, reports, or local databases.

## CLI usage

```bash
python -m src.cli generate-drafts --country uk --source apollo --source-file data/leads/apollo-contacts-export.csv --min-score 50 --no-enrich --force

python -m src.cli approve-drafts --csv data/output/outreach_drafts_uk.csv

python -m src.cli send-approved --country uk --dry-run --limit 5

python -m src.cli send-approved --country uk --live --limit 1

python -m src.cli mark-sent --message-id 151
```

## Visual dashboard / Streamlit UI

```bash
python -m streamlit run src/ui_app.py
```

or

```bash
run_app.bat
```

The dashboard is local-first, includes safety controls, and requires both `AUTO_SEND_ENABLED=true` and `SEND LIVE` for live send.

## Project structure

```text
auto_applyer/
├── src/
├── tests/
├── prompts/
├── examples/
├── data/        # local-only (gitignored)
├── assets/      # local CV files (gitignored)
├── README.md
└── README.es.md
```

## Security notes

- Do not commit `.env` or `.env.backup`
- Do not commit SQLite files, real CSVs, reports, or CVs
- Do not expose SMTP credentials or API keys
- Keep sending volume low and reviewed by a human

## Disclaimer

This project is intended for careful, ethical job-search outreach. You are responsible for legal compliance, consent, and platform/email policy adherence.
