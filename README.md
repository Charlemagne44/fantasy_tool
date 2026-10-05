# Fantasy Lineup Optimizer (ETR + DraftKings Classic)

Local web tool that builds DraftKings Classic NFL lineups from Establish The Run projection CSVs. Optimizes under a salary cap using floor / median / ceiling-aware scoring, with lock/exclude controls and top-N lineup generation.

## One-click launch

Double-click the launcher for your system (or run it from a terminal). It creates a virtual environment if needed, installs dependencies, builds the UI on first run, starts the app, and opens your default browser.

| System | Launcher |
|--------|----------|
| macOS | Double-click `Start.command` |
| Windows | Double-click `Start.bat` |
| Linux | Double-click or run `./Start.sh` |

The app opens at http://127.0.0.1:8000. Leave the terminal window open while you use it; press `Ctrl+C` (or close the window) to stop the server.

**First launch** may take a minute while Python packages and the frontend build are set up. Later launches are much faster and only need Python (as long as `frontend/dist` already exists).

### Prerequisites

- **Python 3.9+** (always)
- **Node.js 18+** and **npm** (first build only, or after deleting `frontend/dist`)

## Stack

- **Backend:** Python, FastAPI, PuLP (HiGHS)
- **Frontend:** Vite + React + TypeScript

## Manual / development setup

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

### Run with hot reload (two terminals)

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

Open http://localhost:5173 (Vite proxies `/api` to the backend).

### Or use the one-click path from a terminal

```bash
./Start.sh
# or: python3 launch.py
```

## ETR CSV format

Upload the Establish The Run export `DraftKings NFL DFS Projections -- Main Slate.csv`. Required columns:

`Player`, `DK Pos`, `Team`, `Opp`, `DK Salary`, `DK Proj`, `DK Value`, `Small Field`, `Large Field`, `DK Floor`, `DK Ceiling`, `id`

A sample file lives at `sample_data/etr_dk_main_slate.csv`.

## Tests

```bash
source .venv/bin/activate
pytest backend/tests -q
```
