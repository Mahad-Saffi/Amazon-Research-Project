"""
FastAPI Application for Amazon Product Research
Processes CSV files and ASIN/URL in memory without intermediate files
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import logging
from pathlib import Path

from api.endpoints import research

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Amazon Product Research API",
    description="Analyze Amazon products with design and revenue keyword data",
    version="1.0.0"
)

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(research.router, prefix="/api", tags=["research"])

@app.get("/")
async def root():
    """Serve the web interface"""
    static_file = static_dir / "index.html"
    if static_file.exists():
        return FileResponse(static_file)
    return {
        "message": "Amazon Product Research API",
        "version": "1.0.0",
        "endpoints": {
            "research": "/api/research",
            "research_json": "/api/research/json",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
