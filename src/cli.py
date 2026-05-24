import argparse

from src.commands import (
    cmd_approve_drafts,
    cmd_cleanup_test_data,
    cmd_export_followups,
    cmd_generate_drafts,
    cmd_import_apollo,
    cmd_import_manual,
    cmd_init_env,
    cmd_mark_replied,
    cmd_mark_sent,
    cmd_score_leads,
    cmd_send_approved,
    cmd_validate_contacts,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Job outreach assistant — organise leads, draft emails, track follow-ups.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-env", help="Create .env, folders, and show setup steps")

    p_import = sub.add_parser("import-apollo", help="Import and clean a raw Apollo CSV export")
    p_import.add_argument("--file", required=True, help="Path to Apollo CSV (e.g. data/leads/uk_batch_1.csv)")
    p_import.add_argument("--country", required=True, help="Campaign country: uk or spain")

    sub.add_parser("import-manual", help="Import data/input/companies.csv and contacts.csv")

    p_cleanup = sub.add_parser(
        "cleanup-test-data",
        help="Archive/remove test/example data (dry-run by default)",
    )
    p_cleanup.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview cleanup without modifying DB (default when --apply is omitted)",
    )
    p_cleanup.add_argument(
        "--apply",
        action="store_true",
        help="Apply cleanup after DB backup (default: dry-run only)",
    )

    p_val = sub.add_parser("validate-contacts", help="Validate email format and optional Hunter API")
    p_val.add_argument("--no-hunter", action="store_true", help="Skip Hunter verification")

    sub.add_parser("score-leads", help="Calculate lead scores for all contacts")

    p_gen = sub.add_parser("generate-drafts", help="Generate outreach email drafts")
    p_gen.add_argument("--country", required=True, help="uk or spain")
    p_gen.add_argument("--campaign", default=None, help="Campaign name")
    p_gen.add_argument("--source", default=None, help="Filter by source, e.g. apollo")
    p_gen.add_argument(
        "--source-file",
        default=None,
        help="Only contacts from this import file (basename match supported)",
    )
    p_gen.add_argument(
        "--batch-id",
        type=int,
        default=None,
        help="Only contacts from this import batch (overrides --source-file)",
    )
    p_gen.add_argument("--min-score", type=float, default=50.0, help="Minimum lead score (default: 50)")
    p_gen.add_argument("--include-risky", action="store_true", help="Include risky email contacts")
    p_gen.add_argument("--no-enrich", action="store_true", help="Skip website enrichment")
    p_gen.add_argument("--force", action="store_true", help="Create new drafts even if one already exists")

    p_approve = sub.add_parser("approve-drafts", help="Approve drafts for sending")
    p_approve.add_argument("--csv", default=None, help="CSV with approved=yes rows")
    p_approve.add_argument("--message-id", type=int, default=None)
    p_approve.add_argument("--email", default=None)

    p_send = sub.add_parser("send-approved", help="Send approved emails (dry-run by default)")
    p_send.add_argument("--country", required=True, help="uk or spain")
    p_send.add_argument("--dry-run", action="store_true", help="Preview without sending or DB updates")
    p_send.add_argument("--live", action="store_true", help="Live send via SMTP (requires AUTO_SEND_ENABLED=true)")
    p_send.add_argument("--limit", type=int, default=None)

    p_fu = sub.add_parser("export-followups", help="Export follow-up drafts (CSV only, not sent)")
    p_fu.add_argument("--country", required=True, help="uk or spain")
    p_fu.add_argument("--days", type=int, default=7, help="Days since initial send")
    p_fu.add_argument("--force", action="store_true", help="Create follow-up drafts even if one exists")

    p_sent = sub.add_parser("mark-sent", help="Mark a message or contact as sent manually")
    p_sent.add_argument("--email", default=None, help="Contact email (latest initial message)")
    p_sent.add_argument(
        "--message-id",
        type=int,
        default=None,
        help="Message id after verifying delivery in Gmail Sent",
    )
    p_sent.add_argument("--date", default=None, help="Optional sent date (YYYY-MM-DD)")

    p_rep = sub.add_parser("mark-replied", help="Mark a contact as replied")
    p_rep.add_argument("--email", required=True)
    p_rep.add_argument("--notes", default="")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-env":
        cmd_init_env()
    elif args.command == "import-apollo":
        cmd_import_apollo(args.file, args.country)
    elif args.command == "import-manual":
        cmd_import_manual()
    elif args.command == "cleanup-test-data":
        cmd_cleanup_test_data(apply=args.apply)
    elif args.command == "validate-contacts":
        cmd_validate_contacts(use_hunter=not args.no_hunter)
    elif args.command == "score-leads":
        cmd_score_leads()
    elif args.command == "generate-drafts":
        cmd_generate_drafts(
            args.country,
            args.campaign,
            enrich=not args.no_enrich,
            force=args.force,
            source=args.source,
            source_file=args.source_file,
            batch_id=args.batch_id,
            min_score=args.min_score,
            include_risky=args.include_risky,
        )
    elif args.command == "approve-drafts":
        cmd_approve_drafts(csv_path=args.csv, message_id=args.message_id, email=args.email)
    elif args.command == "send-approved":
        if args.live and args.dry_run:
            raise SystemExit("Use either --live or --dry-run, not both.")
        dry_run = not args.live
        cmd_send_approved(args.country, dry_run=dry_run, limit=args.limit)
    elif args.command == "export-followups":
        cmd_export_followups(args.country, args.days, force=args.force)
    elif args.command == "mark-sent":
        if not args.email and args.message_id is None:
            raise SystemExit("Provide --email or --message-id")
        cmd_mark_sent(email=args.email, message_id=args.message_id, sent_date=args.date)
    elif args.command == "mark-replied":
        cmd_mark_replied(args.email, args.notes)


if __name__ == "__main__":
    main()
