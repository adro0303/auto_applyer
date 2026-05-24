# Auto Applyer

A **safety-first** job outreach assistant for graduate and junior technical roles. Import Apollo leads, score contacts, generate personalised email drafts, approve manually, and send only what you explicitly approve — with SQLite tracking and CV attachment support.

**This is not a spam bot.** Nothing is sent without manual approval.

---

## Features

- Apollo CSV import with email classification (usable / risky / needs email)
- Lead scoring and recruiter vs agency contact typing
- Variable-based email templates (first name, cleaned company name, no keyword dumps)
- Import batch tracking to separate real leads from test data
- Draft export to CSV for manual review (`approved=yes`)
- Dry-run send preview (read-only, no DB changes)
- Live SMTP send with daily limits, delays, and 4xx uncertain handling
- Test data cleanup command
- Optional Streamlit dashboard (read-only)
- Unit tests for SMTP status handling

---

## Safety-first workflow

1. Import leads locally — **never commit** real Apollo CSVs or contacts.
2. Generate drafts → review `data/output/outreach_drafts_*.csv`.
3. Set `approved=yes` only for rows you have read.
4. Run `approve-drafts --csv …` then `send-approved --dry-run`.
5. Live send only when `AUTO_SEND_ENABLED=true` and you confirm at the prompt.
6. If SMTP returns a temporary 4xx, status becomes `send_unknown` — check Gmail Sent before retrying; use `mark-sent --message-id N` after verification.

Keep `DRY_RUN=true` and `AUTO_SEND_ENABLED=false` until you trust the workflow.

---

## What NOT to commit

| Never commit | Why |
|--------------|-----|
| `.env` | SMTP passwords, API keys |
| `data/db/` | SQLite with real contacts and messages |
| `data/leads/` | Real Apollo exports |
| `data/output/`, `data/processed/` | Drafts and send reports |
| `assets/*.pdf` | Your CV |
| Real outreach CSVs | Personal contact data |

Use `.env.example` as a template only. All sensitive paths are in `.gitignore`.

---

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m src.cli init-env
```

Then:

1. Copy `.env.example` → `.env` and fill in **local** values.
2. Place your CV at the path set in `CV_PATH` (e.g. `assets/your_cv.pdf`).
3. Create Gmail App Password (2FA required) for `SMTP_APP_PASSWORD`.
4. Keep `AUTO_SEND_ENABLED=false` until ready.

---

## CLI usage

```bash
python -m src.cli --help

# Import (use your local Apollo file — not committed)
python -m src.cli import-apollo --file data/leads/your_export.csv --country uk

# Generate drafts from a specific import
python -m src.cli generate-drafts --country uk --source apollo \
  --source-file data/leads/your_export.csv --min-score 50 --no-enrich

# Approve and send
python -m src.cli approve-drafts --csv data/output/outreach_drafts_uk.csv
python -m src.cli send-approved --country uk --dry-run
python -m src.cli send-approved --country uk --live   # only when ready

# After verifying delivery in Gmail Sent (4xx uncertain)
python -m src.cli mark-sent --message-id 123

# Remove test/example data from DB
python -m src.cli cleanup-test-data --dry-run
```

### Test with anonymised sample

```bash
mkdir -p data/leads
copy examples\example_apollo_export.csv data\leads\example_apollo_export.csv
python -m src.cli import-apollo --file data/leads/example_apollo_export.csv --country uk
```

---

## Streamlit dashboard (optional)

Read-only view of contacts and messages:

```bash
streamlit run dashboard/app.py
```

---

## Project layout

```
auto_applyer/
├── src/              # CLI, import, scoring, email generation, sending
├── tests/            # Unit tests
├── templates/        # Legacy Jinja templates
├── dashboard/        # Streamlit app
├── examples/         # Anonymised sample Apollo CSV (safe to commit)
├── prompts/          # Cursor / agent prompts
├── data/             # Local only (gitignored): db, leads, output, processed
└── assets/           # Local CV (gitignored); .gitkeep tracks folder
```

---

## License

Private / personal tooling. Use responsibly and comply with email and data protection laws.
