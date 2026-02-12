# Work Tracker - Installation

## Automatic Session Monitoring

The work tracker automatically scans OpenClaw session transcripts for all agents (Nox, Sage, Joy, main) and updates the dashboard every 5 minutes.

### Setup (macOS)

The system uses **launchd** (macOS background service) to run `session_monitor.py` every 5 minutes without requiring any agent interaction.

**Already installed.** To verify it's running:

```bash
launchctl list | grep worktracker
```

You should see:
```
82556	0	com.nox.worktracker
```

### Manual Installation (if needed)

If the service isn't running:

```bash
cd ~/Desktop/Nox\ Builds/nox-work-tracker-repo
cp com.nox.worktracker.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.nox.worktracker.plist
```

### Uninstall

To stop automatic monitoring:

```bash
launchctl unload ~/Library/LaunchAgents/com.nox.worktracker.plist
rm ~/Library/LaunchAgents/com.nox.worktracker.plist
```

### How It Works

1. **launchd** runs `session_monitor.py` every 5 minutes
2. Script scans all agent session files for new activity
3. Updates `data/activity-log.json` with new entries
4. Commits and pushes to GitHub automatically
5. GitHub Pages updates the live dashboard

**No agent tokens consumed.** The script runs as a system process, not an OpenClaw cron job.

### Logs

Check for errors:
```bash
tail -f ~/Desktop/Nox\ Builds/nox-work-tracker-repo/logs/launchd-error.log
```

View activity:
```bash
tail -f ~/Desktop/Nox\ Builds/nox-work-tracker-repo/logs/launchd.log
```

### Manual Run

To trigger a manual scan:
```bash
cd ~/Desktop/Nox\ Builds/nox-work-tracker-repo
python3 session_monitor.py
```
