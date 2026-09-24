from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routes import auth, master_data

app = FastAPI(title="竹南冷凍倉儲庫存管理系統", version="0.1.0")
app.include_router(auth.router)
app.include_router(master_data.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness only; does not create or validate the database."""
    return {"status": "ok"}


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (frontend_dist / "index.html").is_file():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
