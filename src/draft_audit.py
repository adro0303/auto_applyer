"""Quality checks for generated outreach drafts before CSV export."""

from __future__ import annotations

from src.email_content import clean_company_name, safe_text

FORBIDDEN_SUBSTRINGS = ("None", "{{", "}}", "â", "B Corpâ")


def audit_draft(
    subject: str | None,
    body: str | None,
    *,
    raw_company_name: str | None = None,
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
