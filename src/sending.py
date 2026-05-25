import random
import smtplib
import time
import os
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

from src.config import PROJECT_ROOT, settings
from src.db.repository import Repository
from src.smtp_errors import UNCERTAIN_CONSOLE_MESSAGE, classify_smtp_exception
from src.validate_contacts import is_valid_email


class SendSafetyError(Exception):
    pass


# Only these message statuses are eligible for live send-approved.
SENDABLE_MESSAGE_STATUS = "approved"

NON_SENDABLE_MESSAGE_STATUSES = frozenset(
    {
        "sent",
        "failed",
        "send_unknown",
        "archived_superseded",
        "sent_dry_run",
        "archived_test_data",
    }
)


def _smtp_configured() -> bool:
    return bool(settings.smtp_user and settings.smtp_app_password and settings.sender_email)


def _auto_send_enabled_runtime() -> bool:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    raw = os.getenv("AUTO_SEND_ENABLED", "false")
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def check_send_allowed(repo: Repository, count: int = 1) -> None:
    if not _auto_send_enabled_runtime():
        raise SendSafetyError(
            "AUTO_SEND_ENABLED is false. Set AUTO_SEND_ENABLED=true in .env only after manual review."
        )
    if not _smtp_configured():
        raise SendSafetyError(
            "SMTP credentials missing. Set SMTP_USER, SMTP_APP_PASSWORD, and SENDER_EMAIL in .env."
        )
    sent_today = repo.count_sent_today()
    if sent_today + count > settings.daily_send_limit:
        raise SendSafetyError(
            f"Daily limit exceeded ({settings.daily_send_limit}). Sent today: {sent_today}."
        )


def check_cv_attachment() -> dict:
    cv_path: Path = settings.cv_file
    if not cv_path.exists():
        return {
            "status": "missing",
            "path": str(cv_path),
            "would_attach": False,
            "message": "CV missing",
        }
    size = cv_path.stat().st_size
    if size > settings.max_attachment_bytes:
        return {
            "status": "too_large",
            "path": str(cv_path),
            "size_bytes": size,
            "would_attach": False,
            "message": f"CV too large ({size} bytes > {settings.max_attachment_bytes})",
        }
    return {
        "status": "found",
        "path": str(cv_path),
        "size_bytes": size,
        "would_attach": True,
        "message": "CV found",
    }


def build_email_message(to: str, subject: str, body: str, attach_cv: bool = True) -> tuple[EmailMessage, dict]:
    msg = EmailMessage()
    msg["From"] = f"{settings.sender_name} <{settings.sender_email}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    cv_info = check_cv_attachment()
    if attach_cv and cv_info["would_attach"]:
        cv_path = Path(cv_info["path"])
        msg.add_attachment(
            cv_path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=cv_path.name,
        )
    return msg, cv_info


def send_email_live(to: str, subject: str, body: str, attach_cv: bool = True) -> dict:
    if not is_valid_email(to):
        return {"status": "skipped", "reason": "invalid_email", "to": to}

    msg, cv_info = build_email_message(to, subject, body, attach_cv=attach_cv)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_app_password)
        server.send_message(msg)

    return {
        "status": "sent",
        "to": to,
        "subject": subject,
        "cv_attachment": cv_info["status"],
        "cv_message": cv_info["message"],
    }


def preview_email(to: str, subject: str, body: str, attach_cv: bool = True) -> dict:
    cv_info = check_cv_attachment()
    return {
        "status": "dry_run",
        "to": to,
        "subject": subject,
        "preview": body[:200],
        "cv_attachment": cv_info["status"],
        "cv_message": cv_info["message"],
        "would_attach_cv": cv_info["would_attach"],
    }


def process_approved_batch(
    messages: list[dict],
    *,
    dry_run: bool = True,
    repo: Repository | None = None,
) -> list[dict]:
    """Process approved messages. Dry-run is read-only (no DB updates)."""
    repo = repo or Repository()
    results: list[dict] = []
    seen_emails: set[str] = set()
    uncertain_warnings_printed = 0

    if not dry_run:
        check_send_allowed(repo, count=min(len(messages), settings.daily_send_limit))

    sent_today = repo.count_sent_today()
    sent_this_run = 0

    for msg in messages:
        message_id = msg["message_id"]
        email = str(msg["email"]).strip().lower()
        status = msg.get("status")
        row_result = {
            "message_id": message_id,
            "email": email,
            "subject": msg.get("subject", ""),
            "company": msg.get("company_name", ""),
            "mode": "dry_run" if dry_run else "live",
            "manual_check_required": False,
        }

        if status != SENDABLE_MESSAGE_STATUS or status in NON_SENDABLE_MESSAGE_STATUSES:
            row_result.update({"result": "skipped", "reason": f"status_{status or 'unknown'}"})
            results.append(row_result)
            continue

        if not is_valid_email(email):
            row_result.update({"result": "skipped", "reason": "invalid_email"})
            if not dry_run:
                repo.mark_message_failed(message_id, "invalid_email")
            results.append(row_result)
            continue

        if email in seen_emails:
            row_result.update({"result": "skipped", "reason": "duplicate_in_batch"})
            results.append(row_result)
            continue

        if not dry_run and sent_today + sent_this_run >= settings.daily_send_limit:
            row_result.update({"result": "skipped", "reason": "daily_limit_reached"})
            results.append(row_result)
            continue

        seen_emails.add(email)

        if dry_run:
            preview = preview_email(email, msg["subject"], msg["body"])
            row_result.update(
                {
                    "result": "dry_run",
                    "cv_attachment": preview["cv_attachment"],
                    "cv_message": preview["cv_message"],
                    "would_attach_cv": preview["would_attach_cv"],
                    "preview": preview["preview"],
                }
            )
            results.append(row_result)
            continue

        try:
            send_result = send_email_live(email, msg["subject"], msg["body"])
            repo.mark_message_sent(message_id)
            repo.update_contact_status(email, "sent")
            contact_id = msg.get("contact_id")
            if contact_id:
                repo.insert_interaction(contact_id, "sent", message_id, "send-approved live")
            row_result.update(send_result)
            row_result["result"] = "sent"
            sent_this_run += 1
        except Exception as exc:
            error_str = str(exc)
            classification = classify_smtp_exception(exc)
            if classification["kind"] == "uncertain":
                repo.mark_message_send_unknown(message_id, error_str)
                row_result.update(
                    {
                        "result": "uncertain",
                        "error": error_str,
                        "error_message": error_str,
                        "smtp_code": classification.get("smtp_code"),
                        "manual_check_required": True,
                    }
                )
                if uncertain_warnings_printed == 0:
                    print(UNCERTAIN_CONSOLE_MESSAGE)
                    uncertain_warnings_printed += 1
            else:
                repo.mark_message_failed(message_id, error_str)
                row_result.update(
                    {
                        "result": "failed",
                        "error": error_str,
                        "error_message": error_str,
                        "smtp_code": classification.get("smtp_code"),
                        "manual_check_required": False,
                    }
                )

        results.append(row_result)

        if sent_this_run > 0 and sent_this_run < settings.daily_send_limit:
            delay = random.randint(settings.send_delay_min_seconds, settings.send_delay_max_seconds)
            time.sleep(delay)

    return results
