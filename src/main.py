"""Entry point. Use: python -m src.cli <command>"""

CLI_COMMANDS = {
    "init-env",
    "import-apollo",
    "import-manual",
    "validate-contacts",
    "score-leads",
    "generate-drafts",
    "approve-drafts",
    "send-approved",
    "export-followups",
    "mark-sent",
    "mark-replied",
}


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in CLI_COMMANDS:
        from src.cli import main as cli_main

        cli_main()
    else:
        import argparse

        from src.commands import cmd_generate_drafts, cmd_import_manual, cmd_validate_contacts
        from src.config import settings
        from src.db.schema import init_db

        parser = argparse.ArgumentParser(description="Legacy wrapper — prefer python -m src.cli")
        parser.add_argument("--country", default="uk", help="uk or spain")
        args = parser.parse_args()
        init_db(settings.db_path)
        cmd_import_manual()
        cmd_validate_contacts(use_hunter=False)
        cmd_generate_drafts(args.country, source="apollo")
