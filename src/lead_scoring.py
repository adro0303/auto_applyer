import re
from typing import Any

from src.countries import normalize_country

AGENCY_NAME_HINTS = (
    "recruitment",
    "recruiting",
    "staffing",
    "search",
    "talent",
    "consultancy",
    "consulting agency",
    "headhunt",
)

AGENCY_INDUSTRY_HINTS = ("staffing", "recruiting", "recruitment", "executive search")

SENSITIVE_INDUSTRY = ("defense", "defence", "military", "aerospace")

TECH_ROLES = (
    "cto",
    "chief technology",
    "head of engineering",
    "engineering manager",
    "it manager",
    "head of it",
    "technology manager",
)

OPS_ROLES = (
    "operations manager",
    "head of operations",
    "digital transformation",
    "business transformation",
)

RECRUITER_ROLES = (
    "talent acquisition",
    "recruiter",
    "recruitment",
    "people partner",
    "hr manager",
    "human resources",
    "tech recruiter",
    "technical recruiter",
)

FOUNDER_ROLES = ("founder", "co-founder", "cofounder", "ceo")


def _contains(text: str, keywords: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def is_agency_company(record: dict[str, Any]) -> bool:
    name = str(record.get("company_name") or "").lower()
    industry = str(record.get("company_industry") or "").lower()

    if _contains(name, AGENCY_NAME_HINTS):
        return True
    if _contains(industry, AGENCY_INDUSTRY_HINTS):
        return True
    if "recruitment agency" in name or "staffing" in name:
        return True

    keywords = str(record.get("keywords") or "").lower()
    if _contains(name, ("consultancy", "consulting", "search", "staffing", "recruit")):
        if _contains(
            keywords,
            ("staffing", "recruitment", "recruiting", "talent acquisition", "search agency"),
        ):
            return True
    return False


def detect_contact_type(record: dict[str, Any]) -> str:
    role = str(record.get("role") or "").lower()
    employees = record.get("company_employee_count")

    if is_agency_company(record):
        return "agency_recruiter"

    if _contains(role, ("technical recruiter", "tech recruiter")):
        return "agency_recruiter" if is_agency_company(record) else "direct_recruiter"

    if _contains(role, RECRUITER_ROLES):
        return "direct_recruiter"

    if _contains(role, TECH_ROLES):
        return "technical_decision_maker"

    if _contains(role, OPS_ROLES):
        return "operations_transformation"

    if _contains(role, FOUNDER_ROLES):
        if employees is None or int(employees) <= 200:
            return "founder"
        return "general"

    if _contains(role, ("student", "intern")):
        return "general"

    return "general"


def score_contact_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return lead_score, score_notes (semicolon-separated), contact_type."""
    score = 50.0
    notes: list[str] = []
    role = str(record.get("role") or "")
    role_l = role.lower()
    campaign = normalize_country(record.get("campaign_country"))
    company_country = normalize_country(record.get("company_country"))
    contact_country = normalize_country(record.get("country"))
    employees = record.get("company_employee_count")
    usability = record.get("usability_status")
    email_status = str(record.get("email_status") or "").lower()
    catch_all = str(record.get("catch_all_status") or "").lower()
    is_catch_all = catch_all in {"catch-all", "catch all", "accept_all", "accept-all"}

    contact_type = detect_contact_type(record)

    # Role points
    if _contains(role_l, ("technical recruiter", "tech recruiter", "talent acquisition manager")):
        score += 25
    elif _contains(role_l, RECRUITER_ROLES):
        score += 20
    elif _contains(role_l, TECH_ROLES):
        score += 30
    elif _contains(role_l, ("it manager", "technology manager")):
        score += 25
    elif _contains(role_l, OPS_ROLES):
        score += 15
    elif _contains(role_l, FOUNDER_ROLES):
        score += 25
    elif _contains(role_l, ("student", "intern")):
        score -= 40
    elif _contains(role_l, ("account executive", "sales manager", "marketing manager")):
        score -= 25
    else:
        score += 2

    # Company / campaign
    if campaign and company_country == campaign:
        score += 15
    if campaign and contact_country == campaign:
        score += 5
    if campaign and contact_country and contact_country != campaign:
        score -= 3
        notes.append("contact location differs from company country")

    # Email
    if email_status in {"verified", "valid"}:
        if is_catch_all:
            score += 8
        else:
            score += 15
    elif usability == "risky":
        score -= 8

    if is_catch_all:
        score -= 5
        notes.append("catch-all domain")

    domain = record.get("company_domain") or record.get("company_website")
    if domain:
        score += 10

    if employees is not None:
        try:
            n = int(employees)
            if 11 <= n <= 500:
                score += 10
            elif n > 1000 and contact_type not in {"direct_recruiter", "agency_recruiter"}:
                score -= 10
        except (TypeError, ValueError):
            pass

    industry_l = str(record.get("company_industry") or "").lower()
    if _contains(industry_l, SENSITIVE_INDUSTRY):
        score -= 5
        notes.append("review sensitive sector before approving")

    if is_agency_company(record):
        notes.append("agency contact")
        contact_type = "agency_recruiter"
        score = min(score, 80.0)

    if usability == "needs_email":
        score -= 40

    score = round(max(0.0, min(100.0, score)), 1)
    return {
        "lead_score": score,
        "score_notes": "; ".join(dict.fromkeys(notes)),
        "contact_type": contact_type,
    }


# Backward compatibility for legacy template callers
def get_role_messages(contact_type: str, country: str) -> tuple[str, str]:
    from src.email_content import build_email_body

    body = build_email_body(
        contact_type,
        country,
        first_name="there",
        company_name="your company",
        industry=None,
    )
    parts = body.split("\n\n", 2)
    if len(parts) >= 3:
        return parts[1], parts[2]
    return parts[0] if parts else "", ""
