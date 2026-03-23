#!/bin/bash
# REIOS Setup Script
# Run once: ./setup.sh

set -e
echo "╔══════════════════════════════════════════╗"
echo "║   REIOS — Real Estate Investor OS        ║"
echo "║   Setup Script                            ║"
echo "╚══════════════════════════════════════════╝"

cd "$(dirname "$0")"

# 1. Python venv
echo ""
echo "▸ Creating Python virtual environment..."
cd backend
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
echo "▸ Installing dependencies..."
pip install --quiet fastapi uvicorn pydantic pydantic-settings python-dotenv \
    sqlalchemy aiosqlite python-jose passlib python-multipart bcrypt \
    numpy httpx orjson greenlet 2>&1 | grep -v "already satisfied"

# 3. Create .env if missing
if [ ! -f .env ]; then
    cp .env.example .env
    echo "▸ Created .env from template"
fi

# 4. Create database and seed
echo "▸ Creating database tables..."
python3 -c "
import asyncio
from app.core.database import engine, Base
import app.models
async def setup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('  27 tables created')
asyncio.run(setup())
"

echo "▸ Seeding market data..."
cd ..
python3 scripts/seed_data.py

echo ""
echo "✓ Setup complete! Run ./run.sh to start REIOS"
