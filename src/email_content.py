"""Human-readable email bodies and subjects — variable-based templates, no Apollo dumps."""

import re
import unicodedata

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

SPAIN_SUBJECT_DIRECT = (
    "Perfil junior en software e IA aplicada",
    "Candidato junior Computer Science & AI",
    "Interés en oportunidades de software / automatización",
    "Perfil junior para tecnología, IA y automatización",
)

SPAIN_SUBJECT_AGENCY = (
    "Perfil junior software / IA aplicada",
    "Candidato junior backend / automatización",
    "Computer Science & AI Graduate",
)

SPAIN_SUBJECT_FOUNDER = (
    "Perfil junior para software, IA y automatización",
    "Ayuda con tecnología, automatización e IA aplicada",
    "Computer Science & AI Graduate interesado en {company}",
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


GENERIC_NAME_TOKENS_ES = {
    "talento",
    "talento y personas",
    "personas",
    "recursos humanos",
    "rrhh",
    "seleccion",
    "seleccion de personal",
    "equipo",
    "equipo de talento",
    "equipo de personas",
    "equipo de seleccion",
    "careers",
    "empleo",
    "jobs",
}

GENERIC_NAME_TOKENS_EN = {
    "talent",
    "talent team",
    "people",
    "people team",
    "human resources",
    "hr",
    "recruitment",
    "recruiting",
    "careers",
    "jobs",
    "hiring",
    "team",
}

BAD_FIRST_TOKENS = {"talento", "recursos", "rrhh", "people", "talent", "hr", "careers", "jobs", "equipo", "team"}


def _normalize_for_match(value: str | None) -> str:
    text = safe_text(value).strip().lower()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text)
    return text


def _looks_non_personal_name(name: str | None) -> bool:
    normalized = _normalize_for_match(name)
    if not normalized:
        return True
    if normalized in {"none", "nan", "null"}:
        return True
    first = normalized.split()[0] if normalized.split() else ""
    if first in BAD_FIRST_TOKENS:
        return True
    tokens = GENERIC_NAME_TOKENS_ES | GENERIC_NAME_TOKENS_EN
    return any(token in normalized for token in tokens)


def _email_local_part(email: str | None) -> str:
    value = safe_text(email).lower()
    if "@" not in value:
        return ""
    return value.split("@", 1)[0].strip()


def _contains_tokenized(local_part: str, token: str) -> bool:
    if not local_part or not token:
        return False
    normalized = re.sub(r"[-_.+]+", " ", local_part)
    parts = [p for p in normalized.split() if p]
    return token in parts or local_part == token


def _classify_email_local_part(email: str | None) -> str:
    local = _email_local_part(email)
    if not local:
        return "unknown"

    talent_tokens = {
        "talent",
        "people",
        "hr",
        "rrhh",
        "careers",
        "jobs",
        "recruitment",
        "recruiting",
        "hiring",
        "seleccion",
        "selección",
        "recursoshumanos",
    }
    generic_tokens = {"info", "contact", "hello", "hola", "admin", "support", "team", "office"}

    if any(_contains_tokenized(local, tok) for tok in talent_tokens):
        return "talent_generic"
    if any(_contains_tokenized(local, tok) for tok in generic_tokens):
        return "generic"
    return "unknown"


def _looks_company_like_name(name: str | None, company_name: str | None) -> bool:
    n = _normalize_for_match(name)
    c = _normalize_for_match(company_name)
    if not n or not c:
        return False
    name_parts = n.split()
    company_parts = c.split()
    if len(name_parts) == 1 and company_parts and name_parts[0] == company_parts[0]:
        return True
    return n in c


def get_greeting_name(
    name: str | None,
    country: str = "uk",
    *,
    contact_type: str = "general",
    company_name: str | None = None,
    email: str | None = None,
) -> str:
    country_norm = normalize_country(country)
    local_kind = _classify_email_local_part(email)

    if local_kind == "talent_generic":
        if country_norm == "spain":
            return "equipo" if contact_type == "agency_recruiter" else "equipo de Talento"
        return "Talent team" if contact_type == "direct_recruiter" else "team"

    if local_kind == "generic":
        return "equipo" if country_norm == "spain" else "team"

    person_first = get_first_name(name)
    if (
        person_first
        and person_first.lower() not in {"there", "none"}
        and not _looks_non_personal_name(name)
        and not _looks_company_like_name(name, company_name)
    ):
        return person_first

    if country_norm == "spain":
        if contact_type == "agency_recruiter":
            return "equipo"
        if contact_type in {"direct_recruiter", "founder", "technical_decision_maker"}:
            return "equipo de Talento"
        return "equipo"

    if contact_type == "direct_recruiter":
        return "Talent team"
    return "team"


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


def _direct_opener(greeting_name: str, company: str, industry: str | None) -> str:
    sector = specific_sector_angle(industry)
    if sector:
        return (
            f"Hi {greeting_name},\n\n"
            f"I came across {company} and wanted to reach out in case you are hiring "
            f"for junior or graduate tech roles. I noticed your work in {sector}."
        )
    return (
        f"Hi {greeting_name},\n\n"
        f"I came across {company} and wanted to reach out in case you are hiring "
        f"for junior or graduate tech roles."
    )


def _direct_recruiter_body(greeting_name: str, company: str, industry: str | None) -> str:
    opener = _direct_opener(greeting_name, company, industry)
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


def _agency_recruiter_body(greeting_name: str, company: str) -> str:
    return (
        f"Hi {greeting_name},\n\n"
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


def _founder_body_spain(greeting_name: str, company: str) -> str:
    return (
        f"Hola {greeting_name},\n\n"
        f"He visto {company} y quería escribirte directamente porque me interesa mucho cómo empresas "
        "pequeñas y medianas pueden usar software, automatización e IA para mejorar procesos reales.\n\n"
        "Soy graduado en Computer Science & Artificial Intelligence, con experiencia práctica en backend, "
        "APIs, bases de datos, Python y automatización.\n\n"
        "Estoy buscando una oportunidad junior donde pueda aportar en tareas de tecnología, soporte, "
        "automatización de procesos, reporting o IA aplicada, aprendiendo dentro de un entorno real de empresa.\n\n"
        "Te adjunto mi CV por si pudiera tener sentido hablar ahora o más adelante.\n\n"
        "Un saludo,\n"
        "Adrian"
    )


def _direct_recruiter_body_spain_v2(greeting_name: str, company: str) -> str:
    return (
        f"Hola {greeting_name},\n\n"
        f"He visto {company} y quería escribirte por si actualmente estáis buscando perfiles junior o graduate "
        "en tecnología, software, automatización o IA aplicada.\n\n"
        "Soy graduado en Computer Science & Artificial Intelligence, con experiencia práctica en backend, APIs, "
        "PostgreSQL, TypeScript, Python y proyectos de automatización/IA.\n\n"
        "Me interesan especialmente roles donde pueda ayudar a mejorar procesos internos, construir herramientas "
        "útiles y aplicar tecnología a problemas reales de negocio.\n\n"
        "Te adjunto mi CV por si pudiera encajar ahora o más adelante.\n\n"
        "Un saludo,\n"
        "Adrian"
    )


def _agency_recruiter_body_spain_v2(greeting_name: str, company: str) -> str:
    return (
        f"Hola {greeting_name},\n\n"
        f"He visto {company} y quería escribirte por si lleváis procesos para perfiles junior o graduate en "
        "software, backend, automatización o IA aplicada.\n\n"
        "Soy graduado en Computer Science & Artificial Intelligence, con experiencia práctica en backend, APIs, "
        "PostgreSQL, TypeScript, Python y proyectos de automatización/IA.\n\n"
        "Si estáis trabajando en alguna posición junior donde mi perfil pueda encajar, estaría encantado de que "
        "me tuvieras en cuenta.\n\n"
        "Te adjunto mi CV para contexto.\n\n"
        "Un saludo,\n"
        "Adrian"
    )


def build_email_body(
    contact_type: str,
    country: str,
    *,
    greeting_name: str,
    company_name: str,
    industry: str | None = None,
) -> str:
    greeting_name = safe_text(greeting_name, "team")
    company = clean_company_name(company_name)
    is_spain = normalize_country(country) == "spain"

    if contact_type == "agency_recruiter":
        if is_spain:
            return _agency_recruiter_body_spain_v2(greeting_name, company)
        return _agency_recruiter_body(greeting_name, company)

    if is_spain and contact_type in {"founder", "founder_or_executive"}:
        return _founder_body_spain(greeting_name, company)

    if is_spain:
        return _direct_recruiter_body_spain_v2(greeting_name, company)
    return _direct_recruiter_body(greeting_name, company, industry)


def pick_subject(contact_type: str, company_name: str, email: str) -> str:
    """Deterministic but varied subject from professional pool."""
    company = clean_company_name(company_name)
    idx = sum(ord(c) for c in (email or company)) % len(SUBJECT_OPTIONS)
    return SUBJECT_OPTIONS[idx]


def pick_subject_for_country(contact_type: str, company_name: str, email: str, country: str) -> str:
    company = clean_company_name(company_name)
    is_spain = normalize_country(country) == "spain"
    if not is_spain:
        return pick_subject(contact_type, company_name, email)
    if contact_type == "agency_recruiter":
        pool = SPAIN_SUBJECT_AGENCY
    elif contact_type in {"founder", "founder_or_executive"}:
        pool = tuple(s.format(company=company) for s in SPAIN_SUBJECT_FOUNDER)
    else:
        pool = SPAIN_SUBJECT_DIRECT
    idx = sum(ord(c) for c in (email or company)) % len(pool)
    return pool[idx]
