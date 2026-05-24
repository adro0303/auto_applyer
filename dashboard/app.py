"""Streamlit dashboard: streamlit run dashboard/app.py"""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import settings
from src.db.repository import Repository
from src.db.schema import init_db

st.set_page_config(page_title="Job Outreach Dashboard", layout="wide")
st.title("Job Outreach Assistant")
st.caption("Review and approve drafts in CSV/CLI before sending. No auto-send by default.")

init_db(settings.db_path)
repo = Repository(settings.db_path)
stats = repo.stats()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Contacts", stats["total_contacts"])
col2.metric("Drafts", stats["drafts"])
col3.metric("Approved", stats.get("approved", 0))
col4.metric("Sent", stats["sent"])
col5.metric("Replied", stats["replied"])
col6.metric("Follow-up drafts", stats["followup_drafts"])

if stats["sent"]:
    conversion = round(100 * stats["replied"] / max(stats["sent"], 1), 1)
    st.metric("Reply rate (approx.)", f"{conversion}%")

tab_drafts, tab_contacts, tab_files = st.tabs(["Draft messages", "Contacts", "CSV exports"])

with tab_drafts:
    with repo.connect() as conn:
        df = pd.read_sql_query(
            """
            SELECT m.id, co.name AS company, c.name, c.email, c.country,
                   m.message_type, m.status, m.subject, m.created_at
            FROM messages m
            JOIN contacts c ON c.id = m.contact_id
            JOIN companies co ON co.id = c.company_id
            ORDER BY m.created_at DESC
            LIMIT 200
            """,
            conn,
        )
    st.dataframe(df, use_container_width=True)

with tab_contacts:
    contacts = repo.fetch_all_contacts()
    st.dataframe(pd.DataFrame(contacts), use_container_width=True)

with tab_files:
    out = settings.data_output_dir
    if out.exists():
        for f in sorted(out.glob("*.csv")):
            st.subheader(f.name)
            st.dataframe(pd.read_csv(f), use_container_width=True)
    else:
        st.info("No exports yet. Run generate-drafts first.")

st.sidebar.markdown("### Ethical use")
st.sidebar.markdown(
    "- Review every email manually\n"
    "- Do not scrape LinkedIn\n"
    "- Respect website ToS\n"
    "- Start with ~10 emails/day"
)
