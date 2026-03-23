import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.api.v1 import auth, deals, portfolios, markets, ai, sourcing, financing

settings = get_settings()

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.database import engine, Base
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"REIOS v{settings.app_version} — database ready")

    # Auto-seed if database is empty
    from sqlalchemy import select, func
    from app.core.database import async_session
    from app.models.market import MarketMetrics
    async with async_session() as session:
        result = await session.execute(select(func.count(MarketMetrics.id)))
        if result.scalar() == 0:
            print("Seeding market data...")
            import subprocess, sys
            seed_script = Path(__file__).parent.parent.parent / "scripts" / "seed_data.py"
            if seed_script.exists():
                subprocess.run([sys.executable, str(seed_script)], check=True)
                print("Seed complete")

    yield
    await engine.dispose()


app = FastAPI(
    title="REIOS API",
    description="Real Estate Investor Operating System — AI-powered investment lifecycle management",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(deals.router, prefix="/api/v1")
app.include_router(portfolios.router, prefix="/api/v1")
app.include_router(markets.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(sourcing.router, prefix="/api/v1")
app.include_router(financing.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.app_version}


# Serve frontend — must be last so API routes take priority
@app.get("/")
async def serve_frontend():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"name": "REIOS", "version": settings.app_version, "ui": "Visit /docs for API documentation"}
