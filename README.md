# Auto Applyer

🌍 Language: English | [Español](README.es.md)

## Overview

Auto Applyer is a local Python tool for safe job outreach automation. It helps import leads, generate email drafts, review and approve drafts manually, run dry-run checks, send approved emails through SMTP, view reports, and manage safety controls through both CLI and a local Streamlit dashboard.

Designed for careful, human-reviewed, low-volume outreach for junior/graduate roles — not spam.

## How to use

### Recommended option: visual dashboard

The easiest way to use the tool is through the local dashboard:

```bash
run_app.bat
```

or:

```bash
python -m streamlit run src/ui_app.py
```

From the dashboard you can:

1. Review configuration and safety status.
2. Generate drafts from your Apollo CSV.
3. Review generated emails.
4. Approve only the drafts you want to send.
5. Run a dry-run before sending.
6. Enable or disable live sending from settings.
7. Send approved emails with manual confirmation.
8. Review delivery reports.

Live sending is protected: it requires `AUTO_SEND_ENABLED=true` and typing `SEND LIVE`.

### Recommended workflow

1. Place the Apollo CSV in `data/leads/`.
2. Generate drafts from dashboard or CLI.
3. Review emails manually.
4. Approve only high-quality contacts.
5. Run dry-run.
6. If everything looks correct, enable live sending.
7. Send in small batches.
8. Disable live sending again after finishing.

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

Main variables:

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

The dashboard runs locally and lets you manage the full workflow without typing commands constantly.

## Desktop shortcut with custom icon

If you want to launch the app from desktop with a custom icon:

1. Right-click `run_app.bat`.
2. Select **Create shortcut**.
3. Move the shortcut to your desktop.
4. Right-click the shortcut and open **Properties**.
5. Click **Change Icon**.
6. Choose the `.ico` file located in the project root.
7. Save changes.

Important: the `.bat` file itself cannot hold a custom icon directly; the icon is applied to the shortcut.

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
- Always run dry-run before live sending

## Disclaimer

This project is intended for personal, careful, manually reviewed job outreach. Do not use it for spam, abusive scraping, or unsolicited bulk sending.
