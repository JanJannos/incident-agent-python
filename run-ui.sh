#!/bin/bash

set -e

echo "🖥️  Incident DB UI (Python)"
echo "==========================="

echo "📦 Setting up agent virtualenv & seeding DB..."
cd incident-agent
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install -q -r requirements.txt
./.venv/bin/python scripts/seed.py
cd ..

echo "📦 Setting up UI virtualenv..."
cd incident-ui
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install -q -r requirements.txt

echo ""
echo "🔍 Starting UI on http://localhost:5000"
lsof -ti :5000 | xargs kill -9 2>/dev/null || true
./.venv/bin/python src/server.py
