#!/bin/bash
# Apply database migrations (skip gracefully if no alembic config)
if [ -f alembic.ini ]; then
    alembic upgrade head || echo "⚠️ Alembic migration skipped (may not be configured)"
fi

# Start the application
python main.py
