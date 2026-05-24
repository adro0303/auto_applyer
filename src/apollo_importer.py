import re
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from src.countries import is_target_country, normalize_country
from src.email_classification import classify_email_usability, is_valid_email
from src.lead_scoring import score_contact_record
from src.utils_paths import file_basename

FIELD_ALIASES: dict[str, list[str]] = {
    "first_name": ["first name", "first_name", "firstname"],
    "last_name": ["last name", "last_name", "lastname"],
    "full_name": ["full name", "full_name", "name", "contact name", "person name"],
    "role": ["title", "job_title", "job title", "position", "role", "headline"],
    "email": ["email", "contact email", "work email", "work_email", "business_email"],
    "email_status": ["email status", "email_status"],
    "catch_all_status": ["primary email catch-all status", "catch-all status", "catch all status"],
    "email_confidence": ["email confidence"],
    "primary_email_source": ["primary email source"],
    "primary_email_last_verified": ["primary email last verified at"],
    "linkedin_url": ["person linkedin url", "linkedin_url", "linkedin", "linkedin profile"],
    "company_linkedin_url": ["company linkedin url", "company linkedin"],
    "website": ["website", "company website", "company_website"],
    "company_domain": ["company domain", "company_domain", "domain", "website domain"],
    "country": ["country", "contact country", "person country"],
    "company_country": ["company country", "account country", "organization country"],
    "city": ["city", "contact city"],
    "company_city": ["company city", "organization city"],
    "industry": ["industry", "company industry"],
    "employee_count": ["# employees", "employees", "employee_count", "estimated num employees"],
    "keywords": ["keywords"],
    "technologies": ["technologies"],
    "departments": ["departments", "department"],
    "seniority": ["seniority"],
    "apollo_contact_id": ["apollo contact id"],
    "apollo_account_id": ["apollo account id"],
    "company": [
        "company name",
        "company",
        "company_name",
        "account name",
        "organization name",
        "organization",
    ],
    "company_for_email": ["company name for emails"],
}


def _normalize_header(header: str) -> str:
    return re.sub(r"[\s_]+", " ", str(header).strip().lower())


def build_column_map(columns: list[str]) -> dict[str, str]:
    normalized = {_normalize_header(c): c for c in columns}
    mapping: dict[str, str] = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            key = _normalize_header(alias)
            if key in normalized:
                mapping[field] = normalized[key]
                break
    return mapping


def _cell(row: pd.Series, column_map: dict[str, str], field: str) -> str:
    col = column_map.get(field)
    if not col:
        return ""
    value = row.get(col, "")
    if pd.isna(value):
        return ""
    return str(value).strip()


def derive_domain_from_website(website: str) -> str:
    if not website or str(website).lower() == "nan":
        return ""
    url = website.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        text = str(value).strip()
        if not text:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def parse_apollo_row(row: pd.Series, column_map: dict[str, str], campaign_country: str) -> dict[str, Any]:
    first = _cell(row, column_map, "first_name")
    last = _cell(row, column_map, "last_name")
    full = _cell(row, column_map, "full_name")
    if not full:
        full = f"{first} {last}".strip()
    if not full:
        full = "Unknown"

    email = _cell(row, column_map, "email").lower()
    email_status = _cell(row, column_map, "email_status")
    catch_all = _cell(row, column_map, "catch_all_status")

    contact_country_raw = _cell(row, column_map, "country")
    company_country_raw = _cell(row, column_map, "company_country") or contact_country_raw
    contact_country = normalize_country(contact_country_raw) or ""
    company_country = normalize_country(company_country_raw) or ""

    company_display = _cell(row, column_map, "company") or "Unknown Company"
    company_for_email = _cell(row, column_map, "company_for_email") or company_display

    domain = _cell(row, column_map, "company_domain").lower().lstrip("www.")
    website = _cell(row, column_map, "website")
    if website and not website.startswith("http"):
        website = f"https://{website}"
    if not domain:
        domain = derive_domain_from_website(website)

    usability, usability_reason, email_notes = classify_email_usability(
        email, email_status, catch_all
    )

    record: dict[str, Any] = {
        "first_name": first or full.split()[0],
        "last_name": last or " ".join(full.split()[1:]),
        "full_name": full,
        "role": _cell(row, column_map, "role"),
        "email": email,
        "email_status": email_status,
        "catch_all_status": catch_all,
        "linkedin_url": _cell(row, column_map, "linkedin_url"),
        "city": _cell(row, column_map, "city"),
        "country": contact_country,
        "company_country": company_country,
        "campaign_country": campaign_country,
        "seniority": _cell(row, column_map, "seniority"),
        "department": _cell(row, column_map, "departments"),
        "usability_status": usability,
        "usability_reason": usability_reason,
        "email_notes": "; ".join(email_notes),
        "source": "apollo",
        "company_name": company_display,
        "company_name_for_email": company_for_email,
        "company_domain": domain,
        "company_website": website,
        "company_industry": _cell(row, column_map, "industry"),
        "company_employee_count": _safe_int(_cell(row, column_map, "employee_count")),
        "company_linkedin_url": _cell(row, column_map, "company_linkedin_url"),
        "company_city": _cell(row, column_map, "company_city"),
        "keywords": _cell(row, column_map, "keywords"),
        "technologies": _cell(row, column_map, "technologies"),
        "apollo_contact_id": _cell(row, column_map, "apollo_contact_id"),
        "apollo_account_id": _cell(row, column_map, "apollo_account_id"),
        "email_valid_format": int(is_valid_email(email)),
        "email_verified": int(_normalize_header(email_status) in {"verified", "valid"}),
    }

    scoring = score_contact_record(record)
    record["lead_score"] = scoring["lead_score"]
    email_notes = record.get("email_notes") or ""
    score_notes = scoring.get("score_notes") or ""
    combined = [p.strip() for p in (email_notes, score_notes) if p.strip()]
    record["score_notes"] = "; ".join(dict.fromkeys(combined))
    record["contact_type"] = scoring["contact_type"]
    return record


def suggested_next_action(record: dict[str, Any]) -> str:
    domain = record.get("company_domain") or ""
    website = record.get("company_website") or ""
    linkedin = record.get("linkedin_url") or ""
    actions: list[str] = []
    if domain:
        actions.append(f"Check careers page at https://{domain}/careers")
    if website:
        actions.append("Check company website contact page")
    if linkedin:
        actions.append("Reach out via LinkedIn (manual, not automated)")
    return "; ".join(actions) if actions else "Manual research on company careers page"


def run_apollo_import(
    repo,
    csv_path,
    campaign_country: str,
    source_file: str | None = None,
) -> dict[str, Any]:
    from src.config import settings

    campaign_country = normalize_country(campaign_country)
    source_file = str(source_file or csv_path)
    df = pd.read_csv(csv_path)
    column_map = build_column_map(list(df.columns))

    batch_id = repo.create_import_batch(
        {
            "source_file": source_file,
            "country": campaign_country,
            "total_rows": len(df),
            "notes": f"basename={file_basename(source_file)}",
        }
    )

    stats: dict[str, Any] = {
        "import_batch_id": batch_id,
        "source_file": source_file,
        "total_rows": len(df),
        "usable": 0,
        "risky": 0,
        "needs_email": 0,
        "companies_inserted": 0,
        "companies_updated": 0,
        "contacts_inserted": 0,
        "contacts_updated": 0,
        "skipped_country": 0,
    }

    cleaned_contacts: list[dict] = []
    risky_contacts: list[dict] = []
    missing_contacts: list[dict] = []
    companies_map: dict[int, dict] = {}

    for _, row in df.iterrows():
        record = parse_apollo_row(row, column_map, campaign_country)

        company_country = normalize_country(record.get("company_country"))
        if not is_target_country(company_country, [campaign_country]):
            stats["skipped_country"] += 1
            continue

        usability = record["usability_status"]

        company_id, company_action = repo.import_apollo_company(
            {
                "name": record["company_name"],
                "domain": record.get("company_domain") or None,
                "website": record.get("company_website") or None,
                "country": company_country,
                "city": record.get("company_city") or None,
                "industry": record.get("company_industry") or None,
                "employee_count": record.get("company_employee_count"),
                "linkedin_url": record.get("company_linkedin_url") or None,
                "source": "apollo",
                "source_file": source_file,
                "import_batch_id": batch_id,
            }
        )
        if company_action == "inserted":
            stats["companies_inserted"] += 1
        else:
            stats["companies_updated"] += 1
        companies_map[company_id] = {
            "id": company_id,
            "name": record["company_name"],
            "domain": record.get("company_domain"),
            "import_batch_id": batch_id,
            "source_file": source_file,
        }

        if usability == "needs_email":
            stats["needs_email"] += 1
            missing_contacts.append(
                {
                    "import_batch_id": batch_id,
                    "source_file": source_file,
                    "company": record["company_name"],
                    "name": record["full_name"],
                    "role": record.get("role"),
                    "linkedin": record.get("linkedin_url"),
                    "company_website": record.get("company_website"),
                    "company_domain": record.get("company_domain"),
                    "country": record.get("country"),
                    "company_country": company_country,
                    "reason": record.get("usability_reason"),
                    "suggested_next_action": suggested_next_action(record),
                }
            )
            continue

        contact_id, contact_action = repo.import_apollo_contact(
            {**record, "status": "new", "source_file": source_file, "import_batch_id": batch_id},
            company_id,
        )
        if contact_action == "inserted":
            stats["contacts_inserted"] += 1
        else:
            stats["contacts_updated"] += 1

        export_row = {
            "import_batch_id": batch_id,
            "source_file": source_file,
            "contact_id": contact_id,
            "company": record["company_name"],
            "name": record["full_name"],
            "role": record.get("role"),
            "email": record.get("email"),
            "email_status": record.get("email_status"),
            "catch_all_status": record.get("catch_all_status"),
            "linkedin": record.get("linkedin_url"),
            "contact_country": record.get("country"),
            "company_country": company_country,
            "seniority": record.get("seniority"),
            "department": record.get("department"),
            "usability_status": usability,
            "lead_score": record.get("lead_score"),
            "score_notes": record.get("score_notes"),
            "contact_type": record.get("contact_type"),
            "company_domain": record.get("company_domain"),
            "company_website": record.get("company_website"),
        }

        if usability == "usable":
            stats["usable"] += 1
            cleaned_contacts.append(export_row)
        elif usability == "risky":
            stats["risky"] += 1
            risky_contacts.append(export_row)

    repo.update_import_batch_stats(
        batch_id,
        usable=stats["usable"],
        risky=stats["risky"],
        missing=stats["needs_email"],
        contacts_inserted=stats["contacts_inserted"],
        contacts_updated=stats["contacts_updated"],
        companies_inserted=stats["companies_inserted"],
        companies_updated=stats["companies_updated"],
    )

    processed_dir = settings.data_processed_dir
    processed_dir.mkdir(parents=True, exist_ok=True)
    suffix = campaign_country
    files = {
        "contacts_cleaned": processed_dir / f"contacts_cleaned_{suffix}.csv",
        "companies_cleaned": processed_dir / f"companies_cleaned_{suffix}.csv",
        "missing_emails": processed_dir / f"missing_emails_{suffix}.csv",
        "risky_contacts": processed_dir / f"risky_contacts_{suffix}.csv",
    }
    pd.DataFrame(cleaned_contacts).to_csv(files["contacts_cleaned"], index=False)
    pd.DataFrame(list(companies_map.values())).to_csv(files["companies_cleaned"], index=False)
    pd.DataFrame(missing_contacts).to_csv(files["missing_emails"], index=False)
    pd.DataFrame(risky_contacts).to_csv(files["risky_contacts"], index=False)

    stats["files_created"] = [str(v) for v in files.values()]
    stats["companies_imported"] = len(companies_map)
    return stats
