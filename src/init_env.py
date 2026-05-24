from pathlib import Path

from src.config import PROJECT_ROOT, settings

ENV_TEMPLATE = """SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_APP_PASSWORD=your_gmail_app_password_here
SENDER_EMAIL=your_email@gmail.com
SENDER_NAME=Adrian Pliego Perez
CV_PATH=assets/Adrian_Pliego_CV.pdf
DAILY_SEND_LIMIT=10
SEND_DELAY_MIN_SECONDS=45
SEND_DELAY_MAX_SECONDS=180
DRY_RUN=true
AUTO_SEND_ENABLED=false

YOUR_LINKEDIN=https://linkedin.com/in/adrianpliegoperez
YOUR_GITHUB=https://github.com/adro0303
OPENAI_API_KEY=
HUNTER_API_KEY=
APOLLO_LEADS_PATH=data/leads/apollo-contacts-export.csv
DEFAULT_CAMPAIGN_UK=uk-graduate-outreach
DEFAULT_CAMPAIGN_SPAIN=spain-graduate-outreach
ALLOW_EMAIL_GUESSING=false
"""

FOLDERS = (
    "data/leads",
    "data/processed",
    "data/output",
    "data/db",
    "data/input",
    "assets",
)


def cmd_init_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    created_env = False
    if not env_path.exists():
        env_path.write_text(ENV_TEMPLATE, encoding="utf-8")
        created_env = True
        print(f"Created {env_path}")
    else:
        print(f".env already exists at {env_path} — not overwritten.")

    for folder in FOLDERS:
        path = PROJECT_ROOT / folder
        path.mkdir(parents=True, exist_ok=True)
        gitkeep = path / ".gitkeep"
        if folder in {"data/leads", "data/processed", "data/output", "data/db", "assets"} and not any(path.iterdir()):
            gitkeep.write_text("", encoding="utf-8")
        elif folder in {"data/leads", "data/processed", "data/output", "data/db", "assets"}:
            if not gitkeep.exists() and not any(p.name != ".gitkeep" for p in path.iterdir()):
                gitkeep.write_text("", encoding="utf-8")

    print("\nNext manual setup steps:")
    print("  1. Put CV at assets/Adrian_Pliego_CV.pdf")
    print("  2. Fill SMTP_USER in .env")
    print("  3. Fill SMTP_APP_PASSWORD in .env")
    print("  4. Fill SENDER_EMAIL in .env")
    print("  5. Keep DRY_RUN=true while testing")
    print("  6. Only set AUTO_SEND_ENABLED=true when ready for live sending")
    if created_env:
        print("\n.env created with safe placeholders. Never commit it.")
