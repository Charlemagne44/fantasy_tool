from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .csv_parser import CsvParseError, parse_etr_csv
from .models import OptimizeRequest, OptimizeResponse, PlayersResponse
from .optimizer import OptimizeError, optimize_lineups

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CSV = ROOT / "sample_data" / "etr_dk_main_slate.csv"
DIST_DIR = ROOT / "frontend" / "dist"

app = FastAPI(title="Fantasy Lineup Optimizer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/players/upload", response_model=PlayersResponse)
async def upload_players(file: UploadFile = File(...)) -> PlayersResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        players = parse_etr_csv(content)
    except CsvParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PlayersResponse(players=players)


@app.get("/api/players/sample", response_model=PlayersResponse)
def sample_players() -> PlayersResponse:
    if not SAMPLE_CSV.exists():
        raise HTTPException(status_code=404, detail="Sample CSV not found")
    try:
        players = parse_etr_csv(SAMPLE_CSV.open("rb"))
    except CsvParseError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return PlayersResponse(players=players)


@app.get("/api/sample.csv")
def download_sample_csv() -> FileResponse:
    if not SAMPLE_CSV.exists():
        raise HTTPException(status_code=404, detail="Sample CSV not found")
    return FileResponse(
        SAMPLE_CSV,
        media_type="text/csv",
        filename="etr_dk_main_slate.csv",
    )


@app.post("/api/optimize", response_model=OptimizeResponse)
def optimize(req: OptimizeRequest) -> OptimizeResponse:
    try:
        lineups = optimize_lineups(req)
    except OptimizeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OptimizeResponse(
        lineups=lineups,
        salary_cap=req.salary_cap,
        aggression=req.aggression,
    )


if DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def spa_index() -> FileResponse:
        return FileResponse(DIST_DIR / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (DIST_DIR / full_path).resolve()
        try:
            candidate.relative_to(DIST_DIR.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
