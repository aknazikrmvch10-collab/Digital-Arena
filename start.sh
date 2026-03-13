#!/bin/bash
set -e  # Exit immediately if any command fails

echo "🚀 Digital Arena — Starting up..."
echo "📦 Database URL type: $(echo $DB_URL | cut -d: -f1)"

# ── Run Alembic migrations ───────────────────────────────────────────────────
if [ -f alembic.ini ]; then
    echo "🗄️  Running database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "✅ Migrations complete."
else
    echo "⚠️  alembic.ini not found, skipping migrations."
fi

# ── Start the application ────────────────────────────────────────────────────
echo "⚡ Starting Digital Arena bot + API server..."
python main.py
