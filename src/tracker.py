"""Legacy tracker — use src.db instead."""

from src.db.repository import Repository
from src.db.schema import init_db


def insert_draft(row: dict):
    repo = Repository()
    init_db()
    company_id = repo.upsert_company({"name": row.get("company", "")})
    contact_id = repo.upsert_contact(
        {
            "company_id": company_id,
            "name": row.get("name", ""),
            "role": row.get("role"),
            "email": row.get("email", ""),
            "country": row.get("country"),
            "status": "drafted",
        }
    )
    repo.insert_message(
        {
            "contact_id": contact_id,
            "subject": row.get("subject"),
            "body": row.get("email_body"),
            "status": "draft",
        }
    )
