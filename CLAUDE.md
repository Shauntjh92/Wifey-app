# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Start the stack
```bash
# 1. Database (must be first)
docker-compose up -d

# 2. Backend — run from backend/
cd backend
.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000

# 3. Frontend — run from frontend/
cd frontend
npm run dev                               # http://localhost:5173
```

### Backend
```bash
cd backend
.venv/bin/pip install -r requirements.txt          # install deps into venv
.venv/bin/python -c "from app.main import app"     # quick import check

# Alembic migrations (run from backend/)
.venv/bin/alembic revision --autogenerate -m "description"
.venv/bin/alembic upgrade head
```

### Frontend
```bash
cd frontend
npm install
npm run build    # production build (output: dist/)
```

### Database
```bash
docker-compose up -d      # start postgres on :5432
docker-compose down       # stop and remove container (data volume persists)

# Seed test data without OpenAI credits
cd backend && .venv/bin/python3 -c "..."   # see README for seed script
```

## Architecture

The app has three layers that must all be running: PostgreSQL (Docker), FastAPI backend, and React frontend.

### Data flow

**Data gathering** (one-time, admin-triggered):
1. `POST /api/data/gather` kicks off a FastAPI `BackgroundTask` in `services/data_gatherer.py`
2. The job scrapes three sources (no OpenAI cost):
   - **singmalls.app/en/malls** — full mall list from `pageProps.sites` in the embedded `__NEXT_DATA__` JSON
   - **singmalls.app/en/malls/{slug}/directory** — per-mall store directory from `pageProps.merchants`
   - **Wikipedia List_of_shopping_malls_in_Singapore** — region mapping (Central/East/North/North-East/West); falls back to postal-code prefix if a mall isn't listed
3. Results are upserted into PostgreSQL via SQLAlchemy. Stores are deduplicated by `normalized_name` (lowercased, punctuation stripped). Progress is tracked in a module-level `_job_state` dict (single-process only).
4. `GET /api/data/status` polls this dict — the Admin page polls it every 2 seconds.
5. Gather takes ~3 minutes for all ~106 malls (1 s polite delay per mall).

**Search** (per user query):
1. `POST /api/search` with `{"stores": ["Uniqlo", "Starbaks"]}` hits `services/store_matcher.py`
2. All store names are fetched from DB, then a single `gpt-4o` call fuzzy-matches user input to DB entries (handles typos/aliases). Falls back to exact normalized match if OpenAI is unavailable.
3. A SQL query finds all `mall_stores` rows matching the resolved store IDs, groups by mall, sorts by match count descending.

**Frontend proxy**: Vite dev server proxies `/api/*` → `http://localhost:8000`, so all fetch calls use relative `/api/...` paths with no CORS concerns during development.

### Key files

| File | Purpose |
|------|---------|
| `backend/app/models.py` | SQLAlchemy ORM: `Mall`, `Store`, `MallStore` (junction with `UNIQUE(mall_id, store_id)`) |
| `backend/app/schemas.py` | Pydantic v2 schemas for all request/response types |
| `backend/app/services/data_gatherer.py` | Web scraping pipeline (requests + BS4) + DB upsert logic |
| `backend/app/services/store_matcher.py` | OpenAI fuzzy match + SQL rank query |
| `backend/app/routers/` | Thin route handlers — logic lives in services |
| `frontend/src/api/client.js` | Single fetch wrapper used by all components |
| `frontend/src/pages/Admin.jsx` | Triggers gather job, polls `/api/data/status` every 2s |
| `frontend/src/pages/Home.jsx` | Tag-chip store input + calls `/api/search` |
| `frontend/src/components/StoreSearch.jsx` | Tag-chip input with autocomplete dropdown — fetches all stores from `/api/stores` on mount, filters client-side as user types (starts-with ranked above contains, max 8 suggestions), supports arrow-key navigation and click-to-select |

### Environment
`backend/.env` is read at startup via `python-dotenv`. **Restart the backend after editing `.env`** — hot-reload does not re-read it.

Required variables:
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/malldb
OPENAI_API_KEY=sk-...
```

### Python environment
The venv lives at `backend/.venv`. Always invoke Python/pip via `.venv/bin/python` / `.venv/bin/pip`. The project targets Python 3.9 — use `Optional[X]` not `X | None`.

### Node version constraint
Node 18.x is the system version. The frontend is pinned to **Vite 5** and **Tailwind CSS 3** (PostCSS). Do not upgrade to Vite 6+ or `@tailwindcss/vite` — they require Node 20+.

### DB tables auto-created
`Base.metadata.create_all(bind=engine)` runs on every backend startup via the `lifespan` handler. Alembic is available for schema migrations but not required for initial setup.
