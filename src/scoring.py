from src.lead_scoring import score_contact_record


def score_contact(contact: dict, company: dict | None = None) -> dict:
    company = company or {}
    record = {
        **contact,
        "company_name": contact.get("company_name") or company.get("name"),
        "company_industry": company.get("industry") or contact.get("industry"),
        "company_employee_count": company.get("employee_count") or contact.get("employee_count"),
        "company_country": company.get("country") or contact.get("company_country") or contact.get("country"),
        "company_domain": company.get("domain") or contact.get("domain"),
        "company_website": company.get("website") or contact.get("website"),
        "campaign_country": contact.get("campaign_country") or contact.get("country"),
        "keywords": "",
    }
    return score_contact_record(record)


def score_all_contacts(repo, contacts: list[dict]) -> None:
    for contact in contacts:
        company = {
            "name": contact.get("company_name"),
            "industry": contact.get("industry"),
            "employee_count": contact.get("employee_count"),
            "country": contact.get("company_country") or contact.get("country"),
            "domain": contact.get("domain"),
            "website": contact.get("website"),
        }
        result = score_contact(contact, company)
        with repo.connect() as conn:
            conn.execute(
                """
                UPDATE contacts
                SET lead_score = ?, contact_type = ?, score_notes = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    result["lead_score"],
                    result["contact_type"],
                    result.get("score_notes"),
                    contact["id"],
                ),
            )
