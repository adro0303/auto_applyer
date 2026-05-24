import re

import pandas as pd
import requests
from email_validator import EmailNotValidError, validate_email

from src.config import settings

GENERIC_EMAIL_PATTERNS = (
    r"^(info|hello|contact|support|careers|jobs|hr|recruitment|talent)@",
)


def is_valid_email(email: str) -> bool:
    if not isinstance(email, str) or not email.strip():
        return False
    try:
        validate_email(email.strip(), check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def looks_guessed_personal(email: str, name: str) -> bool:
    """Heuristic: first.last@domain patterns without verified source."""
    if settings.allow_email_guessing:
        return False
    local = email.split("@")[0].lower()
    parts = [p for p in re.split(r"\s+", name.lower()) if p]
    if len(parts) < 2:
        return False
    guessed = f"{parts[0]}.{parts[-1]}"
    guessed2 = f"{parts[0][0]}{parts[-1]}"
    return local in {guessed, guessed2, f"{parts[0]}{parts[-1]}"}


def is_generic_email(email: str) -> bool:
    return any(re.match(p, email.lower()) for p in GENERIC_EMAIL_PATTERNS)


def verify_with_hunter(email: str) -> dict:
    if not settings.hunter_api_key:
        return {"verified": None, "score": None, "status": "skipped_no_key"}

    try:
        resp = requests.get(
            "https://api.hunter.io/v2/email-verifier",
            params={"email": email, "api_key": settings.hunter_api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        status = data.get("status", "")
        score = data.get("score")
        verified = status in {"valid", "accept_all"} and (score or 0) >= 50
        return {"verified": verified, "score": score, "status": status}
    except Exception as exc:
        return {"verified": None, "score": None, "status": f"error:{exc}"}


def validate_contact_row(contact: dict, use_hunter: bool = True) -> dict:
    email = str(contact.get("email", "")).strip().lower()
    valid_format = is_valid_email(email)
    generic = is_generic_email(email)
    guessed = looks_guessed_personal(email, str(contact.get("name", "")))

    hunter_score = None
    email_verified = int(contact.get("email_verified") or 0)

    if use_hunter and settings.hunter_api_key and valid_format:
        result = verify_with_hunter(email)
        if result["verified"] is not None:
            email_verified = 1 if result["verified"] else 0
        if result["score"] is not None:
            hunter_score = result["score"]

    reject_guessed = guessed and contact.get("source") not in {"apollo", "hunter", "manual"}
    is_valid = valid_format and not reject_guessed

    return {
        "email_valid_format": int(valid_format),
        "email_verified": int(email_verified),
        "hunter_score": hunter_score,
        "is_valid": is_valid,
        "reject_reason": (
            "guessed_personal_email"
            if reject_guessed
            else ("invalid_format" if not valid_format else ("generic_ok" if generic else ""))
        ),
    }


def validate_contacts_df(df: pd.DataFrame, use_hunter: bool = True) -> pd.DataFrame:
    results = [validate_contact_row(row.to_dict(), use_hunter=use_hunter) for _, row in df.iterrows()]
    enriched = pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)
    return enriched
