#!/bin/bash

set -e

ENTITY_ID=${1:-order_1000}
CHEAP=${2:-}

echo "🚀 Incident Detective Agent (Python)"
echo "===================================="

cd incident-agent

echo "📦 Setting up virtualenv & dependencies..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install -q -r requirements.txt

echo "🌱 Seeding database..."
./.venv/bin/python scripts/seed.py > /dev/null 2>&1 || true

echo "🔍 Running investigation for $ENTITY_ID..."
if [ "$CHEAP" = "--cheap" ]; then
  ./.venv/bin/python src/cli.py "$ENTITY_ID" --cheap
else
  ./.venv/bin/python src/cli.py "$ENTITY_ID"
fi
