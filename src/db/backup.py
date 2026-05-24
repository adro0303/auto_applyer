import shutil
from datetime import datetime
from pathlib import Path

from src.config import settings


def backup_database(db_path: Path | None = None) -> Path:
    """Create timestamped SQLite backup. Raises on failure."""
    source = db_path or settings.db_path
    if not source.exists():
        raise FileNotFoundError(f"Database not found: {source}")

    backup_dir = source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"outreach_backup_{stamp}.sqlite"
    shutil.copy2(source, dest)
    if not dest.exists() or dest.stat().st_size == 0:
        raise OSError(f"Backup failed: {dest}")
    return dest
