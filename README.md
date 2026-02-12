# Work Tracker

Auto-tracking dashboard for Nox, Sage, and Joy agent activity.

## Quick Start

```bash
cd ~/Desktop/Nox\ Builds/nox-work-tracker-repo
./start.sh
```

Then open http://localhost:8081 in your browser.

**Important:** The tracker must be served via HTTP (not `file://`). The start script handles this automatically.

## Features

- **Live Activity Feed** - Real-time view of all agent work
- **Agent Tabs** - Filter by Nox, Sage, or Joy
- **Type Filters** - Filter by activity type (feature, bug fix, research, etc.)
- **Stats Dashboard** - Overview of work completed

## Data

Activity data is stored in `data/activity-log.json` with the structure:

```json
{
  "entries": [
    {
      "timestamp": "2026-02-10T03:00:00Z",
      "type": "youtube_research",
      "description": "...",
      "agent": "nox",
      "session": "cron-youtube-research",
      "project": "stevensongirl"
    }
  ]
}
```

## Logging Activity

Use the `auto_logger.py` script:

```python
from auto_logger import log_activity

log_activity(
    type="feature",
    description="Built new dashboard component",
    agent="nox",
    project="work-tracker"
)
```

## Troubleshooting

**"Loading..." stuck:**
- Make sure you're using `http://localhost:8081` not `file://`
- Run `./start.sh` to start the HTTP server
- Check browser console for errors

**No data showing:**
- Verify `data/activity-log.json` exists and has entries
- Check the JSON structure matches the schema above
