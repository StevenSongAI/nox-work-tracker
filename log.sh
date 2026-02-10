#!/bin/bash
# Quick wrapper for auto_logger.py
# Usage: ./log.sh <type> <description>
# Or: ./log.sh script <script_name> <description>
# Or: ./log.sh research <topic> <findings>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 auto_logger.py "$@"
