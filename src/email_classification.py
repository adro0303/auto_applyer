import re

from email_validator import EmailNotValidError, validate_email

NEEDS_EMAIL_STATUSES = {
    "unavailable",
    "locked",
    "not found",
    "not_found",
    "invalid",
    "bounced",
    "no email",
    "no_email",
}

RISKY_ONLY_STATUSES = {
    "unverified",
    "guessed",
    "unknown",
    "risky",
}


def is_valid_email(email: str | None) -> bool:
    if not email or not isinstance(email, str) or not email.strip():
        return False
    try:
        validate_email(email.strip(), check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def _norm(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return re.sub(r"\s+", " ", text.lower())


def _is_catch_all(catch_all_status: str | None) -> bool:
    return _norm(catch_all_status) in {"catch-all", "catch all", "accept_all", "accept-all"}


def classify_email_usability(
    email: str | None,
    email_status: str | None,
    catch_all_status: str | None = None,
) -> tuple[str, str, list[str]]:
    """
    Returns (usable | needs_email | risky, reason, notes).
    """
    email = (email or "").strip().lower()
    status = _norm(email_status)
    notes: list[str] = []

    if not email or email == "nan":
        return "needs_email", "missing_email", notes

    if status in NEEDS_EMAIL_STATUSES:
        return "needs_email", f"email_status:{status}", notes

    if not is_valid_email(email):
        return "needs_email", "invalid_format", notes

    if status == "verified" or status == "valid":
        if _is_catch_all(catch_all_status):
            notes.append("verified email, catch-all domain")
        else:
            notes.append("verified email, catch-all unknown")
        return "usable", "verified", notes

    if status in RISKY_ONLY_STATUSES or _is_catch_all(catch_all_status):
        return "risky", f"email_status:{status or 'catch-all'}", notes

    if not status:
        if _is_catch_all(catch_all_status):
            return "risky", "catch-all_no_verified_status", notes
        return "usable", "valid_format_no_status", notes

    return "risky", f"email_status:{status}", notes


def classify_email_status(
    email: str | None,
    email_status: str | None,
    catch_all_status: str | None = None,
) -> str:
    return classify_email_usability(email, email_status, catch_all_status)[0]
