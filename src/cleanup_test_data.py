"""Identify and archive/remove test/example outreach data."""

from __future__ import annotations

from typing import Any

from src.db.backup import backup_database
from src.db.repository import Repository
from src.utils_paths import file_basename, source_files_match

TEST_SOURCE_BASENAME = "example_apollo_export.csv"
REAL_SOURCE_BASENAME = "apollo-contacts-export.csv"

TEST_COMPANY_HINTS = (
    "northbridge",
    "startupforge",
    "harbor logistics",
    "retail hub",
    "greenfield insurance",
)

TEST_NAMES = {
    "alex turner",
    "elena vega",
    "sam reed",
    "chris sales",
    "jordan lee",
}


def _norm_name(value: str | None) -> str:
    return (value or "").strip().lower()


def is_test_email(email: str | None) -> bool:
    return bool(email and str(email).strip().lower().endswith(".example"))


def is_test_source_file(source_file: str | None) -> bool:
    return file_basename(source_file) == TEST_SOURCE_BASENAME


def is_real_apollo_source(source_file: str | None) -> bool:
    return file_basename(source_file) == REAL_SOURCE_BASENAME


def company_name_is_test(name: str | None) -> bool:
    lower = (name or "").lower()
    return any(hint in lower for hint in TEST_COMPANY_HINTS)


def contact_name_is_test(name: str | None) -> bool:
    return _norm_name(name) in TEST_NAMES


def is_test_contact(contact: dict[str, Any]) -> bool:
    email = contact.get("email") or ""
    source = contact.get("source_file")
    name = contact.get("full_name") or contact.get("name")
    company = contact.get("company_name") or contact.get("company") or ""

    if is_real_apollo_source(source) and not is_test_email(email):
        return False

    if is_test_source_file(source):
        return True
    if is_test_email(email):
        return True
    if contact_name_is_test(name) and (is_test_source_file(source) or is_test_email(email)):
        return True
    if company_name_is_test(company) and (is_test_source_file(source) or is_test_email(email)):
        return True
    return False


def is_test_message(msg: dict[str, Any]) -> bool:
    if msg.get("status") == "archived_test_data":
        return False
    email = msg.get("email") or ""
    source = msg.get("source_file") or msg.get("contact_source_file")
    name = msg.get("name") or msg.get("full_name")
    company = msg.get("company_name") or ""

    if is_test_email(email):
        return True
    if is_test_source_file(source):
        return True
    if contact_name_is_test(name) and (is_test_source_file(source) or is_test_email(email)):
        return True
    if company_name_is_test(company):
        return True
    return False


def scan_test_data(repo: Repository) -> dict[str, Any]:
    with repo.connect() as conn:
        messages = [
            dict(r)
            for r in conn.execute(
                """
                SELECT m.id, m.status, m.source_file, m.subject,
                       COALESCE(c.full_name, c.name) AS name,
                       c.email, c.source_file AS contact_source_file,
                       co.name AS company_name
                FROM messages m
                JOIN contacts c ON c.id = m.contact_id
                JOIN companies co ON co.id = c.company_id
                WHERE m.status != 'archived_test_data'
                """
            ).fetchall()
        ]
        contacts = [
            dict(r)
            for r in conn.execute(
                """
                SELECT c.id, c.email, c.full_name, c.name, c.source_file,
                       co.name AS company_name
                FROM contacts c
                LEFT JOIN companies co ON co.id = c.company_id
                """
            ).fetchall()
        ]

    test_messages = [m for m in messages if is_test_message(m)]
    test_contacts = [c for c in contacts if is_test_contact(c)]

    # Only delete contacts we're sure about
    deletable_contacts = [
        c
        for c in test_contacts
        if is_test_source_file(c.get("source_file")) or is_test_email(c.get("email"))
    ]

    return {
        "messages_to_archive": test_messages,
        "contacts_to_delete": deletable_contacts,
        "contacts_flagged": [c for c in test_contacts if c not in deletable_contacts],
    }


def print_scan_report(scan: dict[str, Any], *, dry_run: bool) -> None:
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"\n=== cleanup-test-data ({mode}) ===")
    print(f"Messages to archive: {len(scan['messages_to_archive'])}")
    for m in scan["messages_to_archive"]:
        print(
            f"  msg id={m['id']} | {m.get('email')} | {m.get('company_name')} | "
            f"source={m.get('source_file') or m.get('contact_source_file')}"
        )
    print(f"Contacts to delete: {len(scan['contacts_to_delete'])}")
    for c in scan["contacts_to_delete"]:
        print(
            f"  contact id={c['id']} | {c.get('email')} | {c.get('company_name')} | "
            f"source={c.get('source_file')}"
        )
    flagged = scan.get("contacts_flagged") or []
    if flagged:
        print(f"Contacts flagged (not auto-deleted): {len(flagged)}")
        for c in flagged:
            print(f"  contact id={c['id']} | {c.get('email')} | {c.get('company_name')}")


def run_cleanup(repo: Repository, *, apply: bool = False) -> dict[str, Any]:
    scan = scan_test_data(repo)
    print_scan_report(scan, dry_run=not apply)

    if not apply:
        return {"dry_run": True, **scan, "backup_path": None}

    backup_path = backup_database(repo.db_path)
    print(f"\nDatabase backup: {backup_path}")

    message_ids = [int(m["id"]) for m in scan["messages_to_archive"]]
    contact_ids = [int(c["id"]) for c in scan["contacts_to_delete"]]

    archived = repo.archive_test_messages(message_ids)
    deleted = repo.delete_test_contacts(contact_ids)

    print(f"\nArchived {archived} message(s). Deleted {deleted} test contact(s).")
    return {
        "dry_run": False,
        "backup_path": str(backup_path),
        "archived": archived,
        "deleted": deleted,
        **scan,
    }
