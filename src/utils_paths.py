from pathlib import Path


def file_basename(path: str | Path | None) -> str:
    if not path:
        return ""
    return Path(str(path)).name.lower()


def source_files_match(stored: str | None, requested: str | Path | None) -> bool:
    if not stored or not requested:
        return False
    stored_norm = str(stored).replace("\\", "/").lower()
    req_norm = str(requested).replace("\\", "/").lower()
    if stored_norm == req_norm:
        return True
    return file_basename(stored) == file_basename(requested)
