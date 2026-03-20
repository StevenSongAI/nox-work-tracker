#!/usr/bin/env python3
"""
Real-time Pixel Office State Pusher
====================================
Watches OpenClaw agent session files for changes using OS-level file events
(kqueue/fsevents on macOS). When a session file is modified, it instantly
pushes the agent's state to the Railway API — no polling delay.

This is a lightweight companion to auto_tracker.py:
- auto_tracker.py  → logs activities, git commits, detailed tracking (runs every 60s)
- realtime_state.py → pushes pixel office animation states instantly (file watcher)

Resource usage:
- Near-zero CPU when idle (OS file events, not polling)
- One tiny HTTP POST per state change (~200 bytes)
- No Railway credit impact (server is already running)

Usage:
    python3 realtime_state.py
    # Or background:
    nohup python3 realtime_state.py > logs/realtime_state.log 2>&1 &
"""

import json
import os
import sys
import time
import glob
import logging
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────

RAILWAY_API = "https://nox-work-tracker-production.up.railway.app/api/agent-states"

# OpenClaw session directories to watch
SESSIONS_BASE = os.environ.get("OPENCLAW_SESSIONS", "/Users/stevenai/.openclaw/agents")
AGENT_MAP = {
    "main": "Nox",
    "nox":  "Nox",
    "sage": "Sage",
    "joy":  "Joy",
}
AGENT_EMOJI = {"Nox": "\u26a1", "Sage": "\ud83c\udf3f", "Joy": "\u2728"}

# How quickly an agent goes idle after last activity (seconds)
IDLE_TIMEOUT = 90

# How often to check for idle agents (seconds) — very cheap, just compares timestamps
IDLE_CHECK_INTERVAL = 10

# Minimum interval between state pushes for same agent (debounce)
PUSH_DEBOUNCE = 2.0

# ── Logging ─────────────────────────────────────────────────────────────────

log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "realtime_state.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("realtime_state")

# ── State tracking ──────────────────────────────────────────────────────────

agent_last_mtime = {}    # agent_name -> last seen session file mtime
agent_last_active = {}   # agent_name -> time.time() of last detected activity
agent_current_state = {} # agent_name -> current pushed state
agent_last_push = {}     # agent_name -> time.time() of last push (debounce)


def push_state(agent_name, state, detail=""):
    """Push agent state to Railway API (non-blocking, fire-and-forget)."""
    now = time.time()
    last = agent_last_push.get(agent_name, 0)
    if now - last < PUSH_DEBOUNCE:
        return  # debounce

    # Skip if state hasn't changed
    if agent_current_state.get(agent_name) == state:
        return

    payload = json.dumps({
        "name": agent_name,
        "emoji": AGENT_EMOJI.get(agent_name, ""),
        "state": state,
        "detail": detail[:60],
    }).encode()

    try:
        req = urllib.request.Request(
            RAILWAY_API,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
        agent_current_state[agent_name] = state
        agent_last_push[agent_name] = now
        log.info(f"  \u2192 {agent_name}: {state} ({detail})")
    except Exception as e:
        log.warning(f"Push failed for {agent_name}: {e}")


def classify_latest_activity(session_file):
    """Read the last few lines of a session file to determine activity type."""
    try:
        # Read last 8KB to find recent tool calls
        with open(session_file, "rb") as f:
            f.seek(0, 2)  # end
            size = f.tell()
            f.seek(max(0, size - 8192))
            tail = f.read().decode("utf-8", errors="replace")

        # Check for tool call patterns in reverse order (most recent first)
        lines = tail.strip().split("\n")
        for line in reversed(lines):
            try:
                entry = json.loads(line)
            except Exception:
                continue

            message = entry.get("message", entry)
            if message.get("role") != "assistant":
                continue

            content = message.get("content", [])
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "toolCall":
                    continue
                tool = item.get("name", "")

                if tool in ("web_search", "web_fetch", "WebSearch", "WebFetch"):
                    return "researching", "Web research"
                elif tool in ("write", "Write", "edit", "Edit"):
                    return "writing", "Editing files"
                elif tool in ("exec", "Bash"):
                    cmd = (item.get("arguments") or {}).get("command", "")
                    if any(t in cmd for t in ["git push", "git commit", "deploy", "sync"]):
                        return "syncing", "Git/deploy"
                    return "executing", "Running commands"
                elif tool in ("browser", "navigate"):
                    return "researching", "Browser automation"
                elif tool in ("message", "sessions_spawn"):
                    return "syncing", "Agent communication"

        return "writing", "Active session"
    except Exception:
        return "writing", "Active session"


def check_sessions():
    """Check all agent session directories for file changes. Returns True if any changed."""
    any_change = False
    now = time.time()

    for agent_dir, agent_name in AGENT_MAP.items():
        if agent_dir == "nox" and "main" in AGENT_MAP:
            continue  # 'main' and 'nox' both map to Nox — skip duplicate

        sessions_dir = os.path.join(SESSIONS_BASE, agent_dir, "sessions")
        if not os.path.isdir(sessions_dir):
            continue

        # Find newest session file
        files = glob.glob(os.path.join(sessions_dir, "*.jsonl"))
        if not files:
            continue

        newest = max(files, key=os.path.getmtime)
        mtime = os.path.getmtime(newest)
        prev_mtime = agent_last_mtime.get(agent_name, 0)

        if mtime > prev_mtime:
            agent_last_mtime[agent_name] = mtime
            agent_last_active[agent_name] = now
            any_change = True

            # Classify what they're doing
            state, detail = classify_latest_activity(newest)
            push_state(agent_name, state, detail)

    return any_change


def check_idle():
    """Push idle state for agents that haven't been active recently."""
    now = time.time()
    for agent_name in set(AGENT_MAP.values()):
        last = agent_last_active.get(agent_name, 0)
        if last > 0 and (now - last) > IDLE_TIMEOUT:
            agent_last_active[agent_name] = 0
            push_state(agent_name, "idle", "Standing by")


def run_with_fswatch():
    """Use fswatch (macOS) for instant file change detection."""
    import subprocess

    # Build list of directories to watch
    watch_dirs = []
    for agent_dir in AGENT_MAP:
        d = os.path.join(SESSIONS_BASE, agent_dir, "sessions")
        if os.path.isdir(d):
            watch_dirs.append(d)

    if not watch_dirs:
        log.error(f"No session directories found under {SESSIONS_BASE}")
        log.error("Falling back to polling mode")
        return False

    log.info(f"Watching {len(watch_dirs)} directories with fswatch")
    for d in watch_dirs:
        log.info(f"  {d}")

    # Start fswatch process
    cmd = ["fswatch", "-r", "--event", "Updated", "--event", "Created"] + watch_dirs
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    except FileNotFoundError:
        log.warning("fswatch not installed — install with: brew install fswatch")
        return False

    log.info("fswatch started — real-time mode active")
    last_idle_check = time.time()

    try:
        import select
        while True:
            # Non-blocking read with timeout for idle checks
            ready, _, _ = select.select([proc.stdout], [], [], IDLE_CHECK_INTERVAL)
            if ready:
                line = proc.stdout.readline()
                if not line:
                    break
                # File changed — check sessions
                check_sessions()

            # Periodic idle check
            now = time.time()
            if now - last_idle_check >= IDLE_CHECK_INTERVAL:
                check_idle()
                last_idle_check = now
    except KeyboardInterrupt:
        log.info("Shutting down...")
    finally:
        proc.terminate()

    return True


def run_polling_fallback():
    """Fallback: poll session files every 2 seconds (if fswatch unavailable)."""
    log.info("Running in polling mode (2s interval)")
    last_idle_check = time.time()

    try:
        while True:
            check_sessions()

            now = time.time()
            if now - last_idle_check >= IDLE_CHECK_INTERVAL:
                check_idle()
                last_idle_check = now

            time.sleep(2)
    except KeyboardInterrupt:
        log.info("Shutting down...")


def main():
    log.info("=" * 50)
    log.info("REAL-TIME PIXEL OFFICE STATE PUSHER")
    log.info(f"Watching: {SESSIONS_BASE}")
    log.info(f"Pushing to: {RAILWAY_API}")
    log.info(f"Idle timeout: {IDLE_TIMEOUT}s")
    log.info("=" * 50)

    # Initial state check
    check_sessions()

    # Try fswatch first, fall back to polling
    if not run_with_fswatch():
        run_polling_fallback()


if __name__ == "__main__":
    main()
