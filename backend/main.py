"""MECE Prompt Builder — FastAPI backend."""
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import init_db
from .routers import projects, uploads, chat, templates, handoff

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    await init_db()
    print(f"MECE Prompt Builder API ready — {settings.environment}")
    yield
    print("Shutting down")


app = FastAPI(
    title="MECE Prompt Builder API",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(handoff.router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/v1/costs")
async def get_costs():
    """Get accumulated LLM cost tracking for this session."""
    from .services.ai_service import get_cost_tracker
    return get_cost_tracker().summary()
