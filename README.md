# Singapore Mall Finder

Find which Singapore shopping malls have all the stores you want to visit — in one trip.

---

## Prerequisites

| Tool | Minimum version | Check |
|------|----------------|-------|
| Node.js | 18.x | `node --version` |
| Python | 3.9+ | `python --version` |
| Docker + Docker Compose | any recent | `docker --version` |

---

## Installation

### 1. Clone the repo

```bash
git clone <repo-url>
cd wifey-app
```

### 2. Set up environment variables

```bash
cp backend/.env.example backend/.env
```

Open `backend/.env` and confirm the database URL:

```
DATABASE_URL=postgresql://postgres:password@localhost:5432/malldb
```

### 3. Start the database

```bash
docker-compose up -d
```

This spins up PostgreSQL 16 on port **5432**. Tables are created automatically when the backend starts.

### 4. Install and run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is now running at **http://localhost:8000**.

### 5. Install and run the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The app is now running at **http://localhost:5173**.

---

## Usage

### Step 1 — Gather mall data (first-time setup)

1. Open **http://localhost:5173/admin** in your browser.
2. Click **Gather Mall Data**.
3. GPT-4o will use web search to discover Singapore malls and scrape each mall's store directory. The progress bar updates every 2 seconds and shows which mall is currently being scanned.
4. Wait for the status to show **Complete!** before searching. This process can take several minutes depending on the number of malls found (~100 malls, one API call each).

> You only need to do this once. Re-run it periodically to refresh the data.

### Step 2 — Search for malls

1. Open **http://localhost:5173**.
2. Type a store name in the input box (e.g. `Uniqlo`) and press **Enter** to add it as a tag.
3. Repeat for each store you want to visit (e.g. `Starbucks`, `Cotton On`).
4. To remove a store, click the **×** on its tag, or press **Backspace** when the input is empty.
5. Click **Find Malls**.

### Step 3 — Read the results

Results are ranked by how many of your stores each mall contains:

```
VivoCity — 3/3 stores found
  ✓ Uniqlo   ✓ Starbucks   ✓ Cotton On

ION Orchard — 2/3 stores found
  ✓ Uniqlo   ✓ Starbucks   ✗ Cotton On
```

- **Green chips** = store found in that mall
- **Red chips** = store not found
- Typos and alternate spellings are handled automatically (e.g. `Starbaks` → `Starbucks`)

---

## API Reference

The backend exposes a REST API at **http://localhost:8000/api**.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/data/gather` | Trigger background data-gathering job |
| `GET` | `/api/data/status` | Poll job progress |
| `GET` | `/api/malls` | List all malls |
| `GET` | `/api/malls/{id}` | Mall detail including all stores |
| `GET` | `/api/stores` | List all stores in the database |
| `POST` | `/api/search` | Search for malls by store list |

**Search request example:**

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"stores": ["Uniqlo", "Starbucks", "Cotton On"]}'
```

---

## Project Structure

```
wifey-app/
├── docker-compose.yml          # PostgreSQL service
├── backend/
│   ├── .env.example            # Environment variable template
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI entry point
│       ├── models.py           # Database models (Mall, Store, MallStore)
│       ├── schemas.py          # Request / response schemas
│       ├── routers/            # API route handlers
│       └── services/
│           ├── data_gatherer.py  # OpenAI gpt-4o-search-preview web search pipeline
│           └── store_matcher.py  # OpenAI gpt-4o fuzzy matching + SQL ranking
└── frontend/
    └── src/
        ├── pages/
        │   ├── Home.jsx        # Search page
        │   └── Admin.jsx       # Data gathering page
        └── components/
            ├── StoreSearch.jsx # Tag-style store input
            ├── MallCard.jsx    # Single mall result card
            └── MallResults.jsx # Ranked list of mall cards
```

---

## Troubleshooting

**Backend won't start — "could not connect to server"**
Make sure Docker is running and the database container is up: `docker-compose up -d`

**Data gathering fails immediately**
Check that the backend is running and the database container is up.

**Search returns no results**
Data has not been gathered yet, or gathering did not complete successfully. Go to `/admin` and run the gather job again.

**Frontend build fails**
This project requires Node.js 18.x. Vite 6+ (which requires Node 20+) is not used here.
