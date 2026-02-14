#!/usr/bin/env python3
"""
Autonomous Work Tracker - Continuously monitors ALL agents (Nox, Sage, Joy)
Tracks git commits, session activity, and tool usage automatically.
NO MANUAL LOGGING REQUIRED.
"""

import json
import subprocess
import time
import os
from datetime import datetime, timezone
from pathlib import Path
import re

# Paths
TRACKER_DIR = Path("/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo")
ACTIVITY_LOG = TRACKER_DIR / "data" / "activity-log.json"
META_FILE = TRACKER_DIR / "meta.json"
STOP_FILE = TRACKER_DIR / "STOP_AUTO_TRACKER"

import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(TRACKER_DIR / "logs" / "auto_tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Session transcript paths for all 3 agents
SESSIONS_DIR = Path("/Users/stevenai/.openclaw/agents/main/sessions")

# Git repos to monitor
REPOS_TO_MONITOR = [
    "/Users/stevenai/Desktop/Nox Builds/nox-dashboard",
    "/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo",
    "/Users/stevenai/Desktop/Nox Builds/nox-scrapers",
    "/Users/stevenai/Desktop/Nox Builds/Ice Dragon Video",
    "/Users/stevenai/Desktop/Nox Builds/RALPH LOOPS",
]

# Track what we've already logged
SEEN_COMMITS = {}
SEEN_SESSIONS = set()

def load_activity_log():
    """Load existing activity log."""
    if ACTIVITY_LOG.exists():
        with open(ACTIVITY_LOG, 'r') as f:
            data = json.load(f)
            # Handle dict format {"entries": [...]} or list format [...]
            if isinstance(data, dict) and 'entries' in data:
                return data['entries']
            elif isinstance(data, list):
                return data
            else:
                return []
    return []

def save_activity_log(activities):
    """Save activity log and update meta."""
    # Save activities in dict format with entries key
    with open(ACTIVITY_LOG, 'w') as f:
        json.dump({"entries": activities}, f, indent=2)
    
    # Update meta
    meta = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "totalActivities": len(activities),
        "trackedAgents": ["nox", "sage", "joy"],
        "autoTracking": True
    }
    with open(META_FILE, 'w') as f:
        json.dump(meta, f, indent=2)

def get_git_commits_since(repo_path, last_commit_hash=None):
    """Get new commits from a repo since last check."""
    try:
        if not Path(repo_path).exists():
            return []
        
        if last_commit_hash:
            # Get commits since last known commit
            cmd = ['git', '-C', repo_path, 'log', f'{last_commit_hash}..HEAD', '--format=%H|%an|%at|%s', '--no-merges']
        else:
            # Get last 10 commits (first run)
            cmd = ['git', '-C', repo_path, 'log', '-10', '--format=%H|%an|%at|%s', '--no-merges']
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            return []
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('|', 3)
            if len(parts) == 4:
                commit_hash, author, timestamp, message = parts
                commits.append({
                    'hash': commit_hash,
                    'author': author,
                    'timestamp': int(timestamp),
                    'message': message,
                    'repo': Path(repo_path).name
                })
        
        return commits
    
    except Exception as e:
        print(f"  ⚠️  Error getting commits from {repo_path}: {e}")
        return []

def detect_agent_from_commit(commit):
    """Detect which agent made the commit based on message patterns."""
    message = commit['message'].lower()
    author = commit['author'].lower()
    
    # Check commit message patterns
    if '[nox]' in message or 'nox' in author:
        return 'nox'
    elif '[sage]' in message or 'sage' in author:
        return 'sage'
    elif '[joy]' in message or 'joy' in author:
        return 'joy'
    
    # Default to nox if unclear (since nox does most git work)
    return 'nox'

def classify_work_type(commit):
    """Classify the type of work from commit message."""
    message = commit['message'].lower()
    
    if any(word in message for word in ['fix', 'bug', 'error', 'issue']):
        return 'bug_fix'
    elif any(word in message for word in ['feature', 'add', 'new', 'implement']):
        return 'feature'
    elif any(word in message for word in ['update', 'improve', 'enhance', 'optimize']):
        return 'improvement'
    elif any(word in message for word in ['research', 'analysis', 'intel', 'data']):
        return 'research'
    elif any(word in message for word in ['doc', 'readme', 'guide']):
        return 'documentation'
    elif any(word in message for word in ['refactor', 'clean', 'reorg']):
        return 'refactor'
    else:
        return 'other'

def extract_project_from_repo(repo_name):
    """Extract project name from repo path."""
    project_map = {
        'nox-dashboard': 'dashboard',
        'nox-work-tracker-repo': 'work_tracker',
        'nox-scrapers': 'scrapers',
        'Ice Dragon Video': 'ice_dragon_video',
        'RALPH LOOPS': 'ralph_chain'
    }
    return project_map.get(repo_name, repo_name)

def commit_to_activity(commit):
    """Convert a git commit to an activity log entry."""
    agent = detect_agent_from_commit(commit)
    work_type = classify_work_type(commit)
    project = extract_project_from_repo(commit['repo'])
    
    return {
        "id": f"auto-{commit['hash'][:8]}",
        "timestamp": datetime.fromtimestamp(commit['timestamp'], tz=timezone.utc).isoformat(),
        "agent": agent,
        "type": work_type,
        "project": project,
        "description": commit['message'],
        "source": "git_commit",
        "repo": commit['repo'],
        "commit_hash": commit['hash'][:8]
    }

def parse_session_transcripts():
    """Parse recent session transcripts for non-git work."""
    # TODO: Implement session transcript parsing
    # This would extract work from session files that didn't result in git commits
    # Examples: research, analysis, tool usage, browser automation
    return []

def scan_for_new_work():
    """Scan all monitored sources for new work activities."""
    global SEEN_COMMITS
    
    new_activities = []
    
    # 1. Check git repos for new commits
    print("  📂 Scanning git repositories...")
    for repo_path in REPOS_TO_MONITOR:
        repo_name = Path(repo_path).name
        last_commit = SEEN_COMMITS.get(repo_name)
        
        commits = get_git_commits_since(repo_path, last_commit)
        
        if commits:
            # Update last seen commit for this repo
            SEEN_COMMITS[repo_name] = commits[0]['hash']
            
            # Convert commits to activities
            for commit in reversed(commits):  # Process oldest first
                activity = commit_to_activity(commit)
                new_activities.append(activity)
                print(f"     ✅ Git: [{activity['agent'].upper()}] {activity['description'][:60]}...")
    
    # 2. Check OpenClaw session transcripts for activity
    print("  📝 Scanning OpenClaw sessions...")
    try:
        import session_monitor
        session_count = session_monitor.main()
        
        # Load session activities if any were found
        session_file = TRACKER_DIR / ".session_activities.json"
        if session_file.exists():
            with open(session_file, 'r') as f:
                session_activities = json.load(f)
            
            new_activities.extend(session_activities)
            print(f"     ✅ Sessions: Found {len(session_activities)} activities")
            
            # Clean up temp file
            session_file.unlink()
        else:
            print(f"     ℹ️  No new session activities")
    
    except Exception as e:
        print(f"     ⚠️  Session monitoring failed: {e}")
    
    return new_activities

def deduplicate_activities(activities):
    """Remove duplicate entries based on ID."""
    seen_ids = set()
    deduped = []
    
    for activity in activities:
        if activity['id'] not in seen_ids:
            deduped.append(activity)
            seen_ids.add(activity['id'])
    
    return deduped

def run_monitoring_cycle():
    """Run one monitoring cycle - check for new work."""
    print("=" * 60)
    print("🔍 AUTO WORK TRACKER - Scanning for new activity")
    print(f"⏰ {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)
    
    # Load existing activities
    activities = load_activity_log()
    initial_count = len(activities)
    
    # Scan for new work
    new_activities = scan_for_new_work()
    
    if new_activities:
        # Add new activities
        activities.extend(new_activities)
        
        # Deduplicate
        activities = deduplicate_activities(activities)
        
        # Sort by timestamp (newest first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Save
        save_activity_log(activities)
        
        # Commit and push
        try:
            subprocess.run(['git', '-C', str(TRACKER_DIR), 'add', '.'], timeout=5)
            subprocess.run([
                'git', '-C', str(TRACKER_DIR), 'commit', '-m',
                f'[auto-tracker] Logged {len(new_activities)} activities'
            ], timeout=5)
            subprocess.run(['git', '-C', str(TRACKER_DIR), 'push', 'origin', 'main'], timeout=10)
            print(f"  📤 Pushed {len(new_activities)} new activities to GitHub")
        except Exception as e:
            print(f"  ⚠️  Failed to push: {e}")
        
        print(f"\n✅ Added {len(new_activities)} new activities")
        print(f"   Total activities: {len(activities)}")
    else:
        print("ℹ️  No new activities found")
    
    print("✅ Monitoring cycle complete\n")

def main():
    """Run autonomous monitoring loop."""
    print("🚀 AUTO WORK TRACKER STARTED")
    print("   Monitoring: Nox, Sage, Joy")
    print(f"   Repos: {len(REPOS_TO_MONITOR)} repositories")
    print(f"   Stop by creating: {STOP_FILE}")
    print("=" * 60)
    
    # Initialize last seen commits
    global SEEN_COMMITS
    for repo_path in REPOS_TO_MONITOR:
        repo_name = Path(repo_path).name
        try:
            # Get latest commit hash
            result = subprocess.run([
                'git', '-C', repo_path, 'rev-parse', 'HEAD'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                SEEN_COMMITS[repo_name] = result.stdout.strip()
        except:
            pass
    
    # Run monitoring loop
    while True:
        # Check for STOP file
        if STOP_FILE.exists():
            print("🛑 STOP file detected - shutting down")
            STOP_FILE.unlink()
            break
        
        try:
            run_monitoring_cycle()
        except Exception as e:
            print(f"❌ Error in monitoring cycle: {e}")
        
        # Sleep for 5 minutes
        print(f"💤 Sleeping for 5 minutes...")
        time.sleep(300)  # 5 minutes

if __name__ == "__main__":
    main()
