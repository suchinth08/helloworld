#!/bin/bash
# Run congress-twin API. Use --host 0.0.0.0 to accept connections from other machines (e.g. http://192.168.0.101:8010)
cd "$(dirname "$0")"
export PYTHONPATH=src
exec uv run uvicorn congress_twin.main:app --reload --host 0.0.0.0 --port 8010
