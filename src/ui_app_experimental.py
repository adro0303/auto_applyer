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
from urllib.parse import quote

import pandas as pd
import streamlit as st
from dotenv import dotenv_values

from src.config import PROJECT_ROOT, settings
from src.db.repository import Repository
from src.db.schema import init_db

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LIVE_CONFIRM_PHRASE = "SEND LIVE"
ENABLE_LIVE_PHRASE = "ENABLE LIVE"

FORBIDDEN_ENV_KEYS = frozenset(
    {
        "SMTP_APP_PASSWORD",
        "SMTP_PASSWORD",
        "OPENAI_API_KEY",
        "HUNTER_API_KEY",
        "APOLLO_API_KEY",
        "SMTP_USER",
    }
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

# Lucide-style monochrome SVG paths (24x24)
ICON_PATHS: dict[str, str] = {
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "file": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>',
    "wand": '<path d="m15 4-1 1"/><path d="m16 3-1 1"/><path d="M2 20l6-6"/><path d="m22 2-7 7-3-1 1-3 7-7Z"/>',
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="m9 11 3 3L22 4"/>',
    "flask": '<path d="M10 2v7.31"/><path d="M14 2v7.31"/><path d="M8.5 2h7"/><path d="M14 9.3a6.5 6.5 0 1 1-4 0"/><path d="M5.52 16h12.96"/>',
    "send": '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    "chart": '<line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "sliders": '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/>',
    "chevron_left": '<path d="m15 18-6-6 6-6"/>',
    "chevron_right": '<path d="m9 18 6-6-6-6"/>',
}

NAV_ITEMS: list[tuple[str, str, str]] = [
    ("dashboard", "home", "nav_dashboard"),
    ("drafts", "file", "nav_drafts"),
    ("generate", "wand", "nav_generate"),
    ("approve", "check", "nav_approve"),
    ("dry_run", "flask", "nav_dry_run"),
    ("live_send", "send", "nav_live_send"),
    ("reports", "chart", "nav_reports"),
    ("manual_actions", "wrench", "nav_manual"),
    ("settings", "sliders", "nav_settings"),
]

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------

TEXT: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Auto Applyer",
        "app_subtitle": "Local outreach control",
        "nav_dashboard": "Dashboard",
        "nav_drafts": "Drafts",
        "nav_generate": "Generate",
        "nav_approve": "Approve",
        "nav_dry_run": "Dry Run",
        "nav_live_send": "Live Send",
        "nav_reports": "Reports",
        "nav_manual": "Manual Actions",
        "nav_settings": "Settings",
        "collapse_sidebar": "Collapse sidebar",
        "expand_sidebar": "Expand sidebar",
        "language": "Language",
        "lang_en": "English",
        "lang_es": "Español",
        "campaign_country": "Campaign country",
        "secrets_never": "Secrets are never shown in this UI.",
        "live_on": "LIVE ON",
        "live_off": "LIVE OFF",
        "live_enabled": "LIVE SENDING IS ENABLED",
        "live_disabled_safe": "Live sending is disabled. Safe mode.",
        "live_enabled_smtp": "LIVE SENDING IS ENABLED — emails will be sent via SMTP.",
        "metric_sender": "Sender",
        "metric_drafts": "Drafts",
        "metric_approved": "Approved",
        "metric_sent_today": "Sent today",
        "metric_cv": "CV",
        "metric_auto_send": "AUTO_SEND",
        "metric_report": "Latest report",
        "from_env": "from .env",
        "messages_db": "in database",
        "ready_send": "ready to send",
        "live_sends": "live sends today",
        "cv_found": "Found",
        "cv_missing": "Missing",
        "enabled": "ENABLED",
        "disabled": "DISABLED",
        "not_found": "Not found",
        "available": "Available",
        "dry_run_report": "Dry-run",
        "live_report": "Live send",
        "rows": "rows",
        "action_review": "Review Drafts",
        "action_review_sub": "Edit and approve outreach CSV",
        "action_dry_run": "Run Dry-Run",
        "action_dry_run_sub": "Simulate send without SMTP",
        "action_live": "Send Live",
        "action_live_sub": "Requires AUTO_SEND and SEND LIVE",
        "action_reports": "View Reports",
        "action_reports_sub": "Dry-run and live send CSVs",
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
        "approve_selected": "Approve selected",
        "unapprove_selected": "Unapprove selected",
        "save_csv": "Save CSV changes",
        "marked_yes": "Marked {n} row(s) as approved=yes (not saved yet).",
        "marked_no": "Marked {n} row(s) as approved=no (not saved yet).",
        "saved_csv": "Saved to `{name}` with UTF-8 BOM. Review before approve-drafts.",
        "generate_drafts": "Generate Drafts",
        "country": "Country",
        "source_file": "Source file",
        "force_regen": "Force regenerate (--force)",
        "btn_generate": "Generate Drafts",
        "generating": "Generating drafts…",
        "drafts_generated": "Drafts generated. Open **Draft Review** to inspect.",
        "approve_db_title": "Approve Drafts to Database",
        "approve_import_hint": "Imports rows with `approved=yes` from `{path}` into SQLite.",
        "btn_approve_db": "Approve selected drafts",
        "running_approve": "Running approve-drafts…",
        "dry_run_title": "Dry Run",
        "limit": "Limit",
        "btn_dry_run": "Run dry-run",
        "running_dry_run": "Running dry-run (read-only)…",
        "latest_dry_report": "Latest dry-run report",
        "cv_found_count": "CV found: {ok}/{total}",
        "live_send_title": "Live Send",
        "confirm_send_live": 'Type exactly "SEND LIVE" to unlock send button',
        "btn_send_live": "Send live emails",
        "sending": "Sending live emails…",
        "go_settings_enable": "Open Settings to enable live sending",
        "reports_title": "Reports",
        "no_live_report": "No live send report yet.",
        "no_dry_report": "No dry-run report yet.",
        "report_live_title": "send_report.csv (live)",
        "report_dry_title": "send_report_dry_run.csv",
        "manual_title": "Manual Actions",
        "mark_sent_help": "Mark message as sent after checking Gmail Sent (e.g. uncertain 4xx delivery).",
        "message_id": "message_id",
        "btn_mark_sent": "Mark as sent",
        "updating_db": "Updating database…",
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
        "auto_send_help_off": "OFF — safe mode. Live send is blocked.",
        "auto_send_help_on": "ON — live sending allowed (still requires SEND LIVE on send page).",
        "enable_live_warning": "Turning on live sending is dangerous. Type ENABLE LIVE to confirm.",
        "enable_live_placeholder": "Type ENABLE LIVE",
        "btn_save_settings": "Save settings",
        "settings_saved": "Settings saved. Backup: `.env.backup`",
        "settings_save_failed": "Could not save settings: {reason}",
        "safe_mode_on": "Safe mode enabled. AUTO_SEND_ENABLED=false in .env.",
        "env_missing": "No `.env` file found. Run `python -m src.cli init-env` first.",
        "invalid_enable_phrase": 'Type exactly "ENABLE LIVE" to enable live sending.',
        "quick_actions": "Quick actions",
    },
    "es": {
        "app_title": "Auto Applyer",
        "app_subtitle": "Control local de outreach",
        "nav_dashboard": "Panel",
        "nav_drafts": "Borradores",
        "nav_generate": "Generar",
        "nav_approve": "Aprobar",
        "nav_dry_run": "Simulación",
        "nav_live_send": "Envío real",
        "nav_reports": "Informes",
        "nav_manual": "Acciones manuales",
        "nav_settings": "Ajustes",
        "collapse_sidebar": "Contraer barra",
        "expand_sidebar": "Expandir barra",
        "language": "Idioma",
        "lang_en": "English",
        "lang_es": "Español",
        "campaign_country": "País de campaña",
        "secrets_never": "Los secretos nunca se muestran en esta interfaz.",
        "live_on": "ENVÍO ACTIVO",
        "live_off": "ENVÍO OFF",
        "live_enabled": "EL ENVÍO REAL ESTÁ ACTIVADO",
        "live_disabled_safe": "El envío real está desactivado. Modo seguro.",
        "live_enabled_smtp": "EL ENVÍO REAL ESTÁ ACTIVADO — se enviarán correos por SMTP.",
        "metric_sender": "Remitente",
        "metric_drafts": "Borradores",
        "metric_approved": "Aprobados",
        "metric_sent_today": "Enviados hoy",
        "metric_cv": "CV",
        "metric_auto_send": "AUTO_SEND",
        "metric_report": "Último informe",
        "from_env": "desde .env",
        "messages_db": "en BD",
        "ready_send": "listos para enviar",
        "live_sends": "envíos reales hoy",
        "cv_found": "Encontrado",
        "cv_missing": "No encontrado",
        "enabled": "ACTIVADO",
        "disabled": "DESACTIVADO",
        "not_found": "No encontrado",
        "available": "Disponible",
        "dry_run_report": "Simulación",
        "live_report": "Envío real",
        "rows": "filas",
        "action_review": "Revisar borradores",
        "action_review_sub": "Editar y aprobar el CSV",
        "action_dry_run": "Ejecutar simulación",
        "action_dry_run_sub": "Simular sin SMTP",
        "action_live": "Envío real",
        "action_live_sub": "Requiere AUTO_SEND y SEND LIVE",
        "action_reports": "Ver informes",
        "action_reports_sub": "CSV de simulación y envío real",
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
        "approve_selected": "Aprobar seleccionados",
        "unapprove_selected": "Desaprobar seleccionados",
        "save_csv": "Guardar cambios CSV",
        "marked_yes": "Marcados {n} como approved=yes (sin guardar aún).",
        "marked_no": "Marcados {n} como approved=no (sin guardar aún).",
        "saved_csv": "Guardado en `{name}` con UTF-8 BOM. Revisa antes de approve-drafts.",
        "generate_drafts": "Generar borradores",
        "country": "País",
        "source_file": "Archivo origen",
        "force_regen": "Forzar regeneración (--force)",
        "btn_generate": "Generar borradores",
        "generating": "Generando borradores…",
        "drafts_generated": "Borradores generados. Abre **Revisión de borradores**.",
        "approve_db_title": "Aprobar borradores en la base de datos",
        "approve_import_hint": "Importa filas con `approved=yes` desde `{path}` a SQLite.",
        "btn_approve_db": "Aprobar borradores seleccionados",
        "running_approve": "Ejecutando approve-drafts…",
        "dry_run_title": "Simulación (dry-run)",
        "limit": "Límite",
        "btn_dry_run": "Ejecutar simulación",
        "running_dry_run": "Ejecutando simulación (solo lectura)…",
        "latest_dry_report": "Último informe de simulación",
        "cv_found_count": "CV encontrado: {ok}/{total}",
        "live_send_title": "Envío real",
        "confirm_send_live": 'Escribe exactamente "SEND LIVE" para desbloquear el envío',
        "btn_send_live": "Enviar correos en vivo",
        "sending": "Enviando correos en vivo…",
        "go_settings_enable": "Abrir Ajustes para activar el envío real",
        "reports_title": "Informes",
        "no_live_report": "Aún no hay informe de envío real.",
        "no_dry_report": "Aún no hay informe de simulación.",
        "report_live_title": "send_report.csv (real)",
        "report_dry_title": "send_report_dry_run.csv",
        "manual_title": "Acciones manuales",
        "mark_sent_help": "Marcar mensaje como enviado tras verificar en Gmail Sent (p. ej. 4xx uncertain).",
        "message_id": "message_id",
        "btn_mark_sent": "Marcar como enviado",
        "updating_db": "Actualizando base de datos…",
        "marked_sent": "Mensaje {mid} marcado como enviado.",
        "command": "Comando",
        "output": "Salida",
        "no_output": "(sin salida)",
        "no_report_data": "Sin datos en el informe.",
        "uncertain_warning": "Algunos correos quedaron en estado **uncertain**. Revisa Gmail Sent antes de reintentar.",
        "failed_sends": "Envíos fallidos detectados:",
        "exit_code": "código de salida",
        "settings_title": "Ajustes",
        "settings_subtitle": "Ajustes operativos en `.env` (los secretos no se editan aquí).",
        "sender_email": "SENDER_EMAIL",
        "sender_name": "SENDER_NAME",
        "cv_path": "CV_PATH",
        "daily_send_limit": "DAILY_SEND_LIMIT",
        "send_delay_min": "SEND_DELAY_MIN_SECONDS",
        "send_delay_max": "SEND_DELAY_MAX_SECONDS",
        "auto_send_label": "AUTO_SEND_ENABLED",
        "auto_send_help_off": "OFF — modo seguro. El envío real está bloqueado.",
        "auto_send_help_on": "ON — envío real permitido (sigue requiriendo SEND LIVE en la página de envío).",
        "enable_live_warning": "Activar el envío real es peligroso. Escribe ENABLE LIVE para confirmar.",
        "enable_live_placeholder": "Escribe ENABLE LIVE",
        "btn_save_settings": "Guardar ajustes",
        "settings_saved": "Ajustes guardados. Copia: `.env.backup`",
        "settings_save_failed": "No se pudieron guardar los ajustes: {reason}",
        "safe_mode_on": "Modo seguro activado. AUTO_SEND_ENABLED=false en .env.",
        "env_missing": "No hay archivo `.env`. Ejecuta `python -m src.cli init-env` primero.",
        "invalid_enable_phrase": 'Escribe exactamente "ENABLE LIVE" para activar el envío real.',
        "quick_actions": "Acciones rápidas",
    },
}


# ---------------------------------------------------------------------------
# Session & i18n
# ---------------------------------------------------------------------------


def init_session() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "language" not in st.session_state:
        st.session_state.language = "en"
    if "sidebar_collapsed" not in st.session_state:
        st.session_state.sidebar_collapsed = False
    if "campaign_country" not in st.session_state:
        st.session_state.campaign_country = "uk"


def t(key: str, **kwargs: Any) -> str:
    lang = st.session_state.get("language", "en")
    template = TEXT.get(lang, TEXT["en"]).get(key, TEXT["en"].get(key, key))
    return template.format(**kwargs) if kwargs else template


def set_page(page_name: str) -> None:
    st.session_state.page = page_name


# ---------------------------------------------------------------------------
# .env helpers (safe editing)
# ---------------------------------------------------------------------------


def env_file_path() -> Path:
    return get_project_root() / ".env"


def load_env_lines() -> list[str]:
    path = env_file_path()
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def _parse_env_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    return stripped.split("=", 1)[0].strip()


def get_env_value(key: str, default: str = "") -> str:
    raw = dotenv_values(env_file_path()) if env_file_path().exists() else {}
    val = raw.get(key)
    if val is None:
        return default
    return str(val)


def update_env_value(lines: list[str], key: str, value: str) -> list[str]:
    if key in FORBIDDEN_ENV_KEYS:
        raise ValueError(f"Forbidden key: {key}")
    if key not in ALLOWED_ENV_KEYS:
        raise ValueError(f"Key not allowed in UI: {key}")

    seen = False
    out: list[str] = []
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")

    for line in lines:
        if pattern.match(line):
            out.append(f"{key}={value}\n")
            seen = True
        else:
            out.append(line if line.endswith("\n") else line + "\n")

    if not seen:
        if out and not out[-1].endswith("\n"):
            out[-1] = out[-1] + "\n"
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


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def get_project_root() -> Path:
    return PROJECT_ROOT


def icon_data_uri(name: str) -> str:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="%2394a3b8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'{ICON_PATHS.get(name, ICON_PATHS["home"])}</svg>'
    )
    return f"data:image/svg+xml,{quote(svg)}"


def load_env_safe() -> dict[str, str | bool]:
    raw: dict[str, str | None] = {}
    if env_file_path().exists():
        raw = dotenv_values(env_file_path())

    auto = str(raw.get("AUTO_SEND_ENABLED", os.getenv("AUTO_SEND_ENABLED", "false"))).lower()
    return {
        "sender_email": (
            raw.get("SENDER_EMAIL") or raw.get("YOUR_EMAIL") or settings.sender_email or "—"
        ),
        "sender_name": raw.get("SENDER_NAME") or settings.sender_name or "",
        "cv_path": raw.get("CV_PATH") or settings.cv_path,
        "daily_send_limit": raw.get("DAILY_SEND_LIMIT") or str(settings.daily_send_limit),
        "send_delay_min": raw.get("SEND_DELAY_MIN_SECONDS") or str(settings.send_delay_min_seconds),
        "send_delay_max": raw.get("SEND_DELAY_MAX_SECONDS") or str(settings.send_delay_max_seconds),
        "auto_send_enabled": auto in {"1", "true", "yes", "on"},
    }


def run_cli_command(args: list[str], stdin_text: str | None = None) -> dict[str, Any]:
    root = get_project_root()
    cmd = [sys.executable, "-m", "src.cli", *args]
    result = subprocess.run(
        cmd,
        cwd=str(root),
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
    result_col = "result" if "result" in df.columns else None
    counts: dict[str, int] = {}
    if result_col:
        counts = df[result_col].value_counts().to_dict()
    return {
        "exists": True,
        "path": str(path),
        "rows": len(df),
        "counts": counts,
        "latest": df.iloc[-1].to_dict() if len(df) else {},
    }


def render_status_badge(label: str, kind: str = "neutral") -> str:
    colors = {
        "safe": ("#10b981", "#064e3b"),
        "sent": ("#10b981", "#064e3b"),
        "warning": ("#fbbf24", "#78350f"),
        "dry_run": ("#fbbf24", "#78350f"),
        "uncertain": ("#f97316", "#7c2d12"),
        "danger": ("#ef4444", "#7f1d1d"),
        "error": ("#ef4444", "#7f1d1d"),
        "neutral": ("#94a3b8", "#1e293b"),
        "info": ("#60a5fa", "#1e3a5f"),
    }
    fg, bg = colors.get(kind, colors["neutral"])
    return (
        f'<span style="display:inline-block;padding:0.25rem 0.65rem;border-radius:999px;'
        f'font-size:0.78rem;font-weight:600;color:{fg};background:{bg};'
        f'border:1px solid {fg}33;margin:0.15rem;">{html_mod.escape(label)}</span>'
    )


def render_metric_card(
    title: str, value: str | int, subtitle: str = "", accent: str = "#6366f1", truncate: bool = False
) -> str:
    value_class = "metric-value truncate" if truncate else "metric-value"
    return f"""
    <div class="metric-card" style="border-top:3px solid {accent};">
        <span class="metric-label">{html_mod.escape(str(title))}</span>
        <span class="{value_class}" title="{html_mod.escape(str(value))}">{html_mod.escape(str(value))}</span>
        <span class="metric-sub">{html_mod.escape(str(subtitle))}</span>
    </div>
    """


def build_nav_button_css() -> str:
    rules: list[str] = []
    for page_id, icon_key, _ in NAV_ITEMS:
        uri = icon_data_uri(icon_key)
        rules.append(
            f"""
            .app-shell .nav-{page_id} div[data-testid="stButton"] > button {{
                background-image: url("{uri}");
                background-repeat: no-repeat;
                background-position: 14px center;
                background-size: 18px 18px;
                padding-left: 44px !important;
                text-align: left;
                justify-content: flex-start;
            }}
            .app-shell.sidebar-collapsed .nav-{page_id} div[data-testid="stButton"] > button {{
                background-position: center;
                padding-left: 0 !important;
                font-size: 0 !important;
                color: transparent !important;
                min-width: 44px;
                width: 44px;
                margin: 0 auto;
            }}
            .app-shell .nav-{page_id} div[data-testid="stButton"] > button[kind="primary"] {{
                filter: brightness(1.15);
            }}
            """
        )
    return "\n".join(rules)


def inject_custom_css(collapsed: bool) -> None:
    shell_class = "sidebar-collapsed" if collapsed else "sidebar-expanded"
    sidebar_width = "72px" if collapsed else "260px"
    main_pad = "84px" if collapsed else "272px"
    toggle_icon = "chevron_right" if collapsed else "chevron_left"
    toggle_uri = icon_data_uri(toggle_icon)

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
        .stApp {{
            background: linear-gradient(160deg, #070b14 0%, #0d1117 40%, #0a0f1a 100%);
            color: #e2e8f0;
        }}
        section[data-testid="stSidebar"] {{ display: none !important; }}
        [data-testid="collapsedControl"] {{ display: none !important; }}
        section.main > div.block-container {{
            padding-left: {main_pad};
            padding-top: 1rem;
            max-width: 100%;
        }}
        div[data-testid="stHorizontalBlock"]:has(div.app-shell) > div[data-testid="column"]:first-child {{
            position: fixed !important;
            left: 0 !important;
            top: 0 !important;
            width: {sidebar_width} !important;
            min-width: {sidebar_width} !important;
            max-width: {sidebar_width} !important;
            flex: 0 0 {sidebar_width} !important;
            height: 100vh !important;
            z-index: 999 !important;
            background: linear-gradient(180deg, #0b1220 0%, #111827 100%) !important;
            border-right: 1px solid #1e293b !important;
            padding: 0.75rem 0.5rem !important;
            overflow-y: auto !important;
            box-shadow: 4px 0 24px rgba(0,0,0,0.35);
        }}
        div[data-testid="stHorizontalBlock"]:has(div.app-shell) > div[data-testid="column"]:last-child {{
            width: calc(100% - {sidebar_width}) !important;
        }}
        .app-shell {{ display: none; height: 0; }}
        .sidebar-brand {{
            font-size: 1.05rem;
            font-weight: 700;
            color: #f1f5f9;
            padding: 0.25rem 0.5rem 0.75rem;
            letter-spacing: -0.02em;
        }}
        .sidebar-brand small {{
            display: block;
            font-size: 0.72rem;
            font-weight: 500;
            color: #64748b;
            margin-top: 0.15rem;
        }}
        .sidebar-status {{
            padding: 0.5rem 0.6rem;
            margin: 0.35rem 0 0.75rem;
            border-radius: 10px;
            background: #0f172a;
            border: 1px solid #1e293b;
            font-size: 0.75rem;
            color: #94a3b8;
        }}
        .nav-toggle-wrap div[data-testid="stButton"] > button {{
            background: #1e293b url("{toggle_uri}") center center no-repeat !important;
            background-size: 18px 18px !important;
            border: 1px solid #334155 !important;
            min-width: 44px !important;
            min-height: 40px !important;
            padding: 0.35rem !important;
            font-size: 0 !important;
            color: transparent !important;
        }}
        .nav-row {{ margin-bottom: 0.15rem; }}
        .nav-row div[data-testid="stButton"] > button {{
            width: 100%;
            border-radius: 10px !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            color: #cbd5e1 !important;
            font-weight: 500 !important;
            min-height: 44px;
        }}
        .nav-row div[data-testid="stButton"] > button:hover {{
            background: #1e293b !important;
            border-color: #334155 !important;
        }}
        .nav-row div[data-testid="stButton"] > button[kind="primary"] {{
            background: linear-gradient(135deg, #2563eb55, #7c3aed55) !important;
            border: 1px solid #6366f1 !important;
            color: #f8fafc !important;
            box-shadow: 0 2px 12px rgba(99, 102, 241, 0.25);
        }}
        .page-header {{
            margin-bottom: 1.25rem;
        }}
        .page-header h1 {{
            color: #f8fafc;
            font-size: 1.65rem;
            font-weight: 700;
            margin: 0;
        }}
        .page-header p {{
            color: #94a3b8;
            margin: 0.35rem 0 0;
            font-size: 0.92rem;
        }}
        .card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 1.25rem 1.35rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 24px rgba(0,0,0,0.35);
        }}
        .card-title {{ font-size: 1.05rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.75rem; }}
        .action-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 1.1rem 1.2rem;
            min-height: 110px;
            transition: border-color 0.2s;
        }}
        .action-card:hover {{ border-color: #6366f1; }}
        .action-card h3 {{ margin: 0; font-size: 1rem; color: #f1f5f9; }}
        .action-card p {{ margin: 0.35rem 0 0; font-size: 0.82rem; color: #94a3b8; }}
        .metric-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 14px;
            padding: 1rem 1.1rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            min-height: 96px;
        }}
        .metric-label {{ display:block; font-size:0.72rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.04em; }}
        .metric-value {{ display:block; font-size:1.45rem; font-weight:700; color:#f8fafc; margin:0.25rem 0; }}
        .metric-value.truncate {{
            font-size: 1rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
        }}
        .metric-sub {{ display:block; font-size:0.78rem; color:#64748b; }}
        .danger-card {{
            background: linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%);
            border: 2px solid #ef4444;
            border-radius: 14px;
            padding: 1.25rem;
            margin: 1rem 0;
            color: #fecaca;
            font-weight: 600;
            text-align: center;
            font-size: 1.05rem;
            box-shadow: 0 0 24px rgba(239,68,68,0.3);
        }}
        .safe-card {{
            background: #052e16;
            border: 1px solid #10b981;
            border-radius: 14px;
            padding: 1rem;
            color: #6ee7b7;
            margin: 0.75rem 0;
        }}
        .terminal-box {{
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
        }}
        .stButton > button {{
            border-radius: 10px !important;
            font-weight: 600 !important;
            border: 1px solid #30363d !important;
        }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #2563eb, #7c3aed) !important;
            border: none !important;
            color: white !important;
        }}
        .live-section {{
            border: 2px solid #ef4444;
            border-radius: 16px;
            padding: 1.25rem;
            background: rgba(127,29,29,0.15);
            margin-top: 1rem;
        }}
        {build_nav_button_css()}
        </style>
        <div class="app-shell {shell_class}"></div>
        """,
        unsafe_allow_html=True,
    )


def render_terminal_output(result: dict[str, Any]) -> None:
    st.markdown(
        f'<div class="card"><span class="metric-label">{html_mod.escape(t("command"))}</span><br>'
        f'<code>{html_mod.escape(result["cmd"])}</code></div>',
        unsafe_allow_html=True,
    )
    box = result.get("output") or t("no_output")
    rc = result.get("returncode", 0)
    prefix = f'{t("exit_code")}: {rc}\n\n'
    st.markdown(
        f'<span class="metric-label">{html_mod.escape(t("output"))}</span>'
        f'<div class="terminal-box">{html_mod.escape(prefix + box)}</div>',
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


def show_report_table(df: pd.DataFrame, title: str) -> None:
    st.markdown(f'<div class="card-title">{html_mod.escape(title)}</div>', unsafe_allow_html=True)
    if df is None or df.empty:
        st.warning(t("no_report_data"))
        return
    if "result" in df.columns:
        styled = df.style.map(highlight_result, subset=["result"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    if "result" in df.columns:
        if (df["result"] == "uncertain").any():
            st.warning(t("uncertain_warning"))
        failed = df[df["result"] == "failed"]
        if not failed.empty and "error" in failed.columns:
            st.error(t("failed_sends"))
            for _, row in failed.iterrows():
                st.markdown(f"- **{row.get('email', '?')}**: {row.get('error', 'unknown')}")


def render_page_header(title_key: str, subtitle_key: str | None = None) -> None:
    sub = f"<p>{html_mod.escape(t(subtitle_key))}</p>" if subtitle_key else ""
    st.markdown(
        f'<div class="page-header"><h1>{html_mod.escape(t(title_key))}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Navigation sidebar
# ---------------------------------------------------------------------------


def render_app_sidebar(env: dict[str, str | bool]) -> None:
    collapsed = st.session_state.sidebar_collapsed
    toggle_icon = "chevron_left" if not collapsed else "chevron_right"
    toggle_help = t("collapse_sidebar") if not collapsed else t("expand_sidebar")

    st.markdown('<div class="nav-toggle-wrap">', unsafe_allow_html=True)
    if st.button(
        " ",
        key="sidebar_toggle",
        help=toggle_help,
        use_container_width=not collapsed,
    ):
        st.session_state.sidebar_collapsed = not collapsed
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if not collapsed:
        st.markdown(
            f'<div class="sidebar-brand">{html_mod.escape(t("app_title"))}'
            f"<small>{html_mod.escape(t('app_subtitle'))}</small></div>",
            unsafe_allow_html=True,
        )

    live_kind = "danger" if env["auto_send_enabled"] else "safe"
    live_label = t("live_on") if env["auto_send_enabled"] else t("live_off")
    if not collapsed:
        st.markdown(
            f'<div class="sidebar-status">'
            f'{render_status_badge(live_label, live_kind)}'
            f'<div style="margin-top:0.45rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'
            f'{html_mod.escape(str(env["sender_email"])[:36])}</div></div>',
            unsafe_allow_html=True,
        )

    current = st.session_state.get("page", "dashboard")
    for page_id, _icon_key, label_key in NAV_ITEMS:
        is_active = current == page_id
        label = " " if collapsed else t(label_key)
        st.markdown(f'<div class="nav-row nav-{page_id}">', unsafe_allow_html=True)
        if st.button(
            label,
            key=f"nav_{page_id}",
            help=t(label_key) if collapsed else None,
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            set_page(page_id)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def render_dashboard(env: dict[str, str | bool], repo: Repository | None) -> None:
    render_page_header("nav_dashboard")

    cv_path = get_project_root() / str(env["cv_path"]) if env["cv_path"] else settings.cv_file
    cv_exists = cv_path.exists()
    stats = repo.stats() if repo else {}
    sent_today = repo.count_sent_today() if repo else 0
    dry_report = report_summary(settings.data_output_dir / "send_report_dry_run.csv")
    live_report = report_summary(settings.data_output_dir / "send_report.csv")

    if env["auto_send_enabled"]:
        st.markdown(
            f'<div class="danger-card">{html_mod.escape(t("live_enabled"))}</div>',
            unsafe_allow_html=True,
        )

    sender_display = str(env["sender_email"])
    if len(sender_display) > 32:
        sender_display = sender_display[:29] + "..."

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            render_metric_card(
                t("metric_sender"), sender_display, t("from_env"), "#60a5fa", truncate=True
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            render_metric_card(t("metric_cv"), t("cv_found") if cv_exists else t("cv_missing"), "", "#10b981"),
            unsafe_allow_html=True,
        )
    with c3:
        auto_label = t("enabled") if env["auto_send_enabled"] else t("disabled")
        st.markdown(
            render_metric_card(
                t("metric_auto_send"),
                auto_label,
                "",
                "#ef4444" if env["auto_send_enabled"] else "#10b981",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        report_label = t("not_found")
        if live_report.get("exists"):
            report_label = f"{t('live_report')} ({live_report['rows']})"
        elif dry_report.get("exists"):
            report_label = f"{t('dry_run_report')} ({dry_report['rows']})"
        st.markdown(
            render_metric_card(t("metric_report"), report_label, "", "#a855f7"),
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

    st.markdown(
        f'<div class="card-title" style="margin-top:0.5rem;">{html_mod.escape(t("quick_actions"))}</div>',
        unsafe_allow_html=True,
    )
    a1, a2, a3, a4 = st.columns(4)
    actions = [
        (a1, "drafts", "action_review", "action_review_sub"),
        (a2, "dry_run", "action_dry_run", "action_dry_run_sub"),
        (a3, "live_send", "action_live", "action_live_sub"),
        (a4, "reports", "action_reports", "action_reports_sub"),
    ]
    for col, page, title_k, sub_k in actions:
        with col:
            st.markdown(
                f'<div class="action-card"><h3>{html_mod.escape(t(title_k))}</h3>'
                f'<p>{html_mod.escape(t(sub_k))}</p></div>',
                unsafe_allow_html=True,
            )
            if st.button(t(title_k), key=f"dash_go_{page}", use_container_width=True):
                set_page(page)
                st.rerun()


def render_drafts(country: str = "uk") -> None:
    render_page_header("draft_review")
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
        types = (
            [t("all")] + sorted(df["contact_type"].dropna().unique().tolist())
            if "contact_type" in df.columns
            else [t("all")]
        )
        type_f = st.selectbox(t("contact_type"), types, key="filter_type")
    with col_f3:
        appr_f = st.selectbox(t("approved_filter"), [t("all"), "yes", "no"], key="filter_approved")
    with col_f4:
        st.number_input(t("min_score"), min_value=0, max_value=100, value=0, key="filter_score")

    filtered = df.copy()
    min_score = st.session_state.get("filter_score", 0)
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
        for c in [
            "message_id",
            "company",
            "name",
            "email",
            "contact_type",
            "lead_score",
            "subject",
            "approved",
            "status",
        ]
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
    render_page_header("generate_drafts")
    country = st.selectbox(t("country"), ["uk", "spain"], index=0, key="gen_country")
    source_file = st.text_input(
        t("source_file"),
        value="data/leads/apollo-contacts-export.csv",
        key="gen_source",
    )
    min_score = st.number_input(t("min_score"), min_value=0, max_value=100, value=50, key="gen_min_score")
    force = st.checkbox(t("force_regen"), value=False, key="gen_force")

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
        if result["returncode"] == 0:
            st.session_state.pop("drafts_df", None)
            st.success(t("drafts_generated"))


def render_approve(country: str = "uk") -> None:
    render_page_header("approve_db_title")
    csv_path = f"data/output/outreach_drafts_{country}.csv"
    st.caption(t("approve_import_hint", path=csv_path))
    if st.button(t("btn_approve_db"), type="primary"):
        with st.spinner(t("running_approve")):
            result = run_cli_command(["approve-drafts", "--csv", csv_path])
        render_terminal_output(result)


def render_dry_run(country: str = "uk") -> None:
    render_page_header("dry_run_title")
    limit = st.number_input(t("limit"), min_value=1, max_value=50, value=5, key="dry_limit")
    if st.button(t("btn_dry_run"), type="primary"):
        with st.spinner(t("running_dry_run")):
            result = run_cli_command(
                ["send-approved", "--country", country, "--dry-run", "--limit", str(limit)]
            )
        render_terminal_output(result)

    report_path = get_project_root() / "data" / "output" / "send_report_dry_run.csv"
    df = load_csv_safe(report_path)
    if df is not None:
        show_report_table(df, t("latest_dry_report"))
        if "cv_attachment" in df.columns:
            cv_ok = (df["cv_attachment"] == "found").sum()
            st.markdown(
                render_status_badge(
                    t("cv_found_count", ok=cv_ok, total=len(df)),
                    "safe" if cv_ok else "warning",
                ),
                unsafe_allow_html=True,
            )


def render_live_send(country: str = "uk", env: dict[str, str | bool] | None = None) -> None:
    env = env or load_env_safe()
    render_page_header("live_send_title")

    if not env["auto_send_enabled"]:
        st.markdown(
            f'<div class="safe-card">{html_mod.escape(t("live_disabled_safe"))}</div>',
            unsafe_allow_html=True,
        )
        st.button(t("btn_send_live"), disabled=True)
        if st.button(t("go_settings_enable"), type="primary"):
            set_page("settings")
            st.rerun()
        return

    st.markdown(
        f'<div class="danger-card">{html_mod.escape(t("live_enabled_smtp"))}</div>',
        unsafe_allow_html=True,
    )
    confirm = st.text_input(t("confirm_send_live"), key="live_confirm")
    limit = st.number_input(t("limit"), min_value=1, max_value=10, value=1, key="live_limit")
    unlocked = confirm.strip() == LIVE_CONFIRM_PHRASE

    if st.button(t("btn_send_live"), type="primary", disabled=not unlocked):
        with st.spinner(t("sending")):
            result = run_cli_command(
                ["send-approved", "--country", country, "--live", "--limit", str(limit)],
                stdin_text="y\n",
            )
        render_terminal_output(result)

    report_path = get_project_root() / "data" / "output" / "send_report.csv"
    df = load_csv_safe(report_path)
    if df is not None:
        show_report_table(df, t("report_live_title"))


def render_reports() -> None:
    render_page_header("reports_title")
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
    render_page_header("manual_title")
    st.markdown(t("mark_sent_help"))
    message_id = st.number_input(t("message_id"), min_value=1, step=1, value=1, key="mark_sent_id")
    if st.button(t("btn_mark_sent")):
        with st.spinner(t("updating_db")):
            result = run_cli_command(["mark-sent", "--message-id", str(int(message_id))])
        render_terminal_output(result)
        if result["returncode"] == 0:
            st.success(t("marked_sent", mid=int(message_id)))


def render_settings() -> None:
    render_page_header("settings_title", "settings_subtitle")

    if not env_file_path().exists():
        st.error(t("env_missing"))
        return

    env = load_env_safe()
    current_auto = bool(env["auto_send_enabled"])

    lang_choice = st.selectbox(
        t("language"),
        options=["en", "es"],
        format_func=lambda code: t("lang_en") if code == "en" else t("lang_es"),
        index=0 if st.session_state.language == "en" else 1,
        key="settings_language",
    )
    if lang_choice != st.session_state.language:
        st.session_state.language = lang_choice
        st.rerun()

    country = st.selectbox(
        t("campaign_country"),
        ["uk", "spain"],
        index=0 if st.session_state.campaign_country == "uk" else 1,
        key="settings_country",
    )
    st.session_state.campaign_country = country

    st.caption(t("secrets_never"))

    sender_email = st.text_input(t("sender_email"), value=get_env_value("SENDER_EMAIL", env["sender_email"]))
    sender_name = st.text_input(t("sender_name"), value=get_env_value("SENDER_NAME", env["sender_name"]))
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
        key="settings_auto_send_toggle",
    )

    enable_confirm = ""
    if auto_send_ui and not current_auto:
        st.markdown(
            f'<div class="danger-card">{html_mod.escape(t("enable_live_warning"))}</div>',
            unsafe_allow_html=True,
        )
        enable_confirm = st.text_input(t("enable_live_placeholder"), key="enable_live_confirm")

    if st.button(t("btn_save_settings"), type="primary"):
        if auto_send_ui and not current_auto:
            if enable_confirm.strip() != ENABLE_LIVE_PHRASE:
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
            if not auto_send_ui and current_auto:
                st.success(t("safe_mode_on"))
            else:
                st.success(t("settings_saved"))
            st.rerun()
        else:
            st.error(t("settings_save_failed", reason=msg))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


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
    st.set_page_config(
        page_title="Auto Applyer",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_session()
    inject_custom_css(st.session_state.sidebar_collapsed)

    env = load_env_safe()
    repo = get_repo()
    country = st.session_state.campaign_country

    side_col, main_col = st.columns([0.14, 0.86], gap="small")
    with side_col:
        render_app_sidebar(env)
    with main_col:
        render_main_content(env, repo, country)


if __name__ == "__main__":
    main()
