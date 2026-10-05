# Fantasy Lineup Optimizer (ETR + DraftKings Classic)

Local web tool that builds DraftKings Classic NFL lineups from Establish The Run projection CSVs. Optimizes under a salary cap using floor / median / ceiling-aware scoring, with lock/exclude controls and top-N lineup generation.

## Stack

- **Backend:** Python, FastAPI, PuLP (HiGHS)
- **Frontend:** Vite + React + TypeScript

## Setup

```bash
# Backend
python3 -m venv .venv
source .venv/bin/activate          # bash/zsh
# source .venv/bin/activate.fish   # fish
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

## Run locally

Terminal 1 — API (port 8000):

```bash
# bash/zsh
source .venv/bin/activate
uvicorn backend.app.main:app --reload --port 8000

# fish
source .venv/bin/activate.fish
uvicorn backend.app.main:app --reload --port 8000

# or without activating the venv:
.venv/bin/uvicorn backend.app.main:app --reload --port 8000
```

Terminal 2 — UI (port 5173):

```bash
cd frontend
npm run dev
```

Open http://localhost:5173

## ETR CSV format

Upload the Establish The Run export `DraftKings NFL DFS Projections -- Main Slate.csv`. Required columns:

`Player`, `DK Pos`, `Team`, `Opp`, `DK Salary`, `DK Proj`, `DK Value`, `Small Field`, `Large Field`, `DK Floor`, `DK Ceiling`, `id`

A sample file lives at `sample_data/etr_dk_main_slate.csv`.

## Tests

```bash
source .venv/bin/activate
pytest backend/tests -q
```
