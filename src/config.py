import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def resolve_path(relative_or_absolute: str | Path) -> Path:
    path = Path(relative_or_absolute)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


@dataclass
class Settings:
    sender_name: str = os.getenv("SENDER_NAME") or os.getenv("YOUR_NAME", "Adrian Pliego Perez")
    sender_email: str = os.getenv("SENDER_EMAIL") or os.getenv("YOUR_EMAIL", "")
    linkedin: str = os.getenv("YOUR_LINKEDIN", "https://linkedin.com/in/adrianpliegoperez")
    github: str = os.getenv("YOUR_GITHUB", "https://github.com/adro0303")

    cv_path: str = os.getenv("CV_PATH", "assets/Adrian_Pliego_CV.pdf")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    hunter_api_key: str = os.getenv("HUNTER_API_KEY", "")
    apollo_api_key: str = os.getenv("APOLLO_API_KEY", "")

    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_app_password: str = os.getenv("SMTP_APP_PASSWORD") or os.getenv("SMTP_PASSWORD", "")

    daily_send_limit: int = int(os.getenv("DAILY_SEND_LIMIT", "10"))
    send_delay_min_seconds: int = int(os.getenv("SEND_DELAY_MIN_SECONDS", "45"))
    send_delay_max_seconds: int = int(os.getenv("SEND_DELAY_MAX_SECONDS", "180"))
    dry_run: bool = _bool("DRY_RUN", True)
    auto_send_enabled: bool = _bool("AUTO_SEND_ENABLED", False)
    allow_email_guessing: bool = _bool("ALLOW_EMAIL_GUESSING", False)

    default_campaign_uk: str = os.getenv("DEFAULT_CAMPAIGN_UK", "uk-graduate-outreach")
    default_campaign_spain: str = os.getenv("DEFAULT_CAMPAIGN_SPAIN", "spain-graduate-outreach")
    apollo_leads_path: str = os.getenv("APOLLO_LEADS_PATH", "data/leads/apollo-contacts-export.csv")

    max_attachment_bytes: int = 5 * 1024 * 1024

    @property
    def cv_file(self) -> Path:
        return resolve_path(self.cv_path)

    @property
    def db_path(self) -> Path:
        return resolve_path("data/db/outreach.sqlite")

    @property
    def data_output_dir(self) -> Path:
        return resolve_path("data/output")

    @property
    def data_processed_dir(self) -> Path:
        return resolve_path("data/processed")

    @property
    def data_input_dir(self) -> Path:
        return resolve_path("data/input")

    @property
    def templates_dir(self) -> Path:
        return resolve_path("templates")

    def path(self, relative: str | Path) -> Path:
        return resolve_path(relative)


settings = Settings()
