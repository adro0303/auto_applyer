# Auto Applyer

🌍 Idioma: [English](README.md) | Español

## Resumen

Auto Applyer es una herramienta local en Python para automatización segura de outreach laboral. Permite importar leads, generar borradores de email, revisarlos y aprobarlos manualmente, ejecutar simulaciones, enviar correos aprobados por SMTP, ver reportes y gestionar controles de seguridad desde CLI y desde un dashboard local de Streamlit.

Está diseñado para outreach cuidadoso, revisado por humanos y de bajo volumen para roles junior/graduate — no para spam.

## Cómo usar

### Opción recomendada: dashboard visual

La forma más cómoda de usar la herramienta es abrir el dashboard local:

```bash
run_app.bat
```

O también:

```bash
python -m streamlit run src/ui_app.py
```

Desde el dashboard puedes:

1. Revisar configuración y estado de seguridad.
2. Generar borradores desde el CSV de Apollo.
3. Revisar emails generados.
4. Aprobar solo los borradores que quieras enviar.
5. Ejecutar una simulación antes de enviar.
6. Activar o desactivar el envío real desde ajustes.
7. Enviar correos aprobados con confirmación manual.
8. Consultar reportes de envío.

El envío real está protegido: requiere `AUTO_SEND_ENABLED=true` y escribir exactamente `SEND LIVE`.

### Flujo recomendado

1. Coloca el CSV de Apollo en `data/leads/`.
2. Genera los borradores desde el dashboard o CLI.
3. Revisa los emails manualmente.
4. Marca como aprobados solo los contactos buenos.
5. Ejecuta un dry-run.
6. Si todo está correcto, activa el envío real.
7. Envía pocos correos por tanda.
8. Vuelve a desactivar el envío real al terminar.

## Funcionalidades

- Importación de CSV de Apollo
- Limpieza y scoring de leads
- Detección de tipo de contacto
- Generación de emails basada en plantillas
- Flujo de aprobación manual antes de enviar
- Envío SMTP con Gmail App Password
- Reportes de dry-run y envío real
- Manejo de estado SMTP incierto
- Helper `mark-sent`
- Dashboard local Streamlit con UI en inglés/español

## Flujo safety-first

1. Importar leads localmente.
2. Generar borradores y revisarlos manualmente.
3. Aprobar solo los borradores revisados.
4. Ejecutar dry-run antes de cualquier envío real.
5. Activar envío real solo cuando estés listo.
6. En Streamlit, el envío real además requiere escribir `SEND LIVE`.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.cli init-env
```

Copia `.env.example` a `.env` y completa solo valores locales.

## Variables de entorno

Variables principales:

- SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_APP_PASSWORD`
- Remitente: `SENDER_EMAIL`, `SENDER_NAME`
- CV: `CV_PATH`
- Seguridad: `DRY_RUN`, `AUTO_SEND_ENABLED`
- Límites: `DAILY_SEND_LIMIT`, `SEND_DELAY_MIN_SECONDS`, `SEND_DELAY_MAX_SECONDS`
- APIs opcionales: `OPENAI_API_KEY`, `HUNTER_API_KEY`

Nunca subas `.env`, credenciales, API keys, contactos reales, CVs, reportes ni bases de datos locales.

## Uso CLI

```bash
python -m src.cli generate-drafts --country uk --source apollo --source-file data/leads/apollo-contacts-export.csv --min-score 50 --no-enrich --force

python -m src.cli approve-drafts --csv data/output/outreach_drafts_uk.csv

python -m src.cli send-approved --country uk --dry-run --limit 5

python -m src.cli send-approved --country uk --live --limit 1

python -m src.cli mark-sent --message-id 151
```

## Dashboard visual / Streamlit UI

```bash
python -m streamlit run src/ui_app.py
```

o:

```bash
run_app.bat
```

El dashboard funciona de forma local y permite gestionar el flujo completo sin escribir comandos constantemente.

## Acceso directo con icono personalizado

Si quieres abrir la app desde el escritorio con un icono personalizado:

1. Haz clic derecho sobre `run_app.bat`.
2. Selecciona **Crear acceso directo**.
3. Mueve el acceso directo al escritorio.
4. Haz clic derecho sobre el acceso directo.
5. Entra en **Propiedades**.
6. Pulsa **Cambiar icono**.
7. Selecciona el archivo `.ico` que está en la carpeta principal del proyecto.
8. Guarda los cambios.

Importante: el archivo `.bat` no puede tener icono propio directamente. El icono se aplica al acceso directo.

## Estructura del proyecto

```text
auto_applyer/
├── src/
├── tests/
├── prompts/
├── examples/
├── data/        # solo local (gitignored)
├── assets/      # CV local (gitignored)
├── README.md
└── README.es.md
```

## Notas de seguridad

- No subas `.env` ni `.env.backup`
- No subas archivos SQLite, CSV reales, reportes ni CVs
- No expongas credenciales SMTP ni API keys
- Mantén envíos de bajo volumen y con revisión humana
- Usa siempre dry-run antes de envío real

## Descargo de responsabilidad

Este proyecto está pensado para outreach laboral personal, cuidadoso y revisado manualmente. No debe utilizarse para spam, scraping abusivo ni envíos masivos no solicitados.
