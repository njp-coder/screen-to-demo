from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipeline.api.routes import jobs, outputs, uploads
from pipeline.database import Base, engine

app = FastAPI(
    title="Recording-to-Video Pipeline API",
    description="Converts screen recordings into polished demo videos.",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — permissive for local development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(outputs.router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    """Create database tables on startup (dev convenience)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
