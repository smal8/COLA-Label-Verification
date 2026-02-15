from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR
from app.routes import health, analyze, pages

app = FastAPI(
    title="Alcohol Label Verification",
    description="AI-powered prototype for validating alcohol beverage labels via OCR",
    version="0.1.0",
)

# Mount the /static URL path to serve CSS/JS/images from the static/ directory.
# The "name" parameter lets templates reference it via url_for("static", path=...).
app.mount("/static", StaticFiles(directory=f"{BASE_DIR}/static"), name="static")
app.mount("/samples", StaticFiles(directory=f"{BASE_DIR}/samples"), name="samples")

# Register route modules.
# Each router handles a specific concern: health checks, API analysis, and UI pages.
app.include_router(health.router)
app.include_router(analyze.router)
app.include_router(pages.router)
