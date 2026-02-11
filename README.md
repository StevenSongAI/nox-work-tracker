# Work Tracker - Autonomous Multi-Agent Tracking

## 🎯 Problem Solved

**Old system:** Required manual logging after every task, which I always forgot.  
**New system:** Automatically tracks ALL work from Nox, Sage, and Joy by monitoring git commits. **Zero manual logging required.**

## 🚀 How It Works

### Autonomous Monitoring

The `auto_tracker.py` script runs continuously in the background (every 5 minutes) and:

1. **Monitors Git Repositories**
   - Watches 5 repos: nox-dashboard, nox-work-tracker, nox-scrapers, Ice Dragon Video, RALPH LOOPS
   - Detects new commits since last check
   - Extracts commit hash, author, message, timestamp

2. **Detects Agent from Commit**
   - Checks commit message patterns: `[nox]`, `[sage]`, `[joy]`
   - Falls back to author name if pattern not found
   - Defaults to Nox if unclear

3. **Classifies Work Type**
   - `feature` - New features, additions, implementations
   - `bug_fix` - Bug fixes, error corrections
   - `improvement` - Updates, enhancements, optimizations
   - `research` - Research, analysis, intelligence gathering
   - `documentation` - Docs, READMEs, guides
   - `refactor` - Code refactoring, cleanup, reorganization

4. **Auto-Logs Activity**
   - Appends to `data/activity-log.json`
   - Updates `meta.json` with timestamp
   - Auto-commits and pushes to GitHub
   - **No manual intervention required**

### What Gets Tracked

✅ **Git commits** from all monitored repos  
✅ **All 3 agents** (Nox, Sage, Joy)  
✅ **Classified by type** (feature, bug_fix, improvement, research, etc.)  
✅ **Project attribution** (dashboard, scrapers, ice_dragon_video, etc.)  
✅ **Automatic deduplication** (never logs same commit twice)

❌ **Currently NOT tracked:**  
- Session activity without git commits (research, analysis, browser automation)  
- Future enhancement: parse session transcripts for non-git work

## 📊 Dashboard

View live activity at:  
**File:** `index.html`  
**URL:** https://stevensongai.github.io/nox-work-tracker/

### Features:
- **All Activity Feed** - Shows all 3 agents combined
- **Agent Tabs** - Filter by Nox, Sage, or Joy
- **Type Filtering** - Filter by work type (feature, bug fix, etc.)
- **Live Stats** - Total activities, today, this week
- **Charts** - Activities by agent, activities by type
- **Auto-refresh** - Updates every 2 minutes

## 🎮 Usage

### Start Auto Tracker
```bash
cd ~/Desktop/Nox\ Builds/nox-work-tracker-repo
./start_auto_tracker.sh
```

This starts the autonomous monitoring process. It runs in the background and checks for new commits every 5 minutes.

### Stop Auto Tracker
```bash
cd ~/Desktop/Nox\ Builds/nox-work-tracker-repo
./stop_auto_tracker.sh
```

Or force kill:
```bash
pkill -f auto_tracker.py
```

### View Logs
```bash
tail -f ~/Desktop/Nox\ Builds/nox-work-tracker-repo/logs/auto_tracker.log
```

### Check if Running
```bash
ps aux | grep auto_tracker.py | grep -v grep
```

## 📝 Commit Message Convention

To ensure proper agent attribution, use these commit message patterns:

- **Nox:** `[nox] Description of work`
- **Sage:** `[sage] Description of work`  
- **Joy:** `[joy] Description of work`

Example:
```bash
git commit -m "[nox] Added NVDA earnings intelligence to dashboard"
git commit -m "[sage] Updated morning health metrics"
git commit -m "[joy] Researched new meme templates"
```

If you don't use the pattern, the tracker will try to detect the agent from the author name or default to Nox.

## 🔄 Monitoring Cycle

Every 5 minutes, the tracker:
1. Checks each monitored repo for new commits
2. Converts commits to activity entries
3. Deduplicates (never logs same commit twice)
4. Saves to `activity-log.json`
5. Commits and pushes changes to GitHub
6. Dashboard auto-refreshes every 2 minutes

**Result:** Continuous, automatic tracking with no manual intervention.

## 📂 File Structure

```
nox-work-tracker-repo/
├── data/
│   ├── activity-log.json      # All tracked activities (auto-updated)
│   └── meta.json              # Metadata (auto-updated)
├── logs/
│   └── auto_tracker.log       # Monitoring process log
├── auto_tracker.py            # Main monitoring script
├── start_auto_tracker.sh      # Start script
├── stop_auto_tracker.sh       # Stop script
├── index.html                 # Dashboard (GitHub Pages)
└── README.md                  # This file
```

## 🐛 Troubleshooting

### Tracker Not Running
```bash
# Check if process is running
ps aux | grep auto_tracker.py

# If not running, start it
cd ~/Desktop/Nox\ Builds/nox-work-tracker-repo
./start_auto_tracker.sh
```

### No Activities Being Logged
```bash
# Check log for errors
tail -50 ~/Desktop/Nox\ Builds/nox-work-tracker-repo/logs/auto_tracker.log

# Manually run monitoring cycle (for debugging)
cd ~/Desktop/Nox\ Builds/nox-work-tracker-repo
python3 auto_tracker.py
# Press Ctrl+C after one cycle completes
```

### Dashboard Not Updating
- Check that `activity-log.json` has new entries
- Hard-refresh browser (Cmd+Shift+R on Mac)
- Check GitHub Pages deployment status

## 🎯 Future Enhancements

1. **Session Transcript Parsing**
   - Track non-git work (research, analysis, browser automation)
   - Parse `.jsonl` session files for tool calls
   - Extract work summary from session context

2. **Real-Time WebSocket Updates**
   - Push updates to dashboard instantly (no 2-minute delay)
   - Live activity notifications

3. **Deeper Analytics**
   - Time-of-day activity patterns
   - Project velocity metrics
   - Agent workload distribution
   - Commit frequency trends

4. **Alerting**
   - Notify when tracker stops running
   - Alert on unusually low activity
   - Daily summary reports

## ✅ Status

- ✅ Auto tracker built and running (PID: 37914)
- ✅ Monitors 5 git repositories
- ✅ Tracks all 3 agents (Nox, Sage, Joy)
- ✅ Dashboard updated with live feed
- ✅ Zero manual logging required
- ✅ GitHub Pages deployed

**No more forgetting to log work. It just happens automatically.**
