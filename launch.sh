#!/bin/bash
set -euo pipefail

# If running inside Docker (/.dockerenv) or DOCKER=1 is set, use system Python
# and skip creating a local virtual environment. This makes `docker compose up`
# / `docker compose down` behave correctly with the provided image.
if [ -f "/.dockerenv" ] || [ "${DOCKER:-}" = "1" ]; then
    echo "Running in container mode; using system Python."
    exec python3 -m src.twitch_recorder
fi

# Local development: create virtual environment if it doesn't exist
if [ ! -d "pyenv" ]; then
    echo "Virtual environment not found. Creating pyenv..."
    python3 -m venv pyenv
    # shellcheck disable=SC1091
    source pyenv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    # shellcheck disable=SC1091
    source pyenv/bin/activate
    echo "Installing/updating dependencies..."
    pip install -r requirements.txt
fi

exec python3 -m src.twitch_recorder
