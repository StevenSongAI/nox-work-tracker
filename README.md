# Nox Work Tracker

24/7 agent activity monitoring dashboard for Steven Song.

## URL
https://stevensongai.github.io/nox-work-tracker/

## Data Structure

All data lives in `/data/` as JSON files:
- `activity-log.json` - Chronological activity feed (all agents)
- `audits.json` - All audit reports with grades
- `ralph-chains.json` - Ralph-chain run history
- `agents.json` - Agent profiles + aggregate stats
- `meta.json` - Last updated, sync status

## Agent Integration

The agent updates this tracker by:
1. `git pull origin main`
2. Append new entries to the relevant JSON file
3. `git add . && git commit -m "[agent:nox] log: heartbeat completed" && git push`
4. GitHub Pages auto-deploys on push to main

### What gets logged:

**Every heartbeat:**
- type: "heartbeat"
- action: "Heartbeat #N: description"
- status: "success" | "failed"

**Every subagent spawn:**
- type: "subagent_spawn"
- action: "Spawned RED_TEAM for batch X audit"

**Every audit:**
- Append to audits.json
- Update agents.json stats

**Every ralph-chain event:**
- Append to activity-log.json
- Update ralph-chains.json

## Local Development

Open `index.html` in any browser. No server needed.
