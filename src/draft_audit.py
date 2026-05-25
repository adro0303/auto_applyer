"""Quality checks for generated outreach drafts before CSV export."""

from __future__ import annotations

from src.countries import normalize_country
from src.email_content import clean_company_name, safe_text

FORBIDDEN_SUBSTRINGS = ("None", "{{", "}}", "â", "Ã", "B Corpâ")
BAD_GREETINGS_SPAIN = (
    "hola talento,",
    "hola recursos,",
    "hola rrhh,",
    "hola people,",
    "hola careers,",
    "hola jobs,",
    "hola none,",
    "hola ,",
)
BAD_GREETINGS_UK = (
    "hi talent,",
    "hi hr,",
    "hi people,",
    "hi careers,",
    "hi jobs,",
    "hi none,",
    "hi,",
)


def audit_draft(
    subject: str | None,
    body: str | None,
    *,
    raw_company_name: str | None = None,
    country: str | None = None,
    first_name: str | None = None,
) -> list[str]:
    issues: list[str] = []
    subject_s = safe_text(subject)
    body_s = safe_text(body)

    if not subject_s:
        issues.append("empty subject")
    if not body_s:
        issues.append("empty email_body")

    first_line = body_s.splitlines()[0].strip() if body_s else ""
    if first_line == "Hi,":
        issues.append('greeting is "Hi," without first name')
    first_line_l = first_line.lower()
    if normalize_country(country) == "spain":
        if first_line == "Hi,":
            issues.append('spanish draft uses "Hi,"')
        if first_line == "Hola," and safe_text(first_name):
            issues.append('greeting is "Hola," without first name')
        if any(first_line_l.startswith(prefix) for prefix in BAD_GREETINGS_SPAIN):
            issues.append(f"contains bad spanish greeting: {first_line!r}")
    else:
        if any(first_line_l.startswith(prefix) for prefix in BAD_GREETINGS_UK):
            issues.append(f"contains bad uk greeting: {first_line!r}")

    for token in FORBIDDEN_SUBSTRINGS:
        if token in subject_s or token in body_s:
            issues.append(f"contains forbidden token: {token!r}")

    if raw_company_name:
        raw = safe_text(raw_company_name)
        cleaned = clean_company_name(raw)
        if raw and raw != cleaned and raw in body_s:
            issues.append(f"contains raw company name: {raw!r}")

    return issues


def audit_draft_rows(rows: list[dict], *, fail: bool = True) -> list[tuple[dict, list[str]]]:
    problems: list[tuple[dict, list[str]]] = []
    for row in rows:
        issues = audit_draft(
            row.get("subject"),
            row.get("email_body") or row.get("body"),
            raw_company_name=row.get("company") or row.get("company_name"),
            country=row.get("country"),
            first_name=row.get("first_name"),
        )
        if issues:
            problems.append((row, issues))

    if problems and fail:
        lines = ["Draft audit failed:"]
        for row, issues in problems:
            label = row.get("email") or row.get("name") or row.get("message_id")
            lines.append(f"  - {label}: {', '.join(issues)}")
        raise SystemExit("\n".join(lines))

    return problems
