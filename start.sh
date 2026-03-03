#!/bin/bash
# Apply database migrations
alembic upgrade head

# Start the application
python main.py
