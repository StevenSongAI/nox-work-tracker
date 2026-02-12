#!/bin/bash
# Start the Work Tracker local server

cd "$(dirname "$0")"
echo "🔨 Starting Work Tracker on http://localhost:8081"
echo "Press Ctrl+C to stop"
echo ""
python3 -m http.server 8081
