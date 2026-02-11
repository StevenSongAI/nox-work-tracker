#!/usr/bin/env python3
"""
Session Activity Monitor - Tracks OpenClaw agent activity from session transcripts
Monitors: tool calls, subagent spawns, file operations, browser automation, etc.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import time

# Session transcript directory
SESSIONS_DIR = Path("/Users/stevenai/.openclaw/agents/main/sessions")

# Track which sessions we've already processed
PROCESSED_SESSIONS = set()
SESSIONS_CACHE_FILE = Path("/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo/.processed_sessions.json")

def load_processed_sessions():
    """Load set of session IDs we've already processed."""
    if SESSIONS_CACHE_FILE.exists():
        with open(SESSIONS_CACHE_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_processed_sessions():
    """Save processed session IDs."""
    with open(SESSIONS_CACHE_FILE, 'w') as f:
        json.dump(list(PROCESSED_SESSIONS), f, indent=2)

def parse_session_transcript(session_file):
    """Parse a session transcript and extract activities."""
    activities = []
    
    try:
        with open(session_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                except:
                    continue
                
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
                                    'timestamp': entry.get('timestamp', time.time() * 1000)
                                })
    
    except Exception as e:
        print(f"  ⚠️  Error parsing {session_file.name}: {e}")
    
    return activities

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
        if command in ['echo', 'ls', 'cat', 'pwd']:
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

def scan_new_sessions():
    """Scan for new session files and extract activities."""
    global PROCESSED_SESSIONS
    
    new_activities = []
    
    # Get all .jsonl files in sessions directory
    session_files = list(SESSIONS_DIR.glob("*.jsonl"))
    
    for session_file in session_files:
        session_id = session_file.stem
        
        # Skip if already processed
        if session_id in PROCESSED_SESSIONS:
            continue
        
        # Skip if file is too old (>7 days)
        file_age_days = (time.time() - session_file.stat().st_mtime) / 86400
        if file_age_days > 7:
            PROCESSED_SESSIONS.add(session_id)
            continue
        
        # Parse session
        print(f"  📝 Parsing session: {session_id}")
        activities = parse_session_transcript(session_file)
        
        if activities:
            print(f"     Found {len(activities)} activities")
            new_activities.extend(activities)
        
        # Mark as processed
        PROCESSED_SESSIONS.add(session_id)
    
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
    global PROCESSED_SESSIONS
    
    print("🔍 SESSION ACTIVITY MONITOR")
    print(f"   Sessions dir: {SESSIONS_DIR}")
    print("=" * 60)
    
    # Load processed sessions cache
    PROCESSED_SESSIONS = load_processed_sessions()
    print(f"📋 Previously processed: {len(PROCESSED_SESSIONS)} sessions")
    
    # Scan for new activities
    activities = scan_new_sessions()
    
    if activities:
        print(f"\n✅ Found {len(activities)} new activities from sessions")
        
        # Convert to log format
        log_entries = [convert_to_log_entry(a) for a in activities]
        
        # Save to temporary file for git_monitor to pick up
        output_file = Path("/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo/.session_activities.json")
        with open(output_file, 'w') as f:
            json.dump(log_entries, f, indent=2)
        
        print(f"💾 Saved to {output_file}")
    else:
        print("ℹ️  No new activities found")
    
    # Save processed sessions cache
    save_processed_sessions()
    
    print("✅ Session scan complete\n")
    return len(activities)

if __name__ == "__main__":
    main()
