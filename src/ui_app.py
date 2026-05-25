"""
Auto Applyer Dashboard — local Streamlit UI for outreach automation.
Run: streamlit run src/ui_app.py   or double-click run_app.bat
"""

from __future__ import annotations

import html as html_mod
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import dotenv_values

from src.config import PROJECT_ROOT, settings
from src.db.repository import Repository
from src.db.schema import init_db

LIVE_CONFIRM_PHRASE = "SEND LIVE"
ENABLE_LIVE_PHRASE = "ENABLE LIVE"

FORBIDDEN_ENV_KEYS = frozenset(
    {"SMTP_APP_PASSWORD", "SMTP_PASSWORD", "OPENAI_API_KEY", "HUNTER_API_KEY"}
)
ALLOWED_ENV_KEYS = frozenset(
    {
        "SENDER_EMAIL",
        "SENDER_NAME",
        "CV_PATH",
        "DAILY_SEND_LIMIT",
        "SEND_DELAY_MIN_SECONDS",
        "SEND_DELAY_MAX_SECONDS",
        "AUTO_SEND_ENABLED",
    }
)

NAV_ITEMS: list[tuple[str, str]] = [
    ("dashboard", "nav_dashboard"),
    ("drafts", "nav_drafts"),
    ("generate", "nav_generate"),
    ("approve", "nav_approve"),
    ("dry_run", "nav_dry_run"),
    ("live_send", "nav_live_send"),
    ("reports", "nav_reports"),
    ("manual_actions", "nav_manual"),
    ("settings", "nav_settings"),
]

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Auto Applyer",
        "app_subtitle": "Local outreach control dashboard",
        "nav_dashboard": "Home",
        "nav_drafts": "Review drafts",
        "nav_generate": "Prepare emails",
        "nav_approve": "Approve emails",
        "nav_dry_run": "Simulate sending",
        "nav_live_send": "Send emails",
        "nav_reports": "Reports",
        "nav_manual": "Manual Actions",
        "nav_settings": "Settings",
        "language": "Language",
        "lang_en": "English",
        "lang_es": "Español",
        "campaign_country": "Campaign country",
        "sender_email_label": "Sender email",
        "secrets_never": "Secrets are never shown in this UI.",
        "live_enabled": "WARNING: live sending is enabled.",
        "live_disabled_safe": "Safe mode enabled: real emails cannot be sent.",
        "live_enabled_smtp": "LIVE SENDING IS ENABLED — emails will be sent via SMTP.",
        "live_on": "LIVE ON",
        "live_off": "LIVE OFF",
        "metric_sender": "Sender email",
        "metric_cv": "CV",
        "metric_auto_send": "AUTO_SEND",
        "metric_drafts": "Drafts",
        "metric_approved": "Approved",
        "metric_sent_today": "Sent today",
        "metric_report": "Latest report",
        "from_env": "from .env",
        "messages_db": "in DB",
        "ready_send": "ready to send",
        "live_sends": "live sends",
        "cv_found": "Found",
        "cv_missing": "Missing",
        "enabled": "ENABLED",
        "disabled": "DISABLED",
        "latest_dry_run": "Latest dry-run",
        "latest_live": "Latest live send",
        "not_found": "Not found",
        "rows": "rows",
        "quick_actions": "Quick actions",
        "action_review": "Review drafts",
        "action_generate": "Prepare emails",
        "action_dry_run": "Simulate sending",
        "action_live": "Send emails",
        "action_reports": "Reports",
        "draft_review": "Draft Review",
        "no_drafts": "No drafts found at `{path}`. Run **Generate Drafts** first.",
        "loaded_rows": "Loaded: `{name}` ({count} rows)",
        "search_company": "Search company",
        "contact_type": "Contact type",
        "all": "All",
        "approved_filter": "Approved",
        "min_score": "Min score",
        "select_ids": "Select message_id(s) to approve/unapprove",
        "preview_draft": "Preview one draft",
        "subject": "Subject",
        "email_body": "Email body",
        "notes": "Notes",
        "score_notes": "Score notes",
        "approve_selected": "Approve selected emails",
        "unapprove_selected": "Unapprove selected",
        "save_csv": "Save changes",
        "marked_yes": "Marked {n} row(s) as approved=yes (not saved yet).",
        "marked_no": "Marked {n} row(s) as approved=no (not saved yet).",
        "saved_csv": "Saved to `{name}` with UTF-8 BOM.",
        "generate_drafts": "Prepare emails",
        "country": "Country",
        "source_file": "Source file",
        "step_1_select_csv": "Step 1 - Select CSV",
        "step_2_import": "Step 2 - Import contacts",
        "step_3_generate": "Step 3 - Generate drafts",
        "btn_import_csv": "Import CSV",
        "importing": "Importing Apollo contacts...",
        "import_done": "Import finished.",
        "import_contacts_result": "Imported/updated contacts: {n}",
        "generate_failed": "Generate command failed (exit code {code}).",
        "import_failed": "Import command failed (exit code {code}).",
        "generate_no_drafts_warning": "No drafts were generated. You may need to import the CSV first or lower min_score.",
        "generate_no_drafts_actions": "Suggested actions:\n- Import CSV first\n- Check Company Country / country is Spain\n- Lower min_score\n- Review email classification\n- Verify valid emails exist",
        "drafts_generated_count": "Generated {n} draft(s).",
        "drafts_export_path": "Draft file: `{path}`",
        "force_regen": "Force regenerate (--force)",
        "btn_generate": "Prepare emails",
        "generating": "Generating drafts...",
        "drafts_generated": "Drafts generated.",
        "approve_db_title": "Approve Drafts to Database",
        "approve_import_hint": "Imports rows with `approved=yes` from `{path}` into SQLite.",
        "btn_approve_db": "Approve selected drafts",
        "running_approve": "Running approve-drafts...",
        "dry_run_title": "Dry Run",
        "limit": "Limit",
        "btn_dry_run": "Simulate sending",
        "running_dry_run": "Running dry-run (read-only)...",
        "latest_dry_report": "Latest dry-run report",
        "cv_found_count": "CV found: {ok}/{total}",
        "live_send_title": "Live Send",
        "confirm_send_live": 'Type exactly "SEND LIVE" to unlock send button',
        "btn_send_live": "Send approved emails",
        "sending": "Sending live emails...",
        "go_settings_enable": "Go to Settings to enable live sending",
        "reports_title": "Reports",
        "no_live_report": "No live send report yet.",
        "no_dry_report": "No dry-run report yet.",
        "report_live_title": "Live send report",
        "report_dry_title": "Dry-run report",
        "manual_title": "Manual Actions",
        "mark_sent_help": "Mark message as sent after checking Gmail Sent (for uncertain 4xx).",
        "message_id": "message_id",
        "btn_mark_sent": "Mark as sent",
        "updating_db": "Updating database...",
        "marked_sent": "Message {mid} marked as sent.",
        "command": "Command",
        "output": "Output",
        "no_output": "(no output)",
        "no_report_data": "No data in report.",
        "uncertain_warning": "Some emails returned **uncertain** status. Check Gmail Sent before retrying.",
        "failed_sends": "Failed sends detected:",
        "exit_code": "exit code",
        "settings_title": "Settings",
        "settings_subtitle": "Operational settings saved to `.env` (secrets are never edited here).",
        "sender_email": "SENDER_EMAIL",
        "sender_name": "SENDER_NAME",
        "cv_path": "CV_PATH",
        "daily_send_limit": "DAILY_SEND_LIMIT",
        "send_delay_min": "SEND_DELAY_MIN_SECONDS",
        "send_delay_max": "SEND_DELAY_MAX_SECONDS",
        "auto_send_label": "AUTO_SEND_ENABLED",
        "auto_send_help_off": "OFF - safe mode.",
        "auto_send_help_on": "ON - live sending enabled.",
        "enable_live_warning": "Turning on live sending is dangerous.",
        "enable_live_placeholder": "Type ENABLE LIVE",
        "btn_save_settings": "Save changes",
        "settings_saved": "Settings saved. Backup: `.env.backup`",
        "settings_save_failed": "Could not save settings: {reason}",
        "safe_mode_on": "Safe mode enabled. AUTO_SEND_ENABLED=false.",
        "env_missing": "No `.env` file found. Run `python -m src.cli init-env` first.",
        "invalid_enable_phrase": 'Type exactly "ENABLE LIVE" to enable live sending.',
        "page_intro_inicio": "From here you can prepare emails, review them, approve them, simulate sending, and send in a controlled way.",
        "page_intro_generate": "Import an Apollo CSV and generate personalized drafts without sending anything.",
        "page_intro_drafts": "Read generated emails and mark as approved only those you want to send.",
        "page_intro_approve": "Save into the database the emails marked as approved in the CSV.",
        "page_intro_dry_run": "Check which emails would be sent and whether the CV is attached, without sending real emails.",
        "page_intro_live_send": "Send only approved emails. This action stays blocked unless live sending is enabled and manually confirmed.",
        "page_intro_reports": "Review dry-run and live-send results.",
        "page_intro_manual": "Use manual recovery actions for special cases.",
        "page_intro_settings": "Configure sender, CV, limits, delays, and safe mode.",
        "result_sent": "sent",
        "result_dry_run": "dry run",
        "result_failed": "failed",
        "result_uncertain": "uncertain",
        "result_skipped": "skipped",
        "btn_enable_live": "Activate live sending",
        "btn_disable_live": "Disable live sending",
    },
    "es": {
        "app_title": "Auto Applyer",
        "app_subtitle": "Panel local de control de outreach",
        "nav_dashboard": "Inicio",
        "nav_drafts": "Revisar borradores",
        "nav_generate": "Preparar correos",
        "nav_approve": "Aprobar correos",
        "nav_dry_run": "Simular envío",
        "nav_live_send": "Enviar correos",
        "nav_reports": "Informes",
        "nav_manual": "Acciones manuales",
        "nav_settings": "Ajustes",
        "language": "Idioma",
        "lang_en": "English",
        "lang_es": "Español",
        "campaign_country": "País de campaña",
        "sender_email_label": "Email remitente",
        "secrets_never": "Los secretos nunca se muestran en esta interfaz.",
        "live_enabled": "ATENCIÓN: el envío real está activado.",
        "live_disabled_safe": "Modo seguro activado: no se pueden enviar correos reales.",
        "live_enabled_smtp": "EL ENVÍO REAL ESTÁ ACTIVADO — se enviarán correos por SMTP.",
        "live_on": "ENVÍO ACTIVO",
        "live_off": "ENVÍO OFF",
        "metric_sender": "Email remitente",
        "metric_cv": "CV",
        "metric_auto_send": "AUTO_SEND",
        "metric_drafts": "Borradores",
        "metric_approved": "Aprobados",
        "metric_sent_today": "Enviados hoy",
        "metric_report": "Último informe",
        "from_env": "desde .env",
        "messages_db": "en BD",
        "ready_send": "listos para enviar",
        "live_sends": "envíos reales",
        "cv_found": "Encontrado",
        "cv_missing": "No encontrado",
        "enabled": "ACTIVADO",
        "disabled": "DESACTIVADO",
        "latest_dry_run": "Última simulación",
        "latest_live": "Último envío real",
        "not_found": "No encontrado",
        "rows": "filas",
        "quick_actions": "Acciones rápidas",
        "action_review": "Revisar borradores",
        "action_generate": "Preparar correos",
        "action_dry_run": "Simular envío",
        "action_live": "Enviar correos",
        "action_reports": "Ver informes",
        "draft_review": "Revisión de borradores",
        "no_drafts": "No hay borradores en `{path}`. Ejecuta **Generar borradores** primero.",
        "loaded_rows": "Cargado: `{name}` ({count} filas)",
        "search_company": "Buscar empresa",
        "contact_type": "Tipo de contacto",
        "all": "Todos",
        "approved_filter": "Aprobado",
        "min_score": "Puntuación mín.",
        "select_ids": "Selecciona message_id(s) para aprobar/desaprobar",
        "preview_draft": "Vista previa de un borrador",
        "subject": "Asunto",
        "email_body": "Cuerpo del email",
        "notes": "Notas",
        "score_notes": "Notas de puntuación",
        "approve_selected": "Aprobar correos seleccionados",
        "unapprove_selected": "Desaprobar seleccionados",
        "save_csv": "Guardar cambios",
        "marked_yes": "Marcados {n} como approved=yes (sin guardar aún).",
        "marked_no": "Marcados {n} como approved=no (sin guardar aún).",
        "saved_csv": "Guardado en `{name}` con UTF-8 BOM.",
        "generate_drafts": "Preparar correos",
        "country": "País",
        "source_file": "Archivo origen",
        "step_1_select_csv": "Paso 1 - Seleccionar CSV",
        "step_2_import": "Paso 2 - Importar contactos",
        "step_3_generate": "Paso 3 - Generar borradores",
        "btn_import_csv": "Importar CSV",
        "importing": "Importando contactos de Apollo...",
        "import_done": "Importación finalizada.",
        "import_contacts_result": "Contactos importados/actualizados: {n}",
        "generate_failed": "El comando de generación falló (exit code {code}).",
        "import_failed": "El comando de importación falló (exit code {code}).",
        "generate_no_drafts_warning": "No se han generado borradores. Puede que primero tengas que importar el CSV o bajar el min_score.",
        "generate_no_drafts_actions": "Acciones sugeridas:\n- Importar primero el CSV\n- Revisar que Company Country / country sea Spain\n- Bajar min_score\n- Revisar clasificación de emails\n- Revisar que haya emails válidos",
        "drafts_generated_count": "Se han generado {n} borradores.",
        "drafts_export_path": "Archivo de borradores: `{path}`",
        "force_regen": "Forzar regeneración (--force)",
        "btn_generate": "Preparar correos",
        "generating": "Generando borradores...",
        "drafts_generated": "Borradores generados.",
        "approve_db_title": "Aprobar borradores en base de datos",
        "approve_import_hint": "Importa filas con `approved=yes` desde `{path}` a SQLite.",
        "btn_approve_db": "Aprobar borradores seleccionados",
        "running_approve": "Ejecutando approve-drafts...",
        "dry_run_title": "Simulación (dry-run)",
        "limit": "Límite",
        "btn_dry_run": "Simular envío",
        "running_dry_run": "Ejecutando simulación (solo lectura)...",
        "latest_dry_report": "Último informe de simulación",
        "cv_found_count": "CV encontrado: {ok}/{total}",
        "live_send_title": "Envío real",
        "confirm_send_live": 'Escribe exactamente "SEND LIVE" para desbloquear el envío',
        "btn_send_live": "Enviar correos aprobados",
        "sending": "Enviando correos en vivo...",
        "go_settings_enable": "Ir a Ajustes para activar envío real",
        "reports_title": "Informes",
        "no_live_report": "No hay informe de envío real todavía.",
        "no_dry_report": "No hay informe de simulación todavía.",
        "report_live_title": "Informe de envío real",
        "report_dry_title": "Informe de simulación",
        "manual_title": "Acciones manuales",
        "mark_sent_help": "Marcar mensaje como enviado tras verificar Gmail Sent (para uncertain 4xx).",
        "message_id": "message_id",
        "btn_mark_sent": "Marcar como enviado",
        "updating_db": "Actualizando base de datos...",
        "marked_sent": "Mensaje {mid} marcado como enviado.",
        "command": "Comando",
        "output": "Salida",
        "no_output": "(sin salida)",
        "no_report_data": "Sin datos en el informe.",
        "uncertain_warning": "Algunos correos están en **uncertain**. Revisa Gmail Sent antes de reintentar.",
        "failed_sends": "Envíos fallidos detectados:",
        "exit_code": "código de salida",
        "settings_title": "Ajustes",
        "settings_subtitle": "Ajustes operativos guardados en `.env` (sin exponer secretos).",
        "sender_email": "SENDER_EMAIL",
        "sender_name": "SENDER_NAME",
        "cv_path": "CV_PATH",
        "daily_send_limit": "DAILY_SEND_LIMIT",
        "send_delay_min": "SEND_DELAY_MIN_SECONDS",
        "send_delay_max": "SEND_DELAY_MAX_SECONDS",
        "auto_send_label": "AUTO_SEND_ENABLED",
        "auto_send_help_off": "OFF - modo seguro.",
        "auto_send_help_on": "ON - envío real activado.",
        "enable_live_warning": "Activar envío real es peligroso.",
        "enable_live_placeholder": "Escribe ENABLE LIVE",
        "btn_save_settings": "Guardar cambios",
        "settings_saved": "Ajustes guardados. Copia: `.env.backup`",
        "settings_save_failed": "No se pudieron guardar los ajustes: {reason}",
        "safe_mode_on": "Modo seguro activado. AUTO_SEND_ENABLED=false.",
        "env_missing": "No existe `.env`. Ejecuta `python -m src.cli init-env` primero.",
        "invalid_enable_phrase": 'Escribe exactamente "ENABLE LIVE" para activar envío real.',
        "page_intro_inicio": "Desde aquí puedes preparar correos, revisarlos, aprobarlos, simular el envío y enviarlos de forma controlada.",
        "page_intro_generate": "Importa el CSV de Apollo y genera borradores personalizados sin enviar nada.",
        "page_intro_drafts": "Lee los correos generados y marca como aprobados solo los que quieras enviar.",
        "page_intro_approve": "Guarda en la base de datos los correos que has marcado como aprobados en el CSV.",
        "page_intro_dry_run": "Comprueba qué correos se enviarían y si el CV está adjunto, sin enviar nada real.",
        "page_intro_live_send": "Envía solo los correos aprobados. Esta acción está bloqueada salvo que actives el envío real y confirmes manualmente.",
        "page_intro_reports": "Revisa los resultados de simulaciones y envíos reales.",
        "page_intro_manual": "Usa acciones manuales para casos excepcionales.",
        "page_intro_settings": "Configura remitente, CV, límites, pausas entre correos y modo seguro.",
        "result_sent": "enviado",
        "result_dry_run": "simulación",
        "result_failed": "fallido",
        "result_uncertain": "incierto",
        "result_skipped": "omitido",
        "btn_enable_live": "Activar envío real",
        "btn_disable_live": "Desactivar envío real",
    },
}


def init_session() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "language" not in st.session_state:
        st.session_state.language = "es"
    if "campaign_country" not in st.session_state:
        st.session_state.campaign_country = "uk"


def t(key: str, **kwargs: Any) -> str:
    lang = st.session_state.get("language", "en")
    template = TEXT.get(lang, TEXT["en"]).get(key, TEXT["en"].get(key, key))
    return template.format(**kwargs) if kwargs else template


def set_page(page_name: str) -> None:
    st.session_state.page = page_name


def get_project_root() -> Path:
    return PROJECT_ROOT


def env_file_path() -> Path:
    return get_project_root() / ".env"


def load_env_lines() -> list[str]:
    path = env_file_path()
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def get_env_value(key: str, default: str = "") -> str:
    raw = dotenv_values(env_file_path()) if env_file_path().exists() else {}
    val = raw.get(key)
    return default if val is None else str(val)


def update_env_value(lines: list[str], key: str, value: str) -> list[str]:
    if key in FORBIDDEN_ENV_KEYS:
        raise ValueError(f"Forbidden key: {key}")
    if key not in ALLOWED_ENV_KEYS:
        raise ValueError(f"Key not allowed in UI: {key}")
    out: list[str] = []
    seen = False
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for line in lines:
        if pattern.match(line):
            out.append(f"{key}={value}\n")
            seen = True
        else:
            out.append(line if line.endswith("\n") else line + "\n")
    if not seen:
        out.append(f"{key}={value}\n")
    return out


def save_env_safely(updates: dict[str, str]) -> tuple[bool, str]:
    for key in updates:
        if key in FORBIDDEN_ENV_KEYS:
            return False, f"forbidden key {key}"
        if key not in ALLOWED_ENV_KEYS:
            return False, f"key not allowed: {key}"
    path = env_file_path()
    if not path.exists():
        return False, "missing .env"
    lines = load_env_lines()
    for key, value in updates.items():
        lines = update_env_value(lines, key, value)
    backup_path = get_project_root() / ".env.backup"
    shutil.copy2(path, backup_path)
    path.write_text("".join(lines), encoding="utf-8")
    return True, str(backup_path)


def load_env_safe() -> dict[str, str | bool]:
    raw: dict[str, str | None] = {}
    if env_file_path().exists():
        raw = dotenv_values(env_file_path())
    auto = str(raw.get("AUTO_SEND_ENABLED", os.getenv("AUTO_SEND_ENABLED", "false"))).lower()
    return {
        "sender_email": raw.get("SENDER_EMAIL") or raw.get("YOUR_EMAIL") or settings.sender_email or "—",
        "sender_name": raw.get("SENDER_NAME") or settings.sender_name or "",
        "cv_path": raw.get("CV_PATH") or settings.cv_path,
        "daily_send_limit": raw.get("DAILY_SEND_LIMIT") or str(settings.daily_send_limit),
        "send_delay_min": raw.get("SEND_DELAY_MIN_SECONDS") or str(settings.send_delay_min_seconds),
        "send_delay_max": raw.get("SEND_DELAY_MAX_SECONDS") or str(settings.send_delay_max_seconds),
        "auto_send_enabled": auto in {"1", "true", "yes", "on"},
    }


def run_cli_command(args: list[str], stdin_text: str | None = None) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "src.cli", *args]
    result = subprocess.run(
        cmd,
        cwd=str(get_project_root()),
        capture_output=True,
        text=True,
        input=stdin_text,
        encoding="utf-8",
        errors="replace",
    )
    output = (result.stdout or "") + (result.stderr or "")
    return {
        "returncode": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
        "output": output.strip(),
        "cmd": " ".join(cmd),
    }


def combined_output(result: dict[str, Any]) -> str:
    return f"{result.get('stdout', '')}\n{result.get('stderr', '')}\n{result.get('output', '')}".strip()


def parse_generate_draft_counts(output: str) -> tuple[int, int]:
    created = 0
    exported = 0
    for pattern in (r"created\s+(\d+)\s+new\s+draft", r"exported\s+(\d+)\s+draft"):
        for match in re.finditer(pattern, output, flags=re.IGNORECASE):
            value = int(match.group(1))
            if "created" in pattern:
                created = max(created, value)
            else:
                exported = max(exported, value)
    return created, exported


def is_generate_noop(output: str) -> bool:
    output_l = output.lower()
    no_op_tokens = (
        "no eligible contacts",
        "created 0 new draft",
        "exported 0 draft",
        "run import-apollo first",
    )
    return any(token in output_l for token in no_op_tokens)


def parse_generate_export_path(output: str) -> str:
    match = re.search(r"exported\s+\d+\s+draft\(s\)\s+to\s+([^\r\n]+)", output, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


def evaluate_generate_result(result: dict[str, Any]) -> dict[str, Any]:
    output = combined_output(result)
    created, exported = parse_generate_draft_counts(output)
    success = result["returncode"] == 0 and (created > 0 or exported > 0)
    noop = result["returncode"] == 0 and not success and is_generate_noop(output)
    return {
        "success": success,
        "noop": noop,
        "created": created,
        "exported": exported,
        "export_path": parse_generate_export_path(output),
        "output": output,
    }


def parse_import_contact_counts(output: str) -> tuple[int, int]:
    inserted = 0
    updated = 0
    m_inserted = re.search(r"contacts inserted:\s*(\d+)", output, flags=re.IGNORECASE)
    m_updated = re.search(r"contacts updated:\s*(\d+)", output, flags=re.IGNORECASE)
    if m_inserted:
        inserted = int(m_inserted.group(1))
    if m_updated:
        updated = int(m_updated.group(1))
    return inserted, updated


def load_csv_safe(path: Path | str) -> pd.DataFrame | None:
    p = Path(path)
    if not p.is_absolute():
        p = get_project_root() / p
    if not p.exists():
        return None
    try:
        return pd.read_csv(p, encoding="utf-8-sig")
    except Exception:
        try:
            return pd.read_csv(p)
        except Exception:
            return None


def list_lead_csv_files() -> list[str]:
    leads_dir = get_project_root() / "data" / "leads"
    if not leads_dir.exists():
        return []
    files = sorted(leads_dir.glob("*.csv"), key=lambda p: p.name.lower())
    return [str(p.relative_to(get_project_root())).replace("\\", "/") for p in files]


def drafts_csv_path(country: str = "uk") -> Path:
    return get_project_root() / "data" / "output" / f"outreach_drafts_{country}.csv"


def save_approved_changes(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def get_repo() -> Repository | None:
    try:
        init_db(settings.db_path)
        return Repository(settings.db_path)
    except Exception:
        return None


def report_summary(path: Path) -> dict[str, Any]:
    df = load_csv_safe(path)
    if df is None or df.empty:
        return {"exists": False, "path": str(path)}
    counts: dict[str, int] = {}
    if "result" in df.columns:
        counts = df["result"].value_counts().to_dict()
    return {"exists": True, "path": str(path), "rows": len(df), "counts": counts}


def render_status_badge(label: str, kind: str = "neutral") -> str:
    colors = {
        "safe": ("#10b981", "#064e3b"),
        "warning": ("#fbbf24", "#78350f"),
        "danger": ("#ef4444", "#7f1d1d"),
        "neutral": ("#94a3b8", "#1e293b"),
    }
    fg, bg = colors.get(kind, colors["neutral"])
    return (
        f'<span style="display:inline-block;padding:0.25rem 0.65rem;border-radius:999px;'
        f'font-size:0.78rem;font-weight:600;color:{fg};background:{bg};'
        f'border:1px solid {fg}33;">{html_mod.escape(label)}</span>'
    )


def render_metric_card(title: str, value: str | int, subtitle: str = "", accent: str = "#6366f1") -> str:
    return f"""
    <div class="metric-card" style="border-top:3px solid {accent};">
        <span class="metric-label">{html_mod.escape(str(title))}</span>
        <span class="metric-value" title="{html_mod.escape(str(value))}">{html_mod.escape(str(value))}</span>
        <span class="metric-sub">{html_mod.escape(str(subtitle))}</span>
    </div>
    """


def inject_custom_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .stApp {
            background: linear-gradient(160deg, #070b14 0%, #0d1117 40%, #0a0f1a 100%);
            color: #e2e8f0;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            border-right: 1px solid #1e293b;
        }
        section.main > div.block-container {
            padding-top: 1rem;
            max-width: 100%;
        }
        .page-header {
            background: linear-gradient(135deg, #2563eb 0%, #7c3aed 45%, #10b981 100%);
            padding: 1.2rem 1.4rem;
            border-radius: 14px;
            margin-bottom: 1rem;
            box-shadow: 0 8px 30px rgba(37, 99, 235, 0.25);
        }
        .page-header h1 { color: #fff; margin: 0; font-size: 1.5rem; font-weight: 700; }
        .page-header p { color: rgba(255,255,255,0.86); margin: 0.3rem 0 0; font-size: 0.9rem; }
        .metric-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            min-height: 98px;
        }
        .metric-label { display:block; font-size:0.72rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.04em; }
        .metric-value {
            display:block; font-size:1.2rem; font-weight:700; color:#f8fafc; margin:0.3rem 0;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .metric-sub { display:block; font-size:0.78rem; color:#64748b; }
        .action-card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.8rem;
        }
        .danger-card {
            background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%);
            border: 2px solid #ef4444;
            border-radius: 14px;
            padding: 1rem;
            margin: 0.8rem 0;
            color: #fecaca;
            font-weight: 600;
            text-align: center;
        }
        .safe-card {
            background: #052e16;
            border: 1px solid #10b981;
            border-radius: 14px;
            padding: 0.9rem;
            color: #6ee7b7;
            margin: 0.8rem 0;
        }
        .terminal-box {
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 1rem;
            font-family: Consolas, Monaco, monospace;
            font-size: 0.82rem;
            color: #7ee787;
            white-space: pre-wrap;
            max-height: 320px;
            overflow-y: auto;
            margin-top: 0.75rem;
        }
        .stButton > button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            border: 1px solid #30363d !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #2563eb, #7c3aed) !important;
            border: none !important;
            color: white !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title_key: str, subtitle_key: str = "app_subtitle") -> None:
    st.markdown(
        f'<div class="page-header"><h1>{html_mod.escape(t(title_key))}</h1>'
        f'<p>{html_mod.escape(t(subtitle_key))}</p></div>',
        unsafe_allow_html=True,
    )


def render_terminal_output(result: dict[str, Any]) -> None:
    st.markdown(f"**{t('command')}:** `{result['cmd']}`")
    box = result.get("output") or t("no_output")
    rc = result.get("returncode", 0)
    content = f"{t('exit_code')}: {rc}\n\n{box}"
    st.markdown(
        f'<div class="terminal-box">{html_mod.escape(content)}</div>',
        unsafe_allow_html=True,
    )


def highlight_result(val: str) -> str:
    colors = {
        "sent": "background-color: #064e3b; color: #6ee7b7",
        "dry_run": "background-color: #78350f; color: #fde68a",
        "failed": "background-color: #7f1d1d; color: #fecaca",
        "uncertain": "background-color: #7c2d12; color: #fed7aa",
        "skipped": "background-color: #1e293b; color: #94a3b8",
    }
    return colors.get(str(val).lower(), "")


def translate_result_value(value: str) -> str:
    mapping = {
        "sent": t("result_sent"),
        "dry_run": t("result_dry_run"),
        "failed": t("result_failed"),
        "uncertain": t("result_uncertain"),
        "skipped": t("result_skipped"),
    }
    return mapping.get(str(value).lower(), str(value))


def show_report_table(df: pd.DataFrame, title: str) -> None:
    st.subheader(title)
    if df is None or df.empty:
        st.warning(t("no_report_data"))
        return
    display_df = df.copy()
    if "result" in display_df.columns:
        display_df["result"] = display_df["result"].map(translate_result_value)
        styled = display_df.style.map(highlight_result, subset=["result"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    if "result" in df.columns:
        if (df["result"] == "uncertain").any():
            st.warning(t("uncertain_warning"))
        failed = df[df["result"] == "failed"]
        if not failed.empty and "error" in failed.columns:
            st.error(t("failed_sends"))
            for _, row in failed.iterrows():
                st.markdown(f"- **{row.get('email', '?')}**: {row.get('error', 'unknown')}")


def render_sidebar(env: dict[str, str | bool]) -> str:
    st.sidebar.markdown(f"## {t('app_title')}")
    st.sidebar.caption(t("app_subtitle"))
    lang_choice = st.sidebar.selectbox(
        t("language"),
        options=["en", "es"],
        format_func=lambda code: t("lang_en") if code == "en" else t("lang_es"),
        index=0 if st.session_state.language == "en" else 1,
        key="sidebar_lang",
    )
    if lang_choice != st.session_state.language:
        st.session_state.language = lang_choice
        st.rerun()
    country = st.sidebar.selectbox(
        t("campaign_country"),
        ["uk", "spain"],
        index=0 if st.session_state.campaign_country == "uk" else 1,
        key="sidebar_country",
    )
    st.session_state.campaign_country = country
    st.sidebar.markdown("---")
    st.sidebar.caption(t("sender_email_label"))
    st.sidebar.code(str(env["sender_email"]))
    st.sidebar.markdown(
        render_status_badge(
            t("live_on") if env["auto_send_enabled"] else t("live_off"),
            "danger" if env["auto_send_enabled"] else "safe",
        ),
        unsafe_allow_html=True,
    )
    if env["auto_send_enabled"]:
        st.sidebar.error(t("live_enabled"))
    else:
        st.sidebar.success(t("live_disabled_safe"))
    st.sidebar.caption(t("secrets_never"))
    st.sidebar.markdown("---")
    current = st.session_state.get("page", "dashboard")
    for page_id, label_key in NAV_ITEMS:
        if st.sidebar.button(
            t(label_key),
            key=f"nav_{page_id}",
            type="primary" if current == page_id else "secondary",
            use_container_width=True,
        ):
            set_page(page_id)
            st.rerun()
    return country


def render_dashboard(env: dict[str, str | bool], repo: Repository | None) -> None:
    render_page_header("nav_dashboard", "page_intro_inicio")
    cv_path = get_project_root() / str(env["cv_path"]) if env["cv_path"] else settings.cv_file
    cv_exists = cv_path.exists()
    stats = repo.stats() if repo else {}
    sent_today = repo.count_sent_today() if repo else 0
    dry_report = report_summary(settings.data_output_dir / "send_report_dry_run.csv")
    live_report = report_summary(settings.data_output_dir / "send_report.csv")
    latest_label = t("not_found")
    if live_report.get("exists"):
        latest_label = f"{t('latest_live')}: {live_report['rows']} {t('rows')}"
    elif dry_report.get("exists"):
        latest_label = f"{t('latest_dry_run')}: {dry_report['rows']} {t('rows')}"
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            render_metric_card(t("metric_sender"), str(env["sender_email"]), t("from_env"), "#60a5fa"),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            render_metric_card(
                t("metric_cv"), t("cv_found") if cv_exists else t("cv_missing"), "", "#10b981"
            ),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            render_metric_card(
                t("metric_auto_send"),
                t("enabled") if env["auto_send_enabled"] else t("disabled"),
                "",
                "#ef4444" if env["auto_send_enabled"] else "#22c55e",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            render_metric_card(t("metric_report"), latest_label, "", "#a855f7"),
            unsafe_allow_html=True,
        )
    c5, c6, c7 = st.columns(3)
    with c5:
        st.markdown(
            render_metric_card(t("metric_drafts"), stats.get("drafts", "—"), t("messages_db"), "#6366f1"),
            unsafe_allow_html=True,
        )
    with c6:
        st.markdown(
            render_metric_card(t("metric_approved"), stats.get("approved", "—"), t("ready_send"), "#818cf8"),
            unsafe_allow_html=True,
        )
    with c7:
        st.markdown(
            render_metric_card(t("metric_sent_today"), sent_today, t("live_sends"), "#22c55e"),
            unsafe_allow_html=True,
        )
    st.subheader(t("quick_actions"))
    a1, a2, a3, a4, a5 = st.columns(5)
    actions = [
        (a1, "drafts", "action_review"),
        (a2, "generate", "action_generate"),
        (a3, "dry_run", "action_dry_run"),
        (a4, "live_send", "action_live"),
        (a5, "reports", "action_reports"),
    ]
    for col, page_id, key in actions:
        with col:
            st.markdown(f'<div class="action-card">{html_mod.escape(t(key))}</div>', unsafe_allow_html=True)
            if st.button(t(key), key=f"quick_{page_id}", use_container_width=True):
                set_page(page_id)
                st.rerun()


def render_drafts(country: str = "uk") -> None:
    render_page_header("nav_drafts", "page_intro_drafts")
    path = drafts_csv_path(country)
    if "drafts_df" not in st.session_state or st.session_state.get("drafts_path") != str(path):
        st.session_state.drafts_df = load_csv_safe(path)
        st.session_state.drafts_path = str(path)
    df = st.session_state.drafts_df
    if df is None or df.empty:
        st.warning(t("no_drafts", path=str(path)))
        return
    st.caption(t("loaded_rows", name=path.name, count=len(df)))
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        company_q = st.text_input(t("search_company"), key="filter_company")
    with col_f2:
        types = [t("all")]
        if "contact_type" in df.columns:
            types += sorted(df["contact_type"].dropna().unique().tolist())
        type_f = st.selectbox(t("contact_type"), types, key="filter_type")
    with col_f3:
        appr_f = st.selectbox(t("approved_filter"), [t("all"), "yes", "no"], key="filter_approved")
    with col_f4:
        min_score = st.number_input(t("min_score"), min_value=0, max_value=100, value=0, key="filter_score")
    filtered = df.copy()
    if company_q and "company" in filtered.columns:
        filtered = filtered[filtered["company"].astype(str).str.contains(company_q, case=False, na=False)]
    if type_f != t("all") and "contact_type" in filtered.columns:
        filtered = filtered[filtered["contact_type"] == type_f]
    if appr_f != t("all") and "approved" in filtered.columns:
        filtered = filtered[filtered["approved"].astype(str).str.lower() == appr_f]
    if min_score > 0 and "lead_score" in filtered.columns:
        filtered = filtered[filtered["lead_score"] >= min_score]
    display_cols = [
        c
        for c in ["message_id", "company", "name", "email", "contact_type", "lead_score", "subject", "approved", "status"]
        if c in filtered.columns
    ]
    st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)
    ids = filtered["message_id"].tolist() if "message_id" in filtered.columns else []
    if not ids:
        return
    selected_ids = st.multiselect(t("select_ids"), ids, key="draft_select_ids")
    sel_single = st.selectbox(t("preview_draft"), ids, key="draft_preview_id")
    if sel_single is not None:
        row = df[df["message_id"] == sel_single].iloc[0]
        st.markdown(f"**{t('subject')}:** {row.get('subject', '')}")
        st.text_area(t("email_body"), value=str(row.get("email_body", "")), height=220, disabled=True)
        if "notes" in row:
            st.markdown(f"**{t('notes')}:** {row.get('notes', '')}")
        if "score_notes" in row:
            st.markdown(f"**{t('score_notes')}:** {row.get('score_notes', '')}")
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if st.button(t("approve_selected"), type="primary", disabled=not selected_ids):
            for mid in selected_ids:
                df.loc[df["message_id"] == mid, "approved"] = "yes"
            st.session_state.drafts_df = df
            st.success(t("marked_yes", n=len(selected_ids)))
    with bc2:
        if st.button(t("unapprove_selected"), disabled=not selected_ids):
            for mid in selected_ids:
                df.loc[df["message_id"] == mid, "approved"] = "no"
            st.session_state.drafts_df = df
            st.info(t("marked_no", n=len(selected_ids)))
    with bc3:
        if st.button(t("save_csv")):
            save_approved_changes(st.session_state.drafts_df, path)
            st.success(t("saved_csv", name=path.name))


def render_generate() -> None:
    render_page_header("nav_generate", "page_intro_generate")
    default_idx = 1 if st.session_state.get("campaign_country") == "spain" else 0
    country = st.selectbox(t("country"), ["uk", "spain"], index=default_idx, key="gen_country")
    st.session_state.campaign_country = country

    st.markdown(f"### {t('step_1_select_csv')}")
    csv_options = list_lead_csv_files()
    preferred_spain = "data/leads/apollo-contacts-export-spain.csv"
    preferred_spain_alt = "data/leads/apollo-contacts-export-esp.csv"
    preferred_uk = "data/leads/apollo-contacts-export.csv"
    if csv_options:
        if country == "spain" and preferred_spain in csv_options:
            source_default = preferred_spain
        elif country == "spain" and preferred_spain_alt in csv_options:
            source_default = preferred_spain_alt
        elif country == "uk" and preferred_uk in csv_options:
            source_default = preferred_uk
        else:
            source_default = csv_options[0]
        source_file = st.selectbox(
            t("source_file"),
            options=csv_options,
            index=csv_options.index(source_default),
            key="gen_source_select",
        )
    else:
        source_file = st.text_input(
            t("source_file"),
            value=preferred_spain if country == "spain" else preferred_uk,
            key="gen_source_fallback",
        )

    st.markdown(f"### {t('step_2_import')}")
    if st.button(t("btn_import_csv"), key="btn_import_csv", type="secondary"):
        import_args = ["import-apollo", "--file", source_file, "--country", country]
        with st.spinner(t("importing")):
            import_result = run_cli_command(import_args)
        render_terminal_output(import_result)
        output = combined_output(import_result)
        inserted, updated = parse_import_contact_counts(output)
        if import_result["returncode"] == 0:
            st.info(t("import_done"))
            st.info(t("import_contacts_result", n=inserted + updated))
        else:
            st.error(t("import_failed", code=import_result["returncode"]))

    st.markdown(f"### {t('step_3_generate')}")
    min_score = st.number_input(t("min_score"), min_value=0, max_value=100, value=50, key="gen_min_score")
    force = st.checkbox(t("force_regen"), value=True, key="gen_force")
    if st.button(t("btn_generate"), type="primary"):
        args = [
            "generate-drafts",
            "--country",
            country,
            "--source",
            "apollo",
            "--source-file",
            source_file,
            "--min-score",
            str(min_score),
            "--no-enrich",
        ]
        if force:
            args.append("--force")
        with st.spinner(t("generating")):
            result = run_cli_command(args)
        render_terminal_output(result)
        evaluation = evaluate_generate_result(result)
        generated_count = max(evaluation["created"], evaluation["exported"])
        if evaluation["success"]:
            st.session_state.pop("drafts_df", None)
            st.success(t("drafts_generated_count", n=generated_count))
            if evaluation["export_path"]:
                st.caption(t("drafts_export_path", path=evaluation["export_path"]))
        elif evaluation["noop"]:
            st.warning(t("generate_no_drafts_warning"))
            st.info(t("generate_no_drafts_actions"))
        elif result["returncode"] == 0:
            st.warning(t("generate_no_drafts_warning"))
        else:
            st.error(t("generate_failed", code=result["returncode"]))


def render_approve(country: str = "uk") -> None:
    render_page_header("nav_approve", "page_intro_approve")
    csv_path = f"data/output/outreach_drafts_{country}.csv"
    st.caption(t("approve_import_hint", path=csv_path))
    if st.button(t("btn_approve_db"), type="primary"):
        with st.spinner(t("running_approve")):
            result = run_cli_command(["approve-drafts", "--csv", csv_path])
        render_terminal_output(result)


def render_dry_run(country: str = "uk") -> None:
    render_page_header("nav_dry_run", "page_intro_dry_run")
    limit = st.number_input(t("limit"), min_value=1, max_value=50, value=5, key="dry_limit")
    if st.button(t("btn_dry_run"), type="primary"):
        with st.spinner(t("running_dry_run")):
            result = run_cli_command(["send-approved", "--country", country, "--dry-run", "--limit", str(limit)])
        render_terminal_output(result)
    df = load_csv_safe(get_project_root() / "data" / "output" / "send_report_dry_run.csv")
    if df is not None:
        show_report_table(df, t("latest_dry_report"))
        if "cv_attachment" in df.columns:
            cv_ok = (df["cv_attachment"] == "found").sum()
            st.markdown(render_status_badge(t("cv_found_count", ok=cv_ok, total=len(df)), "safe"), unsafe_allow_html=True)


def render_live_send(country: str = "uk", env: dict[str, str | bool] | None = None) -> None:
    env = env or load_env_safe()
    render_page_header("nav_live_send", "page_intro_live_send")
    if not env["auto_send_enabled"]:
        st.markdown(f'<div class="safe-card">{html_mod.escape(t("live_disabled_safe"))}</div>', unsafe_allow_html=True)
        st.button(t("btn_send_live"), disabled=True)
        if st.button(t("go_settings_enable")):
            set_page("settings")
            st.rerun()
        return
    st.markdown(f'<div class="danger-card">{html_mod.escape(t("live_enabled_smtp"))}</div>', unsafe_allow_html=True)
    confirm = st.text_input(t("confirm_send_live"), key="live_confirm")
    limit = st.number_input(t("limit"), min_value=1, max_value=10, value=1, key="live_limit")
    if st.button(t("btn_send_live"), type="primary", disabled=confirm.strip() != LIVE_CONFIRM_PHRASE):
        with st.spinner(t("sending")):
            result = run_cli_command(
                ["send-approved", "--country", country, "--live", "--limit", str(limit)],
                stdin_text="y\n",
            )
        render_terminal_output(result)
    df = load_csv_safe(get_project_root() / "data" / "output" / "send_report.csv")
    if df is not None:
        show_report_table(df, t("report_live_title"))


def render_reports() -> None:
    render_page_header("nav_reports", "page_intro_reports")
    out = get_project_root() / "data" / "output"
    live = load_csv_safe(out / "send_report.csv")
    dry = load_csv_safe(out / "send_report_dry_run.csv")
    if live is not None:
        show_report_table(live, t("report_live_title"))
    else:
        st.info(t("no_live_report"))
    if dry is not None:
        show_report_table(dry, t("report_dry_title"))
    else:
        st.info(t("no_dry_report"))


def render_manual_actions() -> None:
    render_page_header("nav_manual", "page_intro_manual")
    st.markdown(t("mark_sent_help"))
    message_id = st.number_input(t("message_id"), min_value=1, step=1, value=1, key="mark_sent_id")
    if st.button(t("btn_mark_sent")):
        with st.spinner(t("updating_db")):
            result = run_cli_command(["mark-sent", "--message-id", str(int(message_id))])
        render_terminal_output(result)
        if result["returncode"] == 0:
            st.success(t("marked_sent", mid=int(message_id)))


def render_settings() -> None:
    render_page_header("settings_title", "page_intro_settings")
    if not env_file_path().exists():
        st.error(t("env_missing"))
        return
    env = load_env_safe()
    current_auto = bool(env["auto_send_enabled"])
    st.caption(t("secrets_never"))
    sender_email = st.text_input(t("sender_email"), value=get_env_value("SENDER_EMAIL", str(env["sender_email"])))
    sender_name = st.text_input(t("sender_name"), value=get_env_value("SENDER_NAME", str(env["sender_name"])))
    cv_path = st.text_input(t("cv_path"), value=get_env_value("CV_PATH", str(env["cv_path"])))
    daily_limit = st.number_input(
        t("daily_send_limit"),
        min_value=1,
        max_value=100,
        value=int(get_env_value("DAILY_SEND_LIMIT", str(env["daily_send_limit"])) or 10),
    )
    delay_min = st.number_input(
        t("send_delay_min"),
        min_value=1,
        max_value=600,
        value=int(get_env_value("SEND_DELAY_MIN_SECONDS", str(env["send_delay_min"])) or 45),
    )
    delay_max = st.number_input(
        t("send_delay_max"),
        min_value=1,
        max_value=900,
        value=int(get_env_value("SEND_DELAY_MAX_SECONDS", str(env["send_delay_max"])) or 180),
    )
    auto_send_ui = st.toggle(
        t("auto_send_label"),
        value=current_auto,
        help=t("auto_send_help_on") if current_auto else t("auto_send_help_off"),
    )
    enable_confirm = ""
    if auto_send_ui and not current_auto:
        st.markdown(f'<div class="danger-card">{html_mod.escape(t("enable_live_warning"))}</div>', unsafe_allow_html=True)
        enable_confirm = st.text_input(t("enable_live_placeholder"))
        st.caption(t("btn_enable_live"))
    if current_auto and not auto_send_ui:
        st.caption(t("btn_disable_live"))
    if st.button(t("btn_save_settings"), type="primary"):
        if auto_send_ui and not current_auto and enable_confirm.strip() != ENABLE_LIVE_PHRASE:
            st.error(t("invalid_enable_phrase"))
            return
        updates = {
            "SENDER_EMAIL": sender_email.strip(),
            "SENDER_NAME": sender_name.strip(),
            "CV_PATH": cv_path.strip(),
            "DAILY_SEND_LIMIT": str(int(daily_limit)),
            "SEND_DELAY_MIN_SECONDS": str(int(delay_min)),
            "SEND_DELAY_MAX_SECONDS": str(int(delay_max)),
            "AUTO_SEND_ENABLED": "true" if auto_send_ui else "false",
        }
        ok, msg = save_env_safely(updates)
        if ok:
            st.success(t("safe_mode_on") if (current_auto and not auto_send_ui) else t("settings_saved"))
            st.rerun()
        else:
            st.error(t("settings_save_failed", reason=msg))


def render_main_content(env: dict[str, str | bool], repo: Repository | None, country: str) -> None:
    page = st.session_state.get("page", "dashboard")
    if page == "dashboard":
        render_dashboard(env, repo)
    elif page == "drafts":
        render_drafts(country)
    elif page == "generate":
        render_generate()
    elif page == "approve":
        render_approve(country)
    elif page == "dry_run":
        render_dry_run(country)
    elif page == "live_send":
        render_live_send(country, env)
    elif page == "reports":
        render_reports()
    elif page == "manual_actions":
        render_manual_actions()
    elif page == "settings":
        render_settings()
    else:
        render_dashboard(env, repo)


def main() -> None:
    st.set_page_config(page_title="Auto Applyer", layout="wide", initial_sidebar_state="expanded")
    init_session()
    inject_custom_css()
    env = load_env_safe()
    repo = get_repo()
    country = render_sidebar(env)
    render_main_content(env, repo, country)


if __name__ == "__main__":
    main()
