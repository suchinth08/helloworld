#!/bin/bash
# Setup script for Novartis Planner (Congress Twin)
# This script sets up the database and loads seed data

set -e

echo "🚀 Setting up Novartis Planner..."

# Check if Python/uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: 'uv' not found. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Run seed script to load data
echo "🌱 Loading seed data into SQLite..."
PYTHONPATH=src uv run python -m congress_twin.scripts.seed_congress_db

echo "✅ Setup complete!"
echo ""
echo "To start the backend:"
echo "  PYTHONPATH=src uv run uvicorn congress_twin.main:app --reload --port 8010"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm install && npm run dev"
