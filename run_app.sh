#!/bin/bash

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Run setup if .env doesn't exist
if [ ! -f ".env" ]; then
    python3.11 setup_config.py
fi

# Create and activate virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r Requirements.txt
else
    source venv/bin/activate
fi

# Launch Streamlit
streamlit run main.py

# Open browser
open http://localhost:5000 