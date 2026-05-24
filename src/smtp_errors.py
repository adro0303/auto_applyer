"""Classify SMTP errors for safe send status handling."""

from __future__ import annotations

import re
import smtplib


SMTP_UNCERTAIN_MIN = 400
SMTP_UNCERTAIN_MAX = 499
SMTP_UNCERTAIN_CODES = {421, 450, 451, 452}

UNCERTAIN_CONSOLE_MESSAGE = (
    "SMTP returned a temporary 4xx response. The email may or may not have been "
    "delivered. Please check Gmail Sent before retrying."
)


def extract_smtp_code(exc: BaseException) -> int | None:
    if isinstance(exc, smtplib.SMTPResponseException):
        return int(exc.smtp_code)
    match = re.search(r"\((\d{3}),", str(exc))
    if match:
        return int(match.group(1))
    match = re.search(r"\b([45]\d{2})\b", str(exc))
    if match:
        return int(match.group(1))
    return None


def is_temporary_smtp_code(code: int | None) -> bool:
    if code is None:
        return False
    if code in SMTP_UNCERTAIN_CODES:
        return True
    return SMTP_UNCERTAIN_MIN <= code <= SMTP_UNCERTAIN_MAX


def is_permanent_smtp_code(code: int | None) -> bool:
    return code is not None and code >= 500


def classify_smtp_exception(exc: BaseException) -> dict:
    """
    Return kind: 'uncertain' | 'failed' and optional smtp_code.
    4xx -> uncertain (may have been delivered).
    5xx, auth, recipient refused -> failed.
    """
    code = extract_smtp_code(exc)

    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return {"kind": "failed", "smtp_code": code, "reason": "auth_failure"}
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return {"kind": "failed", "smtp_code": code, "reason": "recipient_refused"}

    if is_temporary_smtp_code(code):
        return {"kind": "uncertain", "smtp_code": code, "reason": "temporary_4xx"}

    if is_permanent_smtp_code(code):
        return {"kind": "failed", "smtp_code": code, "reason": "permanent_5xx"}

    if isinstance(exc, (smtplib.SMTPDataError, smtplib.SMTPSenderRefused)):
        if is_temporary_smtp_code(code):
            return {"kind": "uncertain", "smtp_code": code, "reason": "temporary_4xx"}
        return {"kind": "failed", "smtp_code": code, "reason": "smtp_data_error"}

    return {"kind": "failed", "smtp_code": code, "reason": "unknown_error"}
