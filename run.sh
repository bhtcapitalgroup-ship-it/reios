#!/bin/bash
# REIOS Run Script
# Start: ./run.sh
# Stop:  Ctrl+C

set -e
cd "$(dirname "$0")"

echo "╔══════════════════════════════════════════╗"
echo "║   REIOS — Real Estate Investor OS        ║"
echo "║   Starting...                             ║"
echo "╚══════════════════════════════════════════╝"

# Check setup
if [ ! -d "backend/.venv" ]; then
    echo "✗ Run ./setup.sh first"
    exit 1
fi

cd backend
source .venv/bin/activate

# Kill any existing REIOS processes on these ports
lsof -ti:8000 | xargs kill 2>/dev/null || true
lsof -ti:3000 | xargs kill 2>/dev/null || true
sleep 1

# Start API server
echo ""
echo "▸ Starting API server on http://localhost:8000"
echo "  Swagger docs: http://localhost:8000/docs"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Start frontend server
echo "▸ Starting frontend on http://localhost:3000"
cd ../frontend
python3 -m http.server 3000 --bind 0.0.0.0 &
FRONT_PID=$!

sleep 2
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   REIOS is running!                       ║"
echo "║                                           ║"
echo "║   Frontend:  http://localhost:3000         ║"
echo "║   API:       http://localhost:8000         ║"
echo "║   API Docs:  http://localhost:8000/docs    ║"
echo "║                                           ║"
echo "║   Press Ctrl+C to stop                    ║"
echo "╚══════════════════════════════════════════╝"

# Open in browser
open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || true

# Wait and cleanup on exit
cleanup() {
    echo ""
    echo "▸ Stopping REIOS..."
    kill $API_PID 2>/dev/null
    kill $FRONT_PID 2>/dev/null
    echo "✓ Stopped"
}
trap cleanup EXIT INT TERM

wait
