"""Manual CSV import helpers."""

import pandas as pd

from src.countries import normalize_country
from src.db.repository import Repository


def import_manual_csv(repo: Repository, companies_path: str, contacts_path: str) -> dict[str, int]:
    companies = pd.read_csv(companies_path)
    contacts = pd.read_csv(contacts_path)
    imported = 0

    for _, row in companies.iterrows():
        repo.upsert_company(
            {
                "name": row["company"],
                "website": row.get("website"),
                "country": normalize_country(str(row.get("country", ""))),
                "city": row.get("city"),
                "industry": row.get("industry"),
                "why_interesting": row.get("why_interesting"),
            }
        )

    for _, row in contacts.iterrows():
        country = normalize_country(str(row.get("country", "")))
        repo.upsert_contact(
            {
                "company_name": row["company"],
                "name": row["name"],
                "role": row.get("role"),
                "email": str(row["email"]).strip().lower(),
                "linkedin": row.get("linkedin"),
                "country": country,
                "source": row.get("source", "manual"),
                "status": "new",
            }
        )
        imported += 1

    return {"imported": imported}
