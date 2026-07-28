# MG Pakistan — Enterprise Analytics Portal (Streamlit build)

This is the original FastAPI + vanilla-JS prototype rebuilt as a single
Streamlit app so it can deploy directly on **Streamlit Community Cloud**
(or `streamlit run` anywhere) — no separate backend/frontend, no API
server, no JWT layer.

## What changed vs. the FastAPI version

| Original | Streamlit build |
|---|---|
| FastAPI routers + JWT auth | `st.session_state`-based login, one `app.py` |
| `frontend/index.html` (mock data) | Native Streamlit UI, wired to the real DB |
| `python-jose`, `passlib`, `python-multipart`, `uvicorn`, `fastapi` | Dropped — not needed |
| `services/excel_processor.py`, `kpi_engine.py`, `ai_insights.py` | **Unchanged**, just imported directly |
| `models.py` / `database.py` | Same SQLAlchemy models; import paths flattened |
| Reports via `FileResponse` from disk | Reports built in-memory, served via `st.download_button` |

The upload pipeline, KPI calculations, and AI-insights logic are the same
code as before — only the delivery layer (API vs. UI) changed.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Demo logins (password `password123` for all):

| Email | Role | Department |
|---|---|---|
| admin@rd-electronics.pk | admin | — (can view any department) |
| sales@rd-electronics.pk | manager | sales |
| finance@rd-electronics.pk | analyst | finance |

The database, roles, departments, KPI definitions, and demo users are
seeded automatically the first time the app starts (see `seed.py`,
called from `init_db()` in `app.py`).

## Deploy to Streamlit Community Cloud

1. Push this folder to a GitHub repo (root of the repo, or set "Main file
   path" to wherever `app.py` lives).
2. On [share.streamlit.io](https://share.streamlit.io), create a new app
   pointing at that repo/branch and `app.py`.
3. In the app's **Settings → Secrets**, optionally paste:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
   Without it, the AI Insights tab still works using the rule-based
   keyword fallback (same as the original prototype).
4. Deploy.

### About persistence — read this before piloting with real data

Streamlit Community Cloud's filesystem is **ephemeral**: it resets on
redeploy, reboot, or when the app sleeps from inactivity. That means the
bundled SQLite database (`./storage/dev.db`) and any uploaded files will
be wiped periodically. This is fine for a demo/pilot walkthrough, but
**before real users touch it**, point `DATABASE_URL` at a persistent
Postgres instance (e.g. [Neon](https://neon.tech), Supabase, Railway) via
the same Secrets panel:

```toml
DATABASE_URL = "postgresql+psycopg2://user:password@host:5432/dbname"
```

Add `psycopg2-binary` back to `requirements.txt` if you do this — it was
dropped from this build since SQLite has no such dependency.
`models.py` already works against either engine unchanged.

## Project layout

```
app.py                     Streamlit app: login, dashboard, upload, AI, reports
database.py                SQLAlchemy engine/session (SQLite by default)
models.py                  ORM models (unchanged from the original)
auth.py                    Password hashing (bcrypt) — no JWT needed
seed.py                    Idempotent seed data, run on startup
services/
├── excel_processor.py     Upload validation + cleaning (unchanged)
├── kpi_engine.py          Per-department KPI calculations (unchanged)
└── ai_insights.py         Claude call with rule-based fallback (unchanged)
requirements.txt
.streamlit/secrets.toml.example
```

## Before this goes anywhere near production

Same caveats as the original prototype:
- Point `DATABASE_URL` at persistent Postgres (see above)
- Restrict who can create accounts / manage users (there's no admin UI
  for this yet — new users would need to be added via a script)
- Add proper migrations (Alembic) instead of `Base.metadata.create_all`
- Put uploaded files and generated reports in object storage (S3/Azure
  Blob) once persistence matters
- Add audit logging on exports and role changes (the `audit_log` table
  exists in `models.py` but isn't wired up yet)
