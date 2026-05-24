import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Repository:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or settings.db_path

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def upsert_company(self, data: dict[str, Any]) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO companies (name, website, country, city, industry, employee_count, why_interesting)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    website=COALESCE(excluded.website, companies.website),
                    country=COALESCE(excluded.country, companies.country),
                    city=COALESCE(excluded.city, companies.city),
                    industry=COALESCE(excluded.industry, companies.industry),
                    employee_count=COALESCE(excluded.employee_count, companies.employee_count),
                    why_interesting=COALESCE(excluded.why_interesting, companies.why_interesting)
                """,
                (
                    data["name"],
                    data.get("website"),
                    data.get("country"),
                    data.get("city"),
                    data.get("industry"),
                    data.get("employee_count"),
                    data.get("why_interesting"),
                ),
            )
            cur.execute("SELECT id FROM companies WHERE name = ?", (data["name"],))
            return int(cur.fetchone()[0])

    def upsert_contact(self, data: dict[str, Any]) -> int:
        company_id = data.get("company_id")
        if not company_id and data.get("company_name"):
            company_id = self.upsert_company({"name": data["company_name"]})

        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO contacts (
                    company_id, name, role, email, linkedin, country, source,
                    email_valid_format, email_verified, hunter_score, lead_score, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    company_id=COALESCE(excluded.company_id, contacts.company_id),
                    name=COALESCE(excluded.name, contacts.name),
                    role=COALESCE(excluded.role, contacts.role),
                    linkedin=COALESCE(excluded.linkedin, contacts.linkedin),
                    country=COALESCE(excluded.country, contacts.country),
                    source=COALESCE(excluded.source, contacts.source),
                    email_valid_format=excluded.email_valid_format,
                    email_verified=excluded.email_verified,
                    hunter_score=COALESCE(excluded.hunter_score, contacts.hunter_score),
                    lead_score=COALESCE(excluded.lead_score, contacts.lead_score),
                    updated_at=datetime('now')
                """,
                (
                    company_id,
                    data["name"],
                    data.get("role"),
                    data["email"].strip().lower(),
                    data.get("linkedin"),
                    data.get("country"),
                    data.get("source"),
                    int(data.get("email_valid_format", 0)),
                    int(data.get("email_verified", 0)),
                    data.get("hunter_score"),
                    data.get("lead_score", 0),
                    data.get("status", "new"),
                ),
            )
            cur.execute("SELECT id FROM contacts WHERE email = ?", (data["email"].strip().lower(),))
            return int(cur.fetchone()[0])

    def get_or_create_campaign(self, name: str, country: str, daily_limit: int = 10) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO campaigns (name, country, daily_limit)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO NOTHING
                """,
                (name, country, daily_limit),
            )
            cur.execute("SELECT id FROM campaigns WHERE name = ?", (name,))
            return int(cur.fetchone()[0])

    def insert_message(self, data: dict[str, Any]) -> int:
        template_type = data.get("template_type") or data.get("message_type", "initial")
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO messages (
                    contact_id, campaign_id, subject, body, message_type, template_type,
                    campaign_country, status, dry_run, attachment_path,
                    source_file, import_batch_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["contact_id"],
                    data.get("campaign_id"),
                    data.get("subject"),
                    data.get("body"),
                    data.get("message_type", template_type),
                    template_type,
                    data.get("campaign_country"),
                    data.get("status", "draft"),
                    int(data.get("dry_run", 1)),
                    data.get("attachment_path"),
                    data.get("source_file"),
                    data.get("import_batch_id"),
                ),
            )
            return int(cur.lastrowid)

    def create_import_batch(self, data: dict[str, Any]) -> int:
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO import_batches (
                    source_file, country, total_rows, notes
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    data["source_file"],
                    data["country"],
                    data.get("total_rows", 0),
                    data.get("notes"),
                ),
            )
            return int(cur.lastrowid)

    def update_import_batch_stats(self, batch_id: int, **stats: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE import_batches SET
                    usable_count = ?,
                    risky_count = ?,
                    missing_count = ?,
                    contacts_inserted = ?,
                    contacts_updated = ?,
                    companies_inserted = ?,
                    companies_updated = ?
                WHERE id = ?
                """,
                (
                    stats.get("usable", 0),
                    stats.get("risky", 0),
                    stats.get("missing", 0),
                    stats.get("contacts_inserted", 0),
                    stats.get("contacts_updated", 0),
                    stats.get("companies_inserted", 0),
                    stats.get("companies_updated", 0),
                    batch_id,
                ),
            )

    def message_exists_for_contact_campaign(
        self,
        contact_email: str,
        campaign_country: str,
        template_type: str,
        active_statuses: tuple[str, ...] = ("draft", "approved", "sent"),
    ) -> bool:
        placeholders = ",".join("?" * len(active_statuses))
        query = f"""
            SELECT 1 FROM messages m
            JOIN contacts c ON c.id = m.contact_id
            WHERE lower(c.email) = lower(?)
              AND lower(m.campaign_country) = lower(?)
              AND m.template_type = ?
              AND m.status IN ({placeholders})
            LIMIT 1
        """
        with self.connect() as conn:
            row = conn.execute(
                query,
                (contact_email.strip().lower(), campaign_country, template_type, *active_statuses),
            ).fetchone()
            return row is not None

    def approve_message(self, message_id: int, approved_by: str = "cli") -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE messages
                SET status = 'approved',
                    approved_at = ?,
                    approved_by = ?,
                    attachment_path = COALESCE(attachment_path, ?)
                WHERE id = ? AND status IN ('draft', 'approved')
                """,
                (_utc_now(), approved_by, str(settings.cv_file), message_id),
            )
            return cur.rowcount > 0

    def approve_messages_from_csv(self, csv_path: Path, approved_by: str = "csv") -> dict[str, int]:
        import pandas as pd

        df = pd.read_csv(csv_path)
        if "message_id" not in df.columns or "approved" not in df.columns:
            raise ValueError("CSV must include message_id and approved columns")

        approved_mask = df["approved"].astype(str).str.strip().str.lower().isin({"yes", "true", "1"})
        ids = df.loc[approved_mask, "message_id"].dropna().astype(int).tolist()

        stats = {"rows_in_csv": len(df), "approved_requested": len(ids), "approved_updated": 0}
        for message_id in ids:
            if self.approve_message(message_id, approved_by=approved_by):
                stats["approved_updated"] += 1
        return stats

    def get_approved_messages(
        self,
        country: str | None = None,
        limit: int | None = None,
        template_type: str = "initial",
    ) -> list[dict]:
        query = """
            SELECT m.id AS message_id, m.subject, m.body, m.status, m.campaign_country,
                   m.template_type, m.attachment_path,
                   c.id AS contact_id, c.email, c.name, c.role, c.lead_score,
                   co.name AS company_name
            FROM messages m
            JOIN contacts c ON c.id = m.contact_id
            JOIN companies co ON co.id = c.company_id
            WHERE m.status = 'approved'
              AND m.template_type = ?
        """
        params: list[Any] = [template_type]
        if country:
            query += " AND lower(m.campaign_country) = lower(?)"
            params.append(country)
        query += " ORDER BY c.lead_score DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_messages_for_export(
        self,
        country: str,
        template_type: str = "initial",
        statuses: tuple[str, ...] = ("draft", "approved"),
        source_file: str | None = None,
        import_batch_id: int | None = None,
    ) -> list[dict]:
        from src.utils_paths import source_files_match

        placeholders = ",".join("?" * len(statuses))
        query = f"""
            SELECT m.id AS message_id, m.subject, m.body, m.status, m.approved_at,
                   m.source_file, m.import_batch_id,
                   COALESCE(c.full_name, c.name) AS name, c.role, c.email, c.lead_score,
                   c.country, c.contact_type, c.score_notes,
                   co.name AS company_name, c.source
            FROM messages m
            JOIN contacts c ON c.id = m.contact_id
            JOIN companies co ON co.id = c.company_id
            WHERE lower(m.campaign_country) = lower(?)
              AND m.template_type = ?
              AND m.status IN ({placeholders})
              AND m.status != 'archived_test_data'
              AND m.status != 'archived_superseded'
        """
        params: list[Any] = [country, template_type, *statuses]
        if import_batch_id is not None:
            query += " AND m.import_batch_id = ?"
            params.append(import_batch_id)
        query += " ORDER BY c.lead_score DESC, m.id DESC"
        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            result = [dict(r) for r in rows]
        if source_file and import_batch_id is None:
            result = [r for r in result if source_files_match(r.get("source_file"), source_file)]
        return result

    def insert_interaction(
        self, contact_id: int, interaction_type: str, message_id: int | None = None, notes: str = ""
    ):
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO interactions (contact_id, message_id, interaction_type, notes)
                VALUES (?, ?, ?, ?)
                """,
                (contact_id, message_id, interaction_type, notes),
            )

    def update_contact_status(self, email: str, status: str):
        with self.connect() as conn:
            conn.execute(
                "UPDATE contacts SET status = ?, updated_at = datetime('now') WHERE email = ?",
                (status, email.strip().lower()),
            )

    def update_company_enrichment(self, company_id: int, personalised_detail: str):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE companies
                SET personalised_detail = ?, enriched_at = ?
                WHERE id = ?
                """,
                (personalised_detail, _utc_now(), company_id),
            )

    def get_contact_by_email(self, email: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM contacts WHERE email = ?", (email.strip().lower(),)).fetchone()
            return dict(row) if row else None

    def get_message_by_id(self, message_id: int) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT m.*, c.email, c.name, c.id AS contact_id
                FROM messages m
                JOIN contacts c ON c.id = m.contact_id
                WHERE m.id = ?
                """,
                (message_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_contacts_for_country(self, country: str, statuses: list[str] | None = None) -> list[dict]:
        statuses = statuses or ["new", "drafted"]
        placeholders = ",".join("?" * len(statuses))
        query = f"""
            SELECT c.*, co.name AS company_name, co.website, co.industry,
                   co.why_interesting, co.personalised_detail, co.employee_count
            FROM contacts c
            JOIN companies co ON c.company_id = co.id
            WHERE lower(c.country) = lower(?)
              AND c.status IN ({placeholders})
            ORDER BY c.lead_score DESC, c.name
        """
        with self.connect() as conn:
            rows = conn.execute(query, [country, *statuses]).fetchall()
            return [dict(r) for r in rows]

    def get_followup_candidates(self, country: str, days_since_sent: int = 7) -> list[dict]:
        query = """
            SELECT c.*, co.name AS company_name, m.id AS message_id, m.sent_at
            FROM contacts c
            JOIN companies co ON c.company_id = co.id
            JOIN messages m ON m.contact_id = c.id
                AND m.template_type = 'initial'
                AND m.status = 'sent'
            WHERE lower(c.country) = lower(?)
              AND c.status = 'sent'
              AND m.sent_at IS NOT NULL
              AND datetime(m.sent_at) <= datetime('now', ?)
              AND NOT EXISTS (
                  SELECT 1 FROM messages fm
                  WHERE fm.contact_id = c.id AND fm.template_type = 'followup'
                    AND fm.status IN ('draft', 'approved', 'sent')
              )
            ORDER BY m.sent_at ASC
        """
        offset = f"-{days_since_sent} days"
        with self.connect() as conn:
            rows = conn.execute(query, (country, offset)).fetchall()
            return [dict(r) for r in rows]

    def count_sent_today(self) -> int:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) FROM messages
                WHERE status = 'sent'
                  AND date(sent_at) = date('now')
                """
            ).fetchone()
            return int(row[0])

    def mark_message_sent(self, message_id: int):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE messages
                SET status = 'sent', sent_at = ?, dry_run = 0, error_message = NULL
                WHERE id = ?
                """,
                (_utc_now(), message_id),
            )

    def mark_message_failed(self, message_id: int, error_message: str):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE messages
                SET status = 'failed', error_message = ?
                WHERE id = ?
                """,
                (error_message[:500], message_id),
            )

    def mark_message_send_unknown(self, message_id: int, error_message: str):
        """Temporary SMTP 4xx — delivery uncertain; do not auto-retry via send-approved."""
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE messages
                SET status = 'send_unknown', error_message = ?, dry_run = 0
                WHERE id = ?
                """,
                (error_message[:500], message_id),
            )

    def fetch_all_contacts(self) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.*, co.name AS company_name
                FROM contacts c
                LEFT JOIN companies co ON c.company_id = co.id
                ORDER BY c.lead_score DESC
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def stats(self) -> dict[str, int]:
        with self.connect() as conn:
            drafted = conn.execute("SELECT COUNT(*) FROM messages WHERE status = 'draft'").fetchone()[0]
            approved = conn.execute("SELECT COUNT(*) FROM messages WHERE status = 'approved'").fetchone()[0]
            sent = conn.execute("SELECT COUNT(*) FROM messages WHERE status = 'sent'").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM messages WHERE status = 'failed'").fetchone()[0]
            replied = conn.execute("SELECT COUNT(*) FROM contacts WHERE status = 'replied'").fetchone()[0]
            followups = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE template_type = 'followup' AND status = 'draft'"
            ).fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
            return {
                "total_contacts": int(total),
                "drafts": int(drafted),
                "approved": int(approved),
                "sent": int(sent),
                "failed": int(failed),
                "replied": int(replied),
                "followup_drafts": int(followups),
            }

    def find_company_id(self, name: str, domain: str | None, country: str | None) -> int | None:
        with self.connect() as conn:
            if domain:
                row = conn.execute(
                    "SELECT id FROM companies WHERE lower(domain) = lower(?)",
                    (domain.strip(),),
                ).fetchone()
                if row:
                    return int(row[0])
            row = conn.execute(
                "SELECT id FROM companies WHERE lower(name) = lower(?) AND lower(COALESCE(country,'')) = lower(COALESCE(?, ''))",
                (name.strip(), country or ""),
            ).fetchone()
            return int(row[0]) if row else None

    def import_apollo_company(self, data: dict[str, Any]) -> tuple[int, str]:
        existing_id = self.find_company_id(
            data["name"], data.get("domain"), data.get("country")
        )
        fields = {
            "name": data["name"],
            "domain": data.get("domain"),
            "website": data.get("website"),
            "country": data.get("country"),
            "city": data.get("city"),
            "industry": data.get("industry"),
            "employee_count": data.get("employee_count"),
            "linkedin_url": data.get("linkedin_url"),
            "source": data.get("source", "apollo"),
            "source_file": data.get("source_file"),
            "import_batch_id": data.get("import_batch_id"),
        }
        if existing_id:
            with self.connect() as conn:
                conn.execute(
                    """
                    UPDATE companies SET
                        domain=COALESCE(?, domain),
                        website=COALESCE(?, website),
                        country=COALESCE(?, country),
                        city=COALESCE(?, city),
                        industry=COALESCE(?, industry),
                        employee_count=COALESCE(?, employee_count),
                        linkedin_url=COALESCE(?, linkedin_url),
                        source=COALESCE(?, source),
                        source_file=COALESCE(?, source_file),
                        import_batch_id=COALESCE(?, import_batch_id)
                    WHERE id=?
                    """,
                    (
                        fields["domain"],
                        fields["website"],
                        fields["country"],
                        fields["city"],
                        fields["industry"],
                        fields["employee_count"],
                        fields["linkedin_url"],
                        fields["source"],
                        fields["source_file"],
                        fields["import_batch_id"],
                        existing_id,
                    ),
                )
            return existing_id, "updated"

        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO companies (
                    name, domain, website, country, city, industry,
                    employee_count, linkedin_url, source, source_file, import_batch_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fields["name"],
                    fields["domain"],
                    fields["website"],
                    fields["country"],
                    fields["city"],
                    fields["industry"],
                    fields["employee_count"],
                    fields["linkedin_url"],
                    fields["source"],
                    fields["source_file"],
                    fields["import_batch_id"],
                ),
            )
            return int(cur.lastrowid), "inserted"

    def find_contact_id(
        self, email: str | None, linkedin_url: str | None, full_name: str, company_id: int
    ) -> int | None:
        with self.connect() as conn:
            if email:
                row = conn.execute(
                    "SELECT id FROM contacts WHERE lower(email) = lower(?)",
                    (email.strip(),),
                ).fetchone()
                if row:
                    return int(row[0])
            if linkedin_url:
                row = conn.execute(
                    """
                    SELECT id FROM contacts
                    WHERE lower(COALESCE(linkedin_url, linkedin, '')) = lower(?)
                    """,
                    (linkedin_url.strip(),),
                ).fetchone()
                if row:
                    return int(row[0])
            row = conn.execute(
                """
                SELECT id FROM contacts
                WHERE lower(COALESCE(full_name, name, '')) = lower(?)
                  AND company_id = ?
                """,
                (full_name.strip(), company_id),
            ).fetchone()
            return int(row[0]) if row else None

    def import_apollo_contact(self, data: dict[str, Any], company_id: int) -> tuple[int, str]:
        full_name = data.get("full_name") or data.get("name") or "Unknown"
        email = (data.get("email") or "").strip().lower()
        existing_id = self.find_contact_id(
            email or None, data.get("linkedin_url"), full_name, company_id
        )

        payload = (
            company_id,
            data.get("first_name"),
            data.get("last_name"),
            full_name,
            full_name,
            data.get("role"),
            email or None,
            data.get("email_status"),
            data.get("catch_all_status"),
            data.get("linkedin_url"),
            data.get("linkedin_url"),
            data.get("country"),
            data.get("source", "apollo"),
            data.get("source_file"),
            data.get("import_batch_id"),
            data.get("usability_status"),
            data.get("seniority"),
            data.get("department"),
            data.get("contact_type"),
            data.get("score_notes"),
            int(data.get("email_valid_format", 0)),
            int(data.get("email_verified", 0)),
            data.get("lead_score", 0),
            data.get("status", "new"),
        )

        if existing_id:
            with self.connect() as conn:
                conn.execute(
                    """
                    UPDATE contacts SET
                        company_id=?,
                        first_name=COALESCE(?, first_name),
                        last_name=COALESCE(?, last_name),
                        full_name=COALESCE(?, full_name),
                        name=COALESCE(?, name),
                        role=COALESCE(?, role),
                        email=COALESCE(?, email),
                        email_status=COALESCE(?, email_status),
                        catch_all_status=COALESCE(?, catch_all_status),
                        linkedin_url=COALESCE(?, linkedin_url),
                        linkedin=COALESCE(?, linkedin),
                        country=COALESCE(?, country),
                        source=COALESCE(?, source),
                        source_file=COALESCE(?, source_file),
                        import_batch_id=COALESCE(?, import_batch_id),
                        usability_status=COALESCE(?, usability_status),
                        seniority=COALESCE(?, seniority),
                        department=COALESCE(?, department),
                        contact_type=COALESCE(?, contact_type),
                        score_notes=COALESCE(?, score_notes),
                        email_valid_format=?,
                        email_verified=?,
                        lead_score=?,
                        status=COALESCE(?, status),
                        updated_at=datetime('now')
                    WHERE id=?
                    """,
                    (*payload, existing_id),
                )
            return existing_id, "updated"

        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO contacts (
                    company_id, first_name, last_name, full_name, name, role, email,
                    email_status, catch_all_status, linkedin_url, linkedin, country, source,
                    source_file, import_batch_id, usability_status, seniority, department,
                    contact_type, score_notes,
                    email_valid_format, email_verified, lead_score, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            return int(cur.lastrowid), "inserted"

    def get_contacts_for_drafts(
        self,
        country: str,
        *,
        source: str | None = None,
        source_file: str | None = None,
        import_batch_id: int | None = None,
        min_score: float = 50.0,
        include_risky: bool = False,
        statuses: list[str] | None = None,
    ) -> list[dict]:
        from src.utils_paths import file_basename, source_files_match

        statuses = statuses or ["new", "drafted"]
        usability = ["usable"]
        if include_risky:
            usability.append("risky")
        status_ph = ",".join("?" * len(statuses))
        use_ph = ",".join("?" * len(usability))

        query = f"""
            SELECT c.*, co.name AS company_name, co.website, co.industry, co.domain,
                   co.why_interesting, co.personalised_detail, co.employee_count,
                   co.country AS company_country
            FROM contacts c
            JOIN companies co ON c.company_id = co.id
            WHERE (
                lower(COALESCE(co.country, '')) = lower(?)
                OR (
                    COALESCE(co.country, '') = ''
                    AND lower(COALESCE(c.country, '')) = lower(?)
                )
            )
              AND c.status IN ({status_ph})
              AND c.usability_status IN ({use_ph})
              AND c.lead_score >= ?
              AND c.email IS NOT NULL AND c.email != ''
              AND COALESCE(c.email, '') NOT LIKE '%.example'
        """
        params: list[Any] = [country, country, *statuses, *usability, min_score]
        if source:
            query += " AND lower(c.source) = lower(?)"
            params.append(source)
        if import_batch_id is not None:
            query += " AND c.import_batch_id = ?"
            params.append(import_batch_id)
        elif source_file:
            query += " AND (c.source_file = ? OR c.source_file LIKE ?)"
            sf = str(source_file)
            params.extend([sf, f"%{file_basename(sf)}"])
        query += " ORDER BY c.lead_score DESC, c.full_name"

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
            result = [dict(r) for r in rows]
        if source_file and import_batch_id is None:
            result = [
                r
                for r in result
                if source_files_match(r.get("source_file"), source_file)
                and "example_apollo" not in file_basename(r.get("source_file") or "")
            ]
        return result

    def archive_draft_messages_for_contact(
        self,
        contact_id: int,
        campaign_country: str,
        template_type: str = "initial",
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE messages
                SET status = 'archived_superseded'
                WHERE contact_id = ?
                  AND lower(campaign_country) = lower(?)
                  AND template_type = ?
                  AND status = 'draft'
                """,
                (contact_id, campaign_country, template_type),
            )
            return cur.rowcount

    def archive_test_messages(self, message_ids: list[int]) -> int:
        if not message_ids:
            return 0
        placeholders = ",".join("?" * len(message_ids))
        with self.connect() as conn:
            cur = conn.execute(
                f"""
                UPDATE messages SET status = 'archived_test_data'
                WHERE id IN ({placeholders})
                """,
                message_ids,
            )
            return cur.rowcount

    def delete_test_contacts(self, contact_ids: list[int]) -> int:
        if not contact_ids:
            return 0
        placeholders = ",".join("?" * len(contact_ids))
        with self.connect() as conn:
            cur = conn.execute(
                f"DELETE FROM contacts WHERE id IN ({placeholders})",
                contact_ids,
            )
            return cur.rowcount

