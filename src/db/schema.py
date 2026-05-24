import sqlite3
from pathlib import Path

from src.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    country TEXT NOT NULL,
    imported_at TEXT DEFAULT (datetime('now')),
    total_rows INTEGER DEFAULT 0,
    usable_count INTEGER DEFAULT 0,
    risky_count INTEGER DEFAULT 0,
    missing_count INTEGER DEFAULT 0,
    contacts_inserted INTEGER DEFAULT 0,
    contacts_updated INTEGER DEFAULT 0,
    companies_inserted INTEGER DEFAULT 0,
    companies_updated INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    domain TEXT,
    website TEXT,
    country TEXT,
    city TEXT,
    industry TEXT,
    employee_count INTEGER,
    linkedin_url TEXT,
    source TEXT,
    source_file TEXT,
    import_batch_id INTEGER REFERENCES import_batches(id),
    why_interesting TEXT,
    personalised_detail TEXT,
    enriched_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER REFERENCES companies(id),
    first_name TEXT,
    last_name TEXT,
    full_name TEXT,
    name TEXT,
    role TEXT,
    email TEXT UNIQUE,
    email_status TEXT,
    catch_all_status TEXT,
    linkedin_url TEXT,
    linkedin TEXT,
    country TEXT,
    source TEXT,
    source_file TEXT,
    import_batch_id INTEGER REFERENCES import_batches(id),
    usability_status TEXT,
    seniority TEXT,
    department TEXT,
    contact_type TEXT,
    score_notes TEXT,
    email_valid_format INTEGER DEFAULT 0,
    email_verified INTEGER DEFAULT 0,
    hunter_score INTEGER,
    lead_score REAL DEFAULT 0,
    status TEXT DEFAULT 'new',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    description TEXT,
    daily_limit INTEGER DEFAULT 10,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    campaign_id INTEGER REFERENCES campaigns(id),
    subject TEXT,
    body TEXT,
    message_type TEXT DEFAULT 'initial',
    template_type TEXT DEFAULT 'initial',
    campaign_country TEXT,
    status TEXT DEFAULT 'draft',
    dry_run INTEGER DEFAULT 1,
    approved_at TEXT,
    approved_by TEXT,
    attachment_path TEXT,
    error_message TEXT,
    source_file TEXT,
    import_batch_id INTEGER REFERENCES import_batches(id),
    sent_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL REFERENCES contacts(id),
    message_id INTEGER REFERENCES messages(id),
    interaction_type TEXT NOT NULL,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(status);
CREATE INDEX IF NOT EXISTS idx_contacts_country ON contacts(country);
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
CREATE INDEX IF NOT EXISTS idx_messages_contact ON messages(contact_id);
CREATE INDEX IF NOT EXISTS idx_import_batches_source ON import_batches(source_file);
"""

INDEXES_AFTER_MIGRATION = """
CREATE INDEX IF NOT EXISTS idx_contacts_usability ON contacts(usability_status);
CREATE INDEX IF NOT EXISTS idx_contacts_batch ON contacts(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_contacts_source_file ON contacts(source_file);
CREATE INDEX IF NOT EXISTS idx_messages_campaign_country ON messages(campaign_country);
CREATE INDEX IF NOT EXISTS idx_messages_batch ON messages(import_batch_id);
CREATE INDEX IF NOT EXISTS idx_companies_batch ON companies(import_batch_id);
"""

MESSAGE_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
    ("template_type", "TEXT DEFAULT 'initial'"),
    ("campaign_country", "TEXT"),
    ("approved_at", "TEXT"),
    ("approved_by", "TEXT"),
    ("attachment_path", "TEXT"),
    ("error_message", "TEXT"),
    ("source_file", "TEXT"),
    ("import_batch_id", "INTEGER"),
]

COMPANY_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
    ("domain", "TEXT"),
    ("linkedin_url", "TEXT"),
    ("source", "TEXT"),
    ("source_file", "TEXT"),
    ("import_batch_id", "INTEGER"),
]

CONTACT_COLUMN_MIGRATIONS: list[tuple[str, str]] = [
    ("first_name", "TEXT"),
    ("last_name", "TEXT"),
    ("full_name", "TEXT"),
    ("email_status", "TEXT"),
    ("catch_all_status", "TEXT"),
    ("usability_status", "TEXT"),
    ("seniority", "TEXT"),
    ("department", "TEXT"),
    ("linkedin_url", "TEXT"),
    ("source_file", "TEXT"),
    ("import_batch_id", "INTEGER"),
    ("contact_type", "TEXT"),
    ("score_notes", "TEXT"),
]


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _migrate_table(conn: sqlite3.Connection, table: str, migrations: list[tuple[str, str]]) -> None:
    existing = _existing_columns(conn, table)
    for column, col_type in migrations:
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def _migrate_messages_table(conn: sqlite3.Connection) -> None:
    _migrate_table(conn, "messages", MESSAGE_COLUMN_MIGRATIONS)
    conn.execute(
        """
        UPDATE messages
        SET template_type = COALESCE(template_type, message_type, 'initial'),
            campaign_country = COALESCE(
                campaign_country,
                (SELECT cam.country FROM campaigns cam WHERE cam.id = messages.campaign_id),
                (SELECT co.country FROM companies co
                 JOIN contacts c ON c.company_id = co.id WHERE c.id = messages.contact_id)
            )
        WHERE template_type IS NULL OR campaign_country IS NULL
        """
    )


def _migrate_companies_table(conn: sqlite3.Connection) -> None:
    _migrate_table(conn, "companies", COMPANY_COLUMN_MIGRATIONS)


def _migrate_contacts_table(conn: sqlite3.Connection) -> None:
    _migrate_table(conn, "contacts", CONTACT_COLUMN_MIGRATIONS)
    conn.execute(
        """
        UPDATE contacts
        SET full_name = COALESCE(full_name, name),
            linkedin_url = COALESCE(linkedin_url, linkedin)
        WHERE full_name IS NULL OR linkedin_url IS NULL
        """
    )


def init_db(db_path: Path | None = None) -> Path:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    _migrate_companies_table(conn)
    _migrate_contacts_table(conn)
    _migrate_messages_table(conn)
    conn.executescript(INDEXES_AFTER_MIGRATION)
    conn.commit()
    conn.close()
    return path
