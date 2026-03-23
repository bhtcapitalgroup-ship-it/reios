FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY scripts/seed_data.py /app/seed_data.py

# Make seed script importable from the app's working dir
RUN mkdir -p /app/../scripts && cp /app/seed_data.py /app/../scripts/seed_data.py 2>/dev/null; \
    ln -sf /app/seed_data.py /scripts/seed_data.py 2>/dev/null || true

ENV DATABASE_URL=sqlite+aiosqlite:///./reios.db
ENV SECRET_KEY=change-me-in-production

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
