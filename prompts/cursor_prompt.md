# Cursor Prompt: Build Job Outreach Automation System

You are improving a Python project that helps me find, organise and contact companies for junior / graduate software engineering and applied AI roles.

Important:
- This is a quality outreach assistant, not a spam bot.
- Every email must be reviewed manually before sending.
- Do not scrape LinkedIn or violate website terms of service.
- Prioritise CSV imports from Apollo, Hunter, manual research, public company pages, or company career pages.

My profile:
- Adrian Pliego Perez
- Computer Science & AI graduate in the UK
- Backend experience with TypeScript, NestJS, PostgreSQL, REST APIs, RBAC, multi-tenant SaaS CRM
- Projects in ML, anomaly detection, financial ML, automation
- Target roles: backend engineer, software engineer, applied AI engineer, automation engineer, platform/data-adjacent roles
- Target countries: UK and Spain, but design so more countries can be added

Build the project in phases:

1. Improve CLI:
- generate-drafts
- validate-contacts
- export-followups
- mark-sent
- mark-replied

2. Improve database:
tables for companies, contacts, campaigns, messages, interactions.

3. Add country-aware templates:
- UK email
- Spain email
- UK follow-up
- Spain follow-up

4. Company enrichment:
- use public website text safely
- generate short personalised detail
- optional OpenAI integration if OPENAI_API_KEY exists

5. Contact validation:
- validate email format
- optional Hunter API verification if HUNTER_API_KEY exists
- never guess personal emails unless experimental mode is explicitly enabled

6. Lead scoring:
score leads based on role relevance, country, industry, company size, verified email, and personalised detail.

7. Safe sending:
- no auto-send by default
- dry-run mode
- daily limit default 10
- SMTP/Gmail only through environment variables

8. Optional dashboard:
Streamlit dashboard for campaigns, drafts, sent emails, replies, follow-ups, conversion stats.

9. Documentation:
Update README with ethical use, setup, workflow, examples, screenshots placeholders, and how to add UK/Spain campaigns.

Make the code clean, modular and good enough to show as a portfolio project.
