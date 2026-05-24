"""Human-readable email bodies and subjects — variable-based templates, no Apollo dumps."""

import re

from src.countries import normalize_country

# Only used when industry is clearly non-generic (healthcare, travel, defence).
SPECIFIC_SECTOR_ANGLES = {
    "health": "health and care services",
    "hospital": "health and care services",
    "home care": "health and care services",
    "healthcare": "health and care services",
    "travel": "travel and customer operations",
    "leisure": "travel and customer operations",
    "airline": "travel and customer operations",
    "defense": "specialist technology and operations",
    "defence": "specialist technology and operations",
    "military": "specialist technology and operations",
    "aerospace": "specialist technology and operations",
}

SUBJECT_OPTIONS = (
    "Junior Software / Backend Graduate",
    "Graduate Backend / Applied AI Profile",
    "Computer Science & AI Graduate",
)


def safe_text(value: str | None, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "null"}:
        return fallback
    return text


def get_first_name(full_name: str | None) -> str:
    name = safe_text(full_name)
    if not name:
        return "there"
    first = name.split()[0]
    return first if first else "there"


def clean_company_name(company: str | None) -> str:
    text = safe_text(company)
    if not text:
        return "your company"

    if "|" in text:
        text = text.split("|", 1)[0].strip()

    text = re.sub(r"\s*\([^)]+\)\s*", " ", text).strip()

    if " - " in text:
        left, right = text.rsplit(" - ", 1)
        right_l = right.strip().lower()
        looks_descriptive = (
            len(right.strip().split()) >= 3
            or right_l.startswith(("the ", "a ", "an "))
            or any(
                hint in right_l
                for hint in ("experts", "specialists", "leading", "global", "online marketplace")
            )
        )
        if looks_descriptive:
            text = left.strip()

    text = re.sub(r"\s+", " ", text).strip()
    return text if text else "your company"


def specific_sector_angle(industry: str | None) -> str | None:
    """Return a sector phrase only when industry is clearly non-generic."""
    industry_l = safe_text(industry).lower()
    if not industry_l:
        return None
    for key, phrase in SPECIFIC_SECTOR_ANGLES.items():
        if key in industry_l:
            return phrase
    return None


def _direct_opener(first_name: str, company: str, industry: str | None) -> str:
    sector = specific_sector_angle(industry)
    if sector:
        return (
            f"Hi {first_name},\n\n"
            f"I came across {company} and wanted to reach out in case you are hiring "
            f"for junior or graduate tech roles. I noticed your work in {sector}."
        )
    return (
        f"Hi {first_name},\n\n"
        f"I came across {company} and wanted to reach out in case you are hiring "
        f"for junior or graduate tech roles."
    )


def _direct_recruiter_body(first_name: str, company: str, industry: str | None) -> str:
    opener = _direct_opener(first_name, company, industry)
    return (
        f"{opener}\n\n"
        "I'm a recent Computer Science & AI graduate based in the UK, with hands-on "
        "backend experience in TypeScript, NestJS, PostgreSQL, REST APIs and "
        "automation/AI projects.\n\n"
        "I would be interested in being considered for junior or graduate software, backend or applied AI "
        "opportunities now or in the coming months.\n\n"
        "I've attached my CV for context.\n\n"
        "Best regards,\n"
        "Adrian"
    )


def _agency_recruiter_body(first_name: str, company: str) -> str:
    return (
        f"Hi {first_name},\n\n"
        f"I came across {company} and saw that you work in tech recruitment.\n\n"
        "I'm a recent Computer Science & AI graduate based in the UK, with hands-on "
        "backend experience in TypeScript, NestJS, PostgreSQL, REST APIs and "
        "automation/AI projects.\n\n"
        "If you are working on junior or graduate software, backend or applied AI "
        "roles, I'd be happy to be considered.\n\n"
        "I've attached my CV for context.\n\n"
        "Best regards,\n"
        "Adrian"
    )


def _direct_recruiter_body_spain(first_name: str, company: str, industry: str | None) -> str:
    sector = specific_sector_angle(industry)
    if sector:
        opener = (
            f"Hi {first_name},\n\n"
            f"Me puse en contacto con {company} por si contratáis perfiles junior o graduate "
            f"en tech. Vi vuestro trabajo en {sector}."
        )
    else:
        opener = (
            f"Hi {first_name},\n\n"
            f"Me puse en contacto con {company} por si contratáis perfiles junior o graduate en tech."
        )
    return (
        f"{opener}\n\n"
        "Me acabo de graduar en Computer Science & AI en Reino Unido, con experiencia "
        "práctica en backend (TypeScript, NestJS, PostgreSQL, APIs REST) y proyectos de "
        "automatización/IA.\n\n"
        "Me interesarían oportunidades junior o graduate en software, backend o applied AI "
        "ahora o en los próximos meses.\n\n"
        "Adjunto mi CV.\n\n"
        "Un saludo,\n"
        "Adrian"
    )


def _agency_recruiter_body_spain(first_name: str, company: str) -> str:
    return (
        f"Hi {first_name},\n\n"
        f"Me puse en contacto con {company} porque trabajáis en reclutamiento tech.\n\n"
        "Me acabo de graduar en Computer Science & AI en Reino Unido, con experiencia "
        "práctica en backend (TypeScript, NestJS, PostgreSQL, APIs REST) y proyectos de "
        "automatización/IA.\n\n"
        "Si tenéis roles junior o graduate en software, backend o applied AI, me encantaría "
        "ser considerado.\n\n"
        "Adjunto mi CV.\n\n"
        "Un saludo,\n"
        "Adrian"
    )


def build_email_body(
    contact_type: str,
    country: str,
    *,
    first_name: str,
    company_name: str,
    industry: str | None = None,
) -> str:
    first_name = safe_text(first_name, "there")
    company = clean_company_name(company_name)
    is_spain = normalize_country(country) == "spain"

    if contact_type == "agency_recruiter":
        if is_spain:
            return _agency_recruiter_body_spain(first_name, company)
        return _agency_recruiter_body(first_name, company)

    if is_spain:
        return _direct_recruiter_body_spain(first_name, company, industry)
    return _direct_recruiter_body(first_name, company, industry)


def pick_subject(contact_type: str, company_name: str, email: str) -> str:
    """Deterministic but varied subject from professional pool."""
    company = clean_company_name(company_name)
    idx = sum(ord(c) for c in (email or company)) % len(SUBJECT_OPTIONS)
    return SUBJECT_OPTIONS[idx]
