#!/usr/bin/env python3
"""
Session Activity Monitor - Tracks OpenClaw agent activity from session transcripts
Monitors: tool calls, subagent spawns, file operations, browser automation, etc.

FIXED: Now tracks last-seen timestamp per session instead of marking entire sessions as "processed"
This allows continuous monitoring of ongoing long-running sessions.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import time

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
            return data
    return {}

def save_session_timestamps():
    """Save last-seen timestamps for each session."""
    with open(SESSIONS_CACHE_FILE, 'w') as f:
        json.dump(SESSION_TIMESTAMPS, f, indent=2)

def parse_session_transcript(session_file, last_seen_timestamp=0):
    """Parse a session transcript and extract activities AFTER last_seen_timestamp."""
    activities = []
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
                
                # Get entry timestamp (handle both int and string timestamps)
                entry_timestamp = entry.get('timestamp', 0)
                try:
                    entry_timestamp = float(entry_timestamp) if entry_timestamp else 0
                except (ValueError, TypeError):
                    entry_timestamp = 0
                
                # Skip if we've already processed this entry
                if entry_timestamp <= last_seen_timestamp:
                    continue
                
                # Track latest timestamp we've seen
                if entry_timestamp > latest_timestamp:
                    latest_timestamp = entry_timestamp
                
                # Extract agent from session label or content
                agent = "nox"  # Default
                if 'label' in entry:
                    label = entry['label'].lower()
                    if 'sage' in label or 'health' in label:
                        agent = "sage"
                    elif 'joy' in label or 'fun' in label:
                        agent = "joy"
                
                # Look for assistant messages with tool calls
                if entry.get('role') == 'assistant':
                    content = entry.get('content', [])
                    
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
            activities, latest_timestamp = parse_session_transcript(session_file, last_seen_timestamp)
            
            if activities:
                print(f"     ✅ Found {len(activities)} new activities")
                new_activities.extend(activities)
            
            # Update last-seen timestamp for this session
            if latest_timestamp > last_seen_timestamp:
                SESSION_TIMESTAMPS[session_id] = latest_timestamp
    
    return new_activities

def convert_to_log_entry(activity):
    """Convert session activity to work log format."""
    timestamp_ms = activity.get('timestamp', time.time() * 1000)
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

def main():
    """Main entry point for session monitoring."""
    global SESSION_TIMESTAMPS
    
    print("🔍 SESSION ACTIVITY MONITOR")
    print(f"   Scanning agents: main, nox, sage, joy")
    print("=" * 60)
    
    # Load session timestamps cache
    SESSION_TIMESTAMPS = load_session_timestamps()
    print(f"📋 Tracking {len(SESSION_TIMESTAMPS)} sessions")
    
    # Scan for new activities
    activities = scan_sessions()
    
    if activities:
        print(f"\n✅ Found {len(activities)} new activities from sessions")
        
        # Convert to log format
        log_entries = [convert_to_log_entry(a) for a in activities]
        
        # Save to temporary file for auto_tracker to pick up
        output_file = Path("/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo/.session_activities.json")
        with open(output_file, 'w') as f:
            json.dump(log_entries, f, indent=2)
        
        print(f"💾 Saved to {output_file}")
    else:
        print("ℹ️  No new activities found")
    
    # Save session timestamps cache
    save_session_timestamps()
    
    print("✅ Session scan complete\n")
    return len(activities)

if __name__ == "__main__":
    main()
