#!/bin/bash
# Start the autonomous work tracker

TRACKER_DIR="/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo"
LOG_DIR="$TRACKER_DIR/logs"
mkdir -p "$LOG_DIR"

echo "🚀 Starting Auto Work Tracker..."

# Start auto tracker in background
nohup python3 "$TRACKER_DIR/auto_tracker.py" > "$LOG_DIR/auto_tracker.log" 2>&1 &
PID=$!

echo "  ✅ Auto Tracker started (PID: $PID)"
echo "     Log: $LOG_DIR/auto_tracker.log"
echo ""
echo "To stop:"
echo "  touch '$TRACKER_DIR/STOP_AUTO_TRACKER'"
echo ""
echo "View log:"
echo "  tail -f '$LOG_DIR/auto_tracker.log'"
