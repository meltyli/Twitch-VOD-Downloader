#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "myenv" ]; then
    echo "Virtual environment not found. Creating myenv..."
    python3 -m venv myenv
    source myenv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    source myenv/bin/activate
fi

python3 -m src.twitch_recorder
