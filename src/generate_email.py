from src.email_content import build_email_body, get_first_name, pick_subject, safe_text
from src.lead_scoring import detect_contact_type


def _contact_type(contact: dict) -> str:
    if contact.get("contact_type"):
        return contact["contact_type"]
    record = {
        "role": contact.get("role"),
        "company_name": contact.get("company_name"),
        "company_industry": contact.get("industry"),
        "keywords": "",
        "company_employee_count": contact.get("employee_count"),
    }
    return detect_contact_type(record)


def _resolve_first_name(contact: dict) -> str:
    first = safe_text(contact.get("first_name"))
    if first:
        return first
    full = contact.get("full_name") or contact.get("name")
    return get_first_name(full)


def generate_subject(contact: dict, country: str) -> str:
    company_name = contact.get("company_name") or ""
    return pick_subject(_contact_type(contact), company_name, contact.get("email") or "")


def generate_email(
    contact: dict,
    company: dict,
    personalised_detail: str,
    country: str,
    followup: bool = False,
) -> str:
    company_name = contact.get("company_name") or company.get("company", "")
    industry = contact.get("industry") or company.get("industry")
    contact_type = _contact_type(contact)
    first_name = _resolve_first_name(contact)

    if followup:
        from src.countries import template_country

        is_spain = template_country(country) == "spain"
        if is_spain:
            return (
                f"Hi {first_name},\n\n"
                "Solo quería hacer un seguimiento breve por si viste mi mensaje anterior. "
                "Sigo interesado en oportunidades junior/graduate en software o applied AI.\n\n"
                "Gracias de nuevo por vuestro tiempo."
            )
        return (
            f"Hi {first_name},\n\n"
            "Just a brief follow-up in case my earlier note got buried. "
            "I'm still interested in junior/graduate software or applied AI opportunities.\n\n"
            "Thanks again for your time."
        )

    return build_email_body(
        contact_type,
        country,
        first_name=first_name,
        company_name=company_name,
        industry=industry,
    )
