import pandas as pd
import os
from dotenv import load_dotenv

from src.cleanup_test_data import run_cleanup
from src.draft_audit import audit_draft_rows
from src.config import settings
from src.countries import normalize_country, template_country
from src.db.repository import Repository
from src.db.schema import init_db
from src.enrich_company import generate_personalised_detail
from src.apollo_importer import run_apollo_import
from src.generate_email import generate_email, generate_subject
from src.import_apollo import import_manual_csv
from src.init_env import cmd_init_env
from src.scoring import score_all_contacts
from src.sending import SendSafetyError, process_approved_batch
from src.validate_contacts import validate_contact_row

def _runtime_auto_send_enabled() -> tuple[bool, str | None, str | None]:
    env_path = settings.path(".env")
    found = load_dotenv(env_path, override=True)
    raw = os.getenv("AUTO_SEND_ENABLED")
    enabled = str(raw).strip().lower() in {"1", "true", "yes", "on"}
    return enabled, str(env_path) if found else None, raw


def _validate_unvalidated(repo: Repository) -> None:
    for contact in repo.fetch_all_contacts():
        if contact.get("email_valid_format"):
            continue
        result = validate_contact_row(contact, use_hunter=bool(settings.hunter_api_key))
        status = contact.get("status") or "new"
        if not result["is_valid"]:
            status = "invalid"
        with repo.connect() as conn:
            conn.execute(
                """
                UPDATE contacts
                SET email_valid_format = ?, email_verified = ?, hunter_score = COALESCE(?, hunter_score),
                    status = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    result["email_valid_format"],
                    result["email_verified"],
                    result["hunter_score"],
                    status,
                    contact["id"],
                ),
            )


def _repo() -> Repository:
    init_db(settings.db_path)
    return Repository(settings.db_path)


def _export_drafts_csv(
    repo: Repository,
    country: str,
    out_file,
    *,
    source_file: str | None = None,
    import_batch_id: int | None = None,
) -> int:
    messages = repo.get_messages_for_export(
        country,
        template_type="initial",
        source_file=source_file,
        import_batch_id=import_batch_id,
    )
    rows = []
    for msg in messages:
        approved = "yes" if msg.get("status") == "approved" else "no"
        notes_parts = [
            f"Source: {msg.get('source', '')}",
            f"import_batch_id={msg.get('import_batch_id') or ''}",
            f"source_file={msg.get('source_file') or ''}",
            f"contact_type={msg.get('contact_type') or ''}",
            f"score_notes={msg.get('score_notes') or ''}",
        ]
        rows.append(
            {
                "message_id": msg["message_id"],
                "lead_score": msg.get("lead_score", 0),
                "contact_type": msg.get("contact_type"),
                "score_notes": msg.get("score_notes"),
                "import_batch_id": msg.get("import_batch_id"),
                "source_file": msg.get("source_file"),
                "company": msg["company_name"],
                "name": msg["name"],
                "first_name": msg.get("name", "").split()[0] if msg.get("name") else "",
                "role": msg.get("role"),
                "email": msg["email"],
                "country": country,
                "subject": msg.get("subject"),
                "email_body": msg.get("body"),
                "approved": approved,
                "status": msg.get("status", "draft"),
                "notes": " | ".join(n for n in notes_parts if n.split("=", 1)[-1]),
            }
        )
    audit_draft_rows(rows, fail=True)
    settings.data_output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        out_file,
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    return len(rows)

def cmd_import_apollo(file: str | None, country: str) -> None:
    repo = _repo()
    if not file:
        raise SystemExit("--file is required (e.g. data/leads/uk_batch_1.csv)")
    path = settings.path(file)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    campaign_country = normalize_country(country)
    if not campaign_country:
        raise SystemExit("--country is required: uk or spain")

    stats = run_apollo_import(repo, path, campaign_country)
    print(f"\nApollo import complete: {path}")
    print(f"  Total rows:           {stats['total_rows']}")
    print(f"  Usable contacts:      {stats['usable']}")
    print(f"  Risky contacts:       {stats['risky']}")
    print(f"  Missing/unavailable:  {stats['needs_email']}")
    print(f"  Companies imported:   {stats['companies_imported']}")
    print(f"  Contacts inserted:    {stats['contacts_inserted']}")
    print(f"  Contacts updated:     {stats['contacts_updated']}")
    print(f"  Companies inserted:   {stats['companies_inserted']}")
    print(f"  Companies updated:    {stats['companies_updated']}")
    if stats.get("import_batch_id"):
        print(f"  Import batch id:      {stats['import_batch_id']}")
    if stats.get("source_file"):
        print(f"  Source file:          {stats['source_file']}")
    if stats.get("skipped_country"):        print(f"  Skipped (country):    {stats['skipped_country']}")
    print("  Files created:")
    for f in stats["files_created"]:
        print(f"    - {f}")


def cmd_import_manual() -> None:
    repo = _repo()
    stats = import_manual_csv(
        repo,
        str(settings.data_input_dir / "companies.csv"),
        str(settings.data_input_dir / "contacts.csv"),
    )
    print(f"Manual CSV import: {stats}")


def cmd_validate_contacts(use_hunter: bool = True) -> None:
    repo = _repo()
    contacts = repo.fetch_all_contacts()
    valid_count = 0
    for contact in contacts:
        result = validate_contact_row(contact, use_hunter=use_hunter)
        if result["is_valid"]:
            valid_count += 1
            status = contact.get("status") or "new"
        else:
            status = "invalid"
        with repo.connect() as conn:
            conn.execute(
                """
                UPDATE contacts
                SET email_valid_format = ?, email_verified = ?, hunter_score = COALESCE(?, hunter_score),
                    status = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    result["email_valid_format"],
                    result["email_verified"],
                    result["hunter_score"],
                    status,
                    contact["id"],
                ),
            )
    print(f"Validated {len(contacts)} contacts. Valid for outreach: {valid_count}")


def cmd_score_leads() -> None:
    repo = _repo()
    contacts = repo.fetch_all_contacts()
    score_all_contacts(repo, contacts)
    print(f"Scored {len(contacts)} contacts.")


def cmd_cleanup_test_data(apply: bool = False) -> None:
    repo = _repo()
    run_cleanup(repo, apply=apply)


def cmd_generate_drafts(
    country: str,
    campaign_name: str | None = None,
    enrich: bool = True,
    force: bool = False,
    source: str | None = None,
    source_file: str | None = None,
    batch_id: int | None = None,
    min_score: float = 50.0,
    include_risky: bool = False,
) -> None:
    repo = _repo()
    country = normalize_country(country)
    if not country:
        raise SystemExit("Country required: uk or spain")

    campaign_name = campaign_name or (
        settings.default_campaign_uk if country == "uk" else settings.default_campaign_spain
    )
    campaign_id = repo.get_or_create_campaign(campaign_name, country)

    if source == "apollo":
        contacts = repo.get_contacts_for_drafts(
            country,
            source="apollo",
            source_file=source_file,
            import_batch_id=batch_id,
            min_score=min_score,
            include_risky=include_risky,
            statuses=["new", "drafted"],
        )
    else:
        _validate_unvalidated(repo)
        contacts = repo.get_contacts_for_country(country, statuses=["new", "drafted"])
        contacts = [
            c
            for c in contacts
            if (c.get("email_valid_format") or c.get("email_verified"))
            and c.get("status") != "invalid"
            and c.get("usability_status") in (None, "usable", *(["risky"] if include_risky else []))
            and (c.get("lead_score") or 0) >= min_score
        ]
        if source:
            contacts = [c for c in contacts if str(c.get("source", "")).lower() == source.lower()]

    if not contacts:
        print(f"No eligible contacts for {country}. Run import-apollo first or lower --min-score.")
        return

    if source != "apollo":
        score_all_contacts(repo, contacts)

    created = 0
    skipped = 0
    tpl_country = template_country(country)
    template_type = "initial"

    for contact in contacts:
        if not force and repo.message_exists_for_contact_campaign(
            contact["email"], country, template_type
        ):
            skipped += 1
            continue

        if force:
            repo.archive_draft_messages_for_contact(contact["id"], country, template_type)

        company = {
            "company": contact["company_name"],
            "website": contact.get("website", ""),
            "why_interesting": contact.get("why_interesting", ""),
            "industry": contact.get("industry", ""),
        }

        detail = contact.get("personalised_detail")
        if enrich and not detail:
            detail = generate_personalised_detail(
                contact["company_name"],
                contact.get("website", "") or "",
                contact.get("why_interesting", "") or "",
                contact.get("industry", "") or "",
            )
            if contact.get("company_id"):
                repo.update_company_enrichment(contact["company_id"], detail)

        subject = generate_subject(contact, country)
        body = generate_email(contact, company, detail or "", tpl_country)

        message_id = repo.insert_message(
            {
                "contact_id": contact["id"],
                "campaign_id": campaign_id,
                "subject": subject,
                "body": body,
                "message_type": "initial",
                "template_type": template_type,
                "campaign_country": country,
                "status": "draft",
                "dry_run": 1,
                "attachment_path": str(settings.cv_file),
                "source_file": contact.get("source_file"),
                "import_batch_id": contact.get("import_batch_id"),
            }
        )
        repo.update_contact_status(contact["email"], "drafted")
        repo.insert_interaction(contact["id"], "draft_created", message_id, "generate-drafts")
        created += 1

    out_file = settings.data_output_dir / f"outreach_drafts_{country}.csv"
    total = _export_drafts_csv(
        repo,
        country,
        out_file,
        source_file=source_file,
        import_batch_id=batch_id,
    )
    print(f"Created {created} new draft(s), skipped {skipped} duplicate(s).")
    print(f"Exported {total} draft(s) to {out_file}")
    print('Review CSV manually. Set approved=yes, then run: python -m src.cli approve-drafts --csv ...')


def cmd_approve_drafts(
    csv_path: str | None = None,
    message_id: int | None = None,
    email: str | None = None,
) -> None:
    repo = _repo()
    approved = 0

    if csv_path:
        stats = repo.approve_messages_from_csv(settings.path(csv_path))
        print(
            f"CSV approval: {stats['approved_updated']} updated "
            f"({stats['approved_requested']} requested from {stats['rows_in_csv']} rows)"
        )
        return

    if message_id:
        if repo.approve_message(message_id):
            approved += 1
        else:
            print(f"Could not approve message_id={message_id} (not found or not in draft/approved state)")
        print(f"Approved {approved} message(s).")
        return

    if email:
        contact = repo.get_contact_by_email(email)
        if not contact:
            raise SystemExit(f"Contact not found: {email}")
        with repo.connect() as conn:
            row = conn.execute(
                """
                SELECT id FROM messages
                WHERE contact_id = ?
                  AND template_type = 'initial'
                  AND status IN ('draft', 'approved')
                ORDER BY id DESC LIMIT 1
                """,
                (contact["id"],),
            ).fetchone()
        if row and repo.approve_message(int(row["id"])):
            approved += 1
        print(f"Approved {approved} message(s) for {email}.")
        return

    raise SystemExit("Provide --csv, --message-id, or --email")


def cmd_send_approved(
    country: str,
    dry_run: bool = True,
    limit: int | None = None,
    debug_env: bool = False,
) -> None:
    repo = _repo()
    country = normalize_country(country)
    if not country:
        raise SystemExit("Country required: uk or spain")

    limit = limit or settings.daily_send_limit
    messages = repo.get_approved_messages(country=country, limit=limit, template_type="initial")

    if not messages:
        print(f"No approved messages for {country}. Approve drafts first.")
        return

    runtime_enabled, env_path, env_raw = _runtime_auto_send_enabled()
    if debug_env:
        print("[debug-env] send-approved configuration")
        print(f"[debug-env] cwd={os.getcwd()}")
        print(f"[debug-env] env_path_loaded={env_path or 'not_found'}")
        print(f"[debug-env] AUTO_SEND_ENABLED raw={env_raw!r}")
        print(f"[debug-env] bool_runtime_enabled={runtime_enabled}")
        print(f"[debug-env] bool_settings_auto_send_enabled={settings.auto_send_enabled}")
        print(f"[debug-env] dry_run={dry_run}")
        print(f"[debug-env] limit={limit}")
        print(f"[debug-env] country={country}")

    if not dry_run:
        if not runtime_enabled:
            raise SendSafetyError("AUTO_SEND_ENABLED is false. Set to true in .env for live sending.")
        answer = input(f"About to send {len(messages)} email(s). Continue? y/N: ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return

    results = process_approved_batch(messages, dry_run=dry_run, repo=repo)

    report_name = "send_report_dry_run.csv" if dry_run else "send_report.csv"
    report_path = settings.data_output_dir / report_name
    settings.data_output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(report_path, index=False)

    sent = sum(1 for r in results if r.get("result") == "sent")
    dry = sum(1 for r in results if r.get("result") == "dry_run")
    skipped = sum(1 for r in results if r.get("result") == "skipped")
    failed = sum(1 for r in results if r.get("result") == "failed")
    uncertain = sum(1 for r in results if r.get("result") == "uncertain")

    mode = "DRY-RUN (read-only, no DB changes)" if dry_run else "LIVE"
    print(f"{mode}: processed {len(results)} message(s).")
    print(f"  sent={sent}, dry_run={dry}, skipped={skipped}, failed={failed}, uncertain={uncertain}")
    if uncertain and not dry_run:
        from src.smtp_errors import UNCERTAIN_CONSOLE_MESSAGE

        print(UNCERTAIN_CONSOLE_MESSAGE)
    print(f"Report written to {report_path}")


def cmd_export_followups(country: str, days: int = 7, force: bool = False) -> None:
    repo = _repo()
    country = normalize_country(country)
    campaign_id = repo.get_or_create_campaign(
        settings.default_campaign_uk if country == "uk" else settings.default_campaign_spain,
        country,
    )
    candidates = repo.get_followup_candidates(country, days_since_sent=days)

    if not candidates:
        print(f"No follow-up candidates for {country} (sent {days}+ days ago).")
        return

    created = 0
    skipped = 0
    tpl_country = template_country(country)
    template_type = "followup"

    for contact in candidates:
        if not force and repo.message_exists_for_contact_campaign(
            contact["email"], country, template_type
        ):
            skipped += 1
            continue

        company = {"company": contact["company_name"]}
        body = generate_email(contact, company, "", tpl_country, followup=True)
        subject = f"Re: {generate_subject(contact, country)}"
        repo.insert_message(
            {
                "contact_id": contact["id"],
                "campaign_id": campaign_id,
                "subject": subject,
                "body": body,
                "message_type": "followup",
                "template_type": template_type,
                "campaign_country": country,
                "status": "draft",
                "dry_run": 1,
            }
        )
        created += 1

    messages = repo.get_messages_for_export(country, template_type="followup", statuses=("draft", "approved"))
    rows = [
        {
            "message_id": m["message_id"],
            "company": m["company_name"],
            "name": m["name"],
            "email": m["email"],
            "country": country,
            "subject": m.get("subject"),
            "email_body": m.get("body"),
            "approved": "yes" if m.get("status") == "approved" else "no",
            "status": m.get("status", "draft"),
            "notes": "Follow-up draft — export only, not auto-sent",
        }
        for m in messages
    ]

    out_file = settings.data_output_dir / f"followups_{country}.csv"
    pd.DataFrame(rows).to_csv(out_file, index=False)
    print(f"Created {created} follow-up draft(s), skipped {skipped} duplicate(s).")
    print(f"Exported {len(rows)} follow-up draft(s) -> {out_file} (CSV only, not auto-sent)")


def cmd_mark_sent(
    email: str | None = None,
    message_id: int | None = None,
    sent_date: str | None = None,
) -> None:
    repo = _repo()

    if message_id is not None:
        msg = repo.get_message_by_id(message_id)
        if not msg:
            raise SystemExit(f"Message not found: message_id={message_id}")
        email = msg["email"]
        repo.mark_message_sent(message_id)
        if sent_date:
            with repo.connect() as conn:
                conn.execute(
                    "UPDATE messages SET sent_at = ? WHERE id = ?",
                    (sent_date, message_id),
                )
        repo.update_contact_status(email, "sent")
        repo.insert_interaction(
            msg["contact_id"],
            "sent",
            message_id,
            "marked manually via CLI (verified in Gmail Sent)",
        )
        print(f"Marked message_id={message_id} ({email}) as sent.")
        return

    if not email:
        raise SystemExit("Provide --email or --message-id")

    contact = repo.get_contact_by_email(email)
    if not contact:
        raise SystemExit(f"Contact not found: {email}")

    with repo.connect() as conn:
        row = conn.execute(
            """
            SELECT id FROM messages
            WHERE contact_id = ? AND template_type = 'initial'
            ORDER BY id DESC LIMIT 1
            """,
            (contact["id"],),
        ).fetchone()
        if row:
            conn.execute(
                """
                UPDATE messages SET status = 'sent', sent_at = COALESCE(?, datetime('now')),
                    error_message = NULL
                WHERE id = ?
                """,
                (sent_date, row["id"]),
            )
    repo.update_contact_status(email, "sent")
    repo.insert_interaction(contact["id"], "sent", notes="marked manually via CLI")
    print(f"Marked {email} as sent.")


def cmd_mark_replied(email: str, notes: str = "") -> None:
    repo = _repo()
    contact = repo.get_contact_by_email(email)
    if not contact:
        raise SystemExit(f"Contact not found: {email}")

    repo.update_contact_status(email, "replied")
    repo.insert_interaction(contact["id"], "replied", notes=notes or "marked via CLI")
    print(f"Marked {email} as replied.")
