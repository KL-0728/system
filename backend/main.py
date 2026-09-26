from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.routes import auth, master_data, stock_options, outbound, inventory, adjustments, reports, shortages

app = FastAPI(title="竹南冷凍倉儲庫存管理系統", version="0.1.0")
app.include_router(auth.router)
app.include_router(master_data.router)
app.include_router(stock_options.router)
app.include_router(outbound.router)
app.include_router(inventory.router)
app.include_router(adjustments.router)
app.include_router(reports.router)
app.include_router(shortages.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness only; does not create or validate the database."""
    return {"status": "ok"}


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if (frontend_dist / "index.html").is_file():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
