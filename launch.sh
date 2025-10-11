#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "pyenv" ]; then
    echo "Virtual environment not found. Creating pyenv..."
    python3 -m venv pyenv
    source pyenv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source pyenv/bin/activate
    echo "Installing/updating dependencies..."
    pip install -r requirements.txt
fi

python3 -m src.twitch_recorder
