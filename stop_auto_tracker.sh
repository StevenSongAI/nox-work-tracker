#!/bin/bash
# Stop the autonomous work tracker

TRACKER_DIR="/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo"

echo "🛑 Stopping Auto Work Tracker..."

# Create STOP file
touch "$TRACKER_DIR/STOP_AUTO_TRACKER"

echo "✅ STOP signal sent"
echo "   Tracker will shut down after current cycle completes (max 30 seconds)"
echo ""
echo "To force kill if needed:"
echo "  pkill -f auto_tracker.py"
