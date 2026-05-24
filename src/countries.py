UK_ALIASES = {
    "uk",
    "united kingdom",
    "great britain",
    "gb",
    "england",
    "scotland",
    "wales",
    "northern ireland",
}

SPAIN_ALIASES = {
    "spain",
    "es",
    "españa",
    "espana",
}

SUPPORTED_COUNTRIES = ("uk", "spain")


def normalize_country(value: str | None) -> str:
    if not value or not isinstance(value, str):
        return ""
    raw = value.strip().lower()
    if raw in UK_ALIASES:
        return "uk"
    if raw in SPAIN_ALIASES:
        return "spain"
    return raw


def is_target_country(value: str | None, targets: list[str] | None = None) -> bool:
    normalized = normalize_country(value)
    targets = targets or list(SUPPORTED_COUNTRIES)
    return normalized in {t.lower() for t in targets}


def template_country(country: str | None) -> str:
    normalized = normalize_country(country)
    return "spain" if normalized == "spain" else "uk"


def default_subject(country: str | None) -> str:
    if template_country(country) == "spain":
        return "Perfil junior en software / IA"
    return "Backend / AI Graduate interested in your team"
