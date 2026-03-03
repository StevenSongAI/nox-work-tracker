#!/usr/bin/env python3
"""
Session Activity Monitor - Tracks OpenClaw agent activity from session transcripts
Monitors: tool calls, subagent spawns, file operations, browser automation, etc.

FIXED: Now tracks last-seen timestamp per session instead of marking entire sessions as "processed"
This allows continuous monitoring of ongoing long-running sessions.
"""

import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
import time

# Setup logging to auto_tracker.log
log_dir = Path("/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo/logs")
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "auto_tracker.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Session transcript directories - scan ALL agents
AGENT_DIRS = [
    Path("/Users/stevenai/.openclaw/agents/main/sessions"),
    Path("/Users/stevenai/.openclaw/agents/nox/sessions"),
    Path("/Users/stevenai/.openclaw/agents/sage/sessions"),
    Path("/Users/stevenai/.openclaw/agents/joy/sessions"),
]

# Track last timestamp we saw in each session (not just "processed" flag)
SESSION_TIMESTAMPS = {}
SESSIONS_CACHE_FILE = Path("/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo/.processed_sessions.json")

def load_session_timestamps():
    """Load last-seen timestamp for each session."""
    if SESSIONS_CACHE_FILE.exists():
        with open(SESSIONS_CACHE_FILE, 'r') as f:
            data = json.load(f)
            # Handle old format (list) vs new format (dict)
            if isinstance(data, list):
                # Convert old format to new: assume all old sessions are fully processed
                return {session_id: float('inf') for session_id in data}
            # Ensure all values are numeric floats
            result = {}
            for session_id, timestamp in data.items():
                try:
                    result[session_id] = float(timestamp) if timestamp else 0
                except (ValueError, TypeError):
                    result[session_id] = 0
            return result
    return {}

def save_session_timestamps():
    """Save last-seen timestamps for each session."""
    # Ensure all timestamps are numeric before saving
    cleaned_timestamps = {}
    for session_id, timestamp in SESSION_TIMESTAMPS.items():
        try:
            cleaned_timestamps[session_id] = float(timestamp) if timestamp else 0
        except (ValueError, TypeError):
            cleaned_timestamps[session_id] = 0
    with open(SESSIONS_CACHE_FILE, 'w') as f:
        json.dump(cleaned_timestamps, f, indent=2)

def parse_session_transcript(session_file, agent_name, last_seen_timestamp=0):
    """Parse a session transcript and extract activities AFTER last_seen_timestamp.
    
    Args:
        session_file: Path to the session transcript file
        agent_name: Name of the agent (main, nox, sage, joy) - REQUIRED
        last_seen_timestamp: Timestamp of last processed entry (default 0)
    
    Returns:
        tuple: (activities list, latest_timestamp)
    """
    activities = []
    # Ensure last_seen_timestamp is numeric (not string from JSON)
    try:
        last_seen_timestamp = float(last_seen_timestamp) if last_seen_timestamp else 0
    except (ValueError, TypeError):
        last_seen_timestamp = 0
    latest_timestamp = last_seen_timestamp
    
    try:
        with open(session_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                except:
                    continue
                
                # Get entry timestamp (handle both int and ISO string timestamps)
                entry_timestamp = entry.get('timestamp', 0)
                try:
                    if isinstance(entry_timestamp, str):
                        # Parse ISO 8601 timestamp to Unix timestamp in ms
                        dt = datetime.fromisoformat(entry_timestamp.replace('Z', '+00:00'))
                        entry_timestamp = dt.timestamp() * 1000
                    else:
                        entry_timestamp = float(entry_timestamp) if entry_timestamp else 0
                except (ValueError, TypeError):
                    entry_timestamp = 0
                
                # Skip if we've already processed this entry
                # Ensure BOTH operands are float before comparison to avoid type errors
                try:
                    entry_ts = float(entry_timestamp) if entry_timestamp else 0
                except (ValueError, TypeError):
                    entry_ts = 0
                try:
                    last_ts = float(last_seen_timestamp) if last_seen_timestamp else 0
                except (ValueError, TypeError):
                    last_ts = 0
                
                if entry_ts <= last_ts:
                    continue
                
                # Track latest timestamp we've seen
                if entry_timestamp > latest_timestamp:
                    latest_timestamp = entry_timestamp
                
                # Use the agent_name passed from scan_sessions()
                agent = agent_name
                
                # Look for assistant messages with tool calls
                # Handle both direct role or nested in message object
                message = entry.get('message', entry)
                if message.get('role') == 'assistant':
                    content = message.get('content', [])
                    
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'toolCall':
                            tool_name = item.get('name', '')
                            tool_args = item.get('arguments', {})
                            
                            # Create activity from tool call
                            activity = classify_tool_activity(tool_name, tool_args, agent, entry)
                            if activity:
                                activities.append(activity)
                        
                        # Check for text content mentioning key actions
                        elif isinstance(item, dict) and item.get('type') == 'text':
                            text = item.get('text', '').lower()
                            
                            # Detect subagent spawns
                            if 'sessions_spawn' in text or 'spawned subagent' in text:
                                activities.append({
                                    'type': 'subagent_spawn',
                                    'agent': agent,
                                    'description': f"Spawned subagent for background task",
                                    'timestamp': entry_timestamp
                                })
    
    except Exception as e:
        logger.error(f"Error parsing {session_file.name}: {e}")
        print(f"  ⚠️  Error parsing {session_file.name}: {e}")
    
    return activities, latest_timestamp

def classify_tool_activity(tool_name, tool_args, agent, entry):
    """Classify a tool call into an activity type."""
    timestamp = entry.get('timestamp', time.time() * 1000)
    
    # File operations
    if tool_name in ['write', 'Write']:
        file_path = tool_args.get('path') or tool_args.get('file_path', '')
        return {
            'type': 'file_write',
            'agent': agent,
            'description': f"Created/updated file: {Path(file_path).name}",
            'timestamp': timestamp,
            'file': file_path
        }
    
    elif tool_name in ['edit', 'Edit']:
        file_path = tool_args.get('path') or tool_args.get('file_path', '')
        return {
            'type': 'file_edit',
            'agent': agent,
            'description': f"Edited file: {Path(file_path).name}",
            'timestamp': timestamp,
            'file': file_path
        }
    
    # Exec/shell commands
    elif tool_name == 'exec':
        command = tool_args.get('command', '')
        # Skip trivial commands
        if any(cmd in command for cmd in ['echo', 'ls', 'cat', 'pwd', 'sleep']):
            return None
        
        # Detect script execution
        if '.py' in command or '.sh' in command:
            return {
                'type': 'script_execution',
                'agent': agent,
                'description': f"Executed script/command: {command[:60]}",
                'timestamp': timestamp
            }
    
    # Browser automation
    elif tool_name == 'browser':
        action = tool_args.get('action', '')
        return {
            'type': 'browser_automation',
            'agent': agent,
            'description': f"Browser action: {action}",
            'timestamp': timestamp
        }
    
    # Web research
    elif tool_name in ['web_search', 'web_fetch']:
        query = tool_args.get('query') or tool_args.get('url', '')
        return {
            'type': 'web_research',
            'agent': agent,
            'description': f"Web research: {query[:60]}",
            'timestamp': timestamp
        }
    
    # Subagent spawning
    elif tool_name == 'sessions_spawn':
        task = tool_args.get('task', '')[:60]
        return {
            'type': 'subagent_spawn',
            'agent': agent,
            'description': f"Spawned subagent: {task}",
            'timestamp': timestamp
        }
    
    # Message/communication
    elif tool_name == 'message':
        action = tool_args.get('action', '')
        return {
            'type': 'communication',
            'agent': agent,
            'description': f"Message action: {action}",
            'timestamp': timestamp
        }
    
    # Cron job management
    elif tool_name == 'cron':
        action = tool_args.get('action', '')
        return {
            'type': 'automation_config',
            'agent': agent,
            'description': f"Cron management: {action}",
            'timestamp': timestamp
        }
    
    return None

def scan_sessions():
    """Scan session files for new activities since last check."""
    global SESSION_TIMESTAMPS
    
    new_activities = []
    
    # Scan ALL agent directories
    for sessions_dir in AGENT_DIRS:
        if not sessions_dir.exists():
            continue
            
        agent_name = sessions_dir.parent.name  # Extract agent name from path
        
        # Get all .jsonl files in sessions directory
        session_files = list(sessions_dir.glob("*.jsonl"))
        
        for session_file in session_files:
            session_id = f"{agent_name}:{session_file.stem}"  # Prefix with agent name
            
            # Get last timestamp we saw for this session
            last_seen_timestamp = SESSION_TIMESTAMPS.get(session_id, 0)
            
            # Check file modification time - skip if file hasn't changed since last check
            file_mtime = session_file.stat().st_mtime * 1000  # Convert to ms
            if file_mtime <= last_seen_timestamp:
                continue
            
            # Skip if file is too old (>7 days) AND we've already processed it
            file_age_days = (time.time() - session_file.stat().st_mtime) / 86400
            if file_age_days > 7 and last_seen_timestamp > 0:
                continue
            
            # Parse session for new activity
            print(f"  📝 Scanning {agent_name}: {session_file.stem[:12]}...")
            logger.info(f"Scanning session: agent={agent_name}, session={session_file.stem[:12]}")
            
            # Pass agent_name explicitly to ensure correct attribution
            activities, latest_timestamp = parse_session_transcript(
                session_file, 
                agent_name=agent_name, 
                last_seen_timestamp=last_seen_timestamp
            )
            
            if activities:
                # Log activities by agent for debugging
                agent_counts = {}
                for act in activities:
                    a = act.get('agent', 'unknown')
                    agent_counts[a] = agent_counts.get(a, 0) + 1
                
                logger.info(f"Found {len(activities)} activities from {agent_name}: {agent_counts}")
                print(f"     ✅ Found {len(activities)} new activities ({agent_counts})")
                new_activities.extend(activities)
            
            # Update last-seen timestamp for this session
            if latest_timestamp > last_seen_timestamp:
                SESSION_TIMESTAMPS[session_id] = latest_timestamp
    
    return new_activities

def convert_to_log_entry(activity):
    """Convert session activity to work log format."""
    timestamp_ms = activity.get('timestamp', time.time() * 1000)
    
    # Handle both numeric and ISO string timestamps
    if isinstance(timestamp_ms, str):
        # Already ISO format, use as-is
        timestamp_iso = timestamp_ms
        # Extract ms for ID
        dt = datetime.fromisoformat(timestamp_ms.replace('Z', '+00:00'))
        timestamp_ms = int(dt.timestamp() * 1000)
    else:
        # Convert numeric ms to ISO
        timestamp_iso = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()
    
    return {
        'id': f"session-{int(timestamp_ms)}",
        'timestamp': timestamp_iso,
        'agent': activity['agent'],
        'type': activity['type'],
        'project': 'session_activity',
        'description': activity['description'],
        'source': 'session_monitor'
    }

def load_meta():
    """Load meta.json file."""
    meta_file = Path(__file__).parent / "data" / "meta.json"
    if meta_file.exists():
        with open(meta_file, 'r') as f:
            return json.load(f)
    return {
        "lastUpdated": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "syncStatus": "active",
        "cacheBust": "v0000",
        "totalActivities": 0,
        "totalEntries": 0
    }

def save_meta(meta_data):
    """Save meta.json file."""
    meta_file = Path(__file__).parent / "data" / "meta.json"
    with open(meta_file, 'w') as f:
        json.dump(meta_data, f, indent=2)

def main():
    """Main entry point for session monitoring."""
    global SESSION_TIMESTAMPS
    
    logger.info("=" * 60)
    logger.info("SESSION ACTIVITY MONITOR STARTED")
    logger.info("Scanning agents: main, nox, sage, joy")
    
    print("🔍 SESSION ACTIVITY MONITOR")
    print(f"   Scanning agents: main, nox, sage, joy")
    print("=" * 60)
    
    # Load session timestamps cache
    SESSION_TIMESTAMPS = load_session_timestamps()
    logger.info(f"Loaded {len(SESSION_TIMESTAMPS)} session timestamps from cache")
    print(f"📋 Tracking {len(SESSION_TIMESTAMPS)} sessions")
    
    # Load meta.json
    meta_data = load_meta()
    logger.info(f"Loaded meta.json: {meta_data.get('totalActivities', 0)} total activities")
    
    # Scan for new activities
    logger.info("Starting session scan...")
    activities = scan_sessions()
    
    if activities:
        logger.info(f"Found {len(activities)} total new activities from all sessions")
        print(f"\n✅ Found {len(activities)} new activities from sessions")
        
        # Convert to log format
        log_entries = [convert_to_log_entry(a) for a in activities]
        logger.info(f"Converted {len(log_entries)} activities to log entries")
        
        # Load existing activity log
        log_file = Path(__file__).parent / "data" / "activity-log.json"
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        # Add new entries
        initial_count = len(log_data['entries'])
        log_data['entries'].extend(log_entries)
        
        # Sort by timestamp
        log_data['entries'].sort(key=lambda x: x['timestamp'])
        
        # Update total count
        log_data['totalEntries'] = len(log_data['entries'])
        
        # Save back
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"Updated activity-log.json: {initial_count} → {log_data['totalEntries']} entries")
        print(f"💾 Updated activity-log.json ({len(log_entries)} new entries)")
        
        # Update meta.json with fresh timestamp and counts
        now = datetime.now(timezone.utc)
        timestamp_iso = now.isoformat().replace('+00:00', 'Z')
        cache_bust = f"v{now.strftime('%m%d%H%M%S')}"
        
        meta_data['lastUpdated'] = timestamp_iso
        meta_data['totalActivities'] = len(log_data['entries'])
        meta_data['totalEntries'] = len(log_data['entries'])
        meta_data['cacheBust'] = cache_bust
        
        save_meta(meta_data)
        print(f"💾 Updated meta.json (timestamp: {timestamp_iso})")
        
        # POST each new entry directly to Railway API for instant real-time update
        # (bypasses git → Railway redeploy pipeline which takes 1-3 minutes)
        import urllib.request, urllib.error
        RAILWAY_API = "https://nox-work-tracker-production.up.railway.app/api/activities"
        posted, failed = 0, 0
        for entry in log_entries:
            try:
                payload = json.dumps(entry).encode()
                req = urllib.request.Request(
                    RAILWAY_API, data=payload,
                    headers={"Content-Type": "application/json"}, method="POST"
                )
                urllib.request.urlopen(req, timeout=5)
                posted += 1
            except Exception as e:
                failed += 1
                logger.warning(f"Railway POST failed for entry {entry.get('id')}: {e}")
        logger.info(f"Railway API: posted {posted}, failed {failed}")
        print(f"🚀 Railway API: {posted} entries posted live ({failed} failed)")

        # Git commit and push (background backup — keeps history, not on hot path)
        import subprocess
        repo_dir = Path(__file__).parent
        try:
            logger.info("Starting git operations...")
            subprocess.run(['git', 'add', 'data/activity-log.json', 'data/meta.json', '.processed_sessions.json'], 
                          cwd=repo_dir, check=True, capture_output=True)
            logger.info("Git add completed")
            
            commit_msg = f"[auto] Session monitor: {len(log_entries)} new activities"
            subprocess.run(['git', 'commit', '-m', commit_msg], 
                          cwd=repo_dir, check=True, capture_output=True)
            logger.info(f"Git commit completed: {commit_msg}")
            
            subprocess.run(['git', 'push', 'origin', 'main'], 
                          cwd=repo_dir, check=True, capture_output=True)
            logger.info("Git push completed")
            
            print(f"✅ Committed and pushed to GitHub (backup)")
        except subprocess.CalledProcessError as e:
            logger.error(f"Git error: {e}")
            print(f"⚠️  Git error: {e}")
    else:
        logger.info("No new activities found")
        print("ℹ️  No new activities found")
    
    # Save session timestamps cache
    save_session_timestamps()
    logger.info(f"Saved {len(SESSION_TIMESTAMPS)} session timestamps to cache")

    # Auto-sync pixel office state from activity log
    # No manual scripts — state is derived from recent activity detection
    sync_pixel_office_state(activities)

    logger.info("Session scan complete")
    print("✅ Session scan complete\n")
    return len(activities)


def sync_pixel_office_state(new_activities):
    """
    Auto-update pixel office agent positions based on activity log.
    - Agent has new activity this run  → state = 'writing' (at desk)
    - Agent has no recent activity (>15 min) → state = 'idle' (breakroom)
    No manual state.py scripts needed.
    """
    import urllib.request
    import urllib.error

    API_URL = "https://nox-work-tracker-production.up.railway.app/api/agent-states"
    ACTIVITY_WINDOW_SECONDS = 15 * 60  # 15 minutes

    AGENT_NAME_MAP = {
        'main': 'Nox',
        'nox':  'Nox',
        'sage': 'Sage',
        'joy':  'Joy',
    }
    AGENT_EMOJI = {
        'Nox': '⚡',
        'Sage': '🌿',
        'Joy': '✨',
    }

    # Agents that have new activity this run
    active_this_run = set()
    for a in (new_activities or []):
        raw = (a.get('agent') or '').lower()
        name = AGENT_NAME_MAP.get(raw)
        if name:
            active_this_run.add(name)

    # Check activity-log.json for recent activity per agent
    log_file = Path(__file__).parent / "data" / "activity-log.json"
    recent_agents = set()
    try:
        with open(log_file) as f:
            log_data = json.load(f)
        now_ts = datetime.now(timezone.utc).timestamp()
        for entry in log_data.get('entries', []):
            try:
                ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')).timestamp()
                if now_ts - ts <= ACTIVITY_WINDOW_SECONDS:
                    raw = (entry.get('agent') or '').lower()
                    name = AGENT_NAME_MAP.get(raw)
                    if name:
                        recent_agents.add(name)
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Could not read activity log for pixel office sync: {e}")
        return

    # Fetch current states to avoid unnecessary writes
    try:
        with urllib.request.urlopen(API_URL, timeout=5) as resp:
            current_states = {s['name']: s.get('state', 'idle') for s in json.loads(resp.read())}
    except Exception:
        current_states = {}

    # Determine desired state for each known agent
    for agent_name in ('Nox', 'Sage', 'Joy'):
        desired = 'writing' if agent_name in recent_agents else 'idle'
        detail  = 'Recently active' if desired == 'writing' else 'Standing by'
        current = current_states.get(agent_name, 'idle')

        if desired == current:
            continue  # No change needed

        payload = json.dumps({
            'name':   agent_name,
            'emoji':  AGENT_EMOJI.get(agent_name, ''),
            'state':  desired,
            'detail': detail,
        }).encode()
        try:
            req = urllib.request.Request(
                API_URL, data=payload,
                headers={'Content-Type': 'application/json'}, method='POST'
            )
            urllib.request.urlopen(req, timeout=5)
            logger.info(f"Pixel office: {agent_name} → {desired}")
            print(f"🏢 Pixel office: {agent_name} → {desired} ({detail})")
        except urllib.error.URLError as e:
            logger.warning(f"Pixel office sync failed for {agent_name}: {e}")


if __name__ == "__main__":
    main()
