"""
Agent Activity Monitor - Track work from Sage (Health) and Joy (Personal) agents
"""
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

AGENT_ACTIVITY_PATH = "/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo/data/agent_activity.json"

AGENT_WORKSPACES = {
    "sage": "/Users/stevenai/clawd-agents/health",
    "joy": "/Users/stevenai/clawd-agents/personal"
}

AGENT_INFO = {
    "sage": {"name": "Sage", "role": "Health", "emoji": "🌱"},
    "joy": {"name": "Joy", "role": "Personal", "emoji": "✨"},
    "nox": {"name": "Nox", "role": "Work", "emoji": "⚡"}
}


@dataclass
class AgentActivity:
    timestamp: str
    agent_id: str
    activity_type: str  # heartbeat, cron, subagent, research, analysis, etc.
    description: str
    details: Dict
    files_modified: List[str] = None
    
    def __post_init__(self):
        if self.files_modified is None:
            self.files_modified = []


class AgentMonitor:
    """Monitor and track activity from all agents"""
    
    def __init__(self):
        self.activity_path = AGENT_ACTIVITY_PATH
        self.activities: List[AgentActivity] = []
        self.load()
    
    def load(self):
        """Load activity log"""
        if os.path.exists(self.activity_path):
            with open(self.activity_path, 'r') as f:
                data = json.load(f)
                for act_dict in data.get('activities', []):
                    self.activities.append(AgentActivity(**act_dict))
    
    def save(self):
        """Save activity log"""
        os.makedirs(os.path.dirname(self.activity_path), exist_ok=True)
        data = {
            'activities': [asdict(a) for a in self.activities[-500:]],  # Keep last 500
            'last_updated': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        with open(self.activity_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def log_activity(self, agent_id: str, activity_type: str, description: str,
                     details: Dict = None, files_modified: List[str] = None):
        """Log an agent activity"""
        activity = AgentActivity(
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            agent_id=agent_id,
            activity_type=activity_type,
            description=description,
            details=details or {},
            files_modified=files_modified or []
        )
        
        self.activities.append(activity)
        self.save()
        
        agent_info = AGENT_INFO.get(agent_id, {"name": agent_id, "emoji": "🤖"})
        print(f"{agent_info['emoji']} {agent_info['name']}: {description}")
    
    def scan_agent_workspace(self, agent_id: str) -> List[Dict]:
        """Scan an agent's workspace for recent activity"""
        workspace = AGENT_WORKSPACES.get(agent_id)
        if not workspace or not os.path.exists(workspace):
            return []
        
        recent_changes = []
        
        # Check for recent memory files
        memory_dir = os.path.join(workspace, "memory")
        if os.path.exists(memory_dir):
            for filename in os.listdir(memory_dir):
                if filename.endswith('.md'):
                    filepath = os.path.join(memory_dir, filename)
                    mtime = os.path.getmtime(filepath)
                    age_hours = (datetime.now().timestamp() - mtime) / 3600
                    if age_hours < 24:  # Modified in last 24 hours
                        recent_changes.append({
                            'file': filepath,
                            'type': 'memory',
                            'age_hours': age_hours
                        })
        
        # Check git status for modified files
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=workspace,
                capture_output=True,
                text=True
            )
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        recent_changes.append({
                            'file': line[3:],
                            'type': 'git_modified',
                            'status': line[:2]
                        })
        except:
            pass
        
        return recent_changes
    
    def detect_agent_sessions(self) -> Dict[str, List[Dict]]:
        """Detect active agent sessions using openclaw status"""
        try:
            result = subprocess.run(
                ["openclaw", "sessions", "list", "--json"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {}
            
            data = json.loads(result.stdout)
            agent_sessions = {"sage": [], "joy": [], "nox": []}
            
            for session in data.get('sessions', []):
                key = session.get('key', '')
                if 'sage' in key:
                    agent_sessions['sage'].append(session)
                elif 'joy' in key:
                    agent_sessions['joy'].append(session)
                elif 'nox' in key and key != 'agent:nox:main':
                    agent_sessions['nox'].append(session)
            
            return agent_sessions
            
        except Exception as e:
            print(f"Error detecting sessions: {e}")
            return {}
    
    def check_cron_activity(self, agent_id: str) -> List[Dict]:
        """Check recent cron activity for an agent"""
        try:
            result = subprocess.run(
                ["openclaw", "cron", "list"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            # Parse cron list output (this is simplified - actual parsing would be more robust)
            cron_jobs = []
            # Would need to parse the JSON output properly
            return cron_jobs
            
        except Exception as e:
            print(f"Error checking cron activity: {e}")
            return []
    
    def generate_daily_summary(self) -> str:
        """Generate daily activity summary for all agents"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        today_activities = [
            a for a in self.activities 
            if a.timestamp.startswith(today)
        ]
        
        # Group by agent
        by_agent = {}
        for activity in today_activities:
            if activity.agent_id not in by_agent:
                by_agent[activity.agent_id] = []
            by_agent[activity.agent_id].append(activity)
        
        lines = []
        lines.append(f"# Agent Activity Summary - {today}")
        lines.append("")
        
        for agent_id, activities in by_agent.items():
            agent_info = AGENT_INFO.get(agent_id, {"name": agent_id, "emoji": "🤖", "role": "Unknown"})
            lines.append(f"## {agent_info['emoji']} {agent_info['name']} ({agent_info['role']})")
            lines.append(f"Total activities: {len(activities)}")
            
            # Group by type
            by_type = {}
            for act in activities:
                by_type[act.activity_type] = by_type.get(act.activity_type, 0) + 1
            
            for act_type, count in by_type.items():
                lines.append(f"  - {act_type}: {count}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def get_recent_activity(self, hours: int = 24) -> List[AgentActivity]:
        """Get activities from last N hours"""
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        
        return [
            a for a in self.activities
            if datetime.fromisoformat(a.timestamp.replace('Z', '+00:00')).timestamp() > cutoff
        ]


def monitor_all_agents():
    """Run full agent monitoring scan"""
    print("🔍 Scanning agent activity...")
    
    monitor = AgentMonitor()
    
    # Check each agent workspace
    for agent_id in ["sage", "joy"]:
        changes = monitor.scan_agent_workspace(agent_id)
        if changes:
            agent_info = AGENT_INFO.get(agent_id, {"name": agent_id})
            print(f"\n{agent_info['name']} recent changes:")
            for change in changes[:5]:  # Show top 5
                print(f"  - {change['file']} ({change.get('type', 'unknown')})")
    
    # Check active sessions
    sessions = monitor.detect_agent_sessions()
    for agent_id, agent_sessions in sessions.items():
        if agent_sessions:
            agent_info = AGENT_INFO.get(agent_id, {"name": agent_id})
            print(f"\n{agent_info['name']} active sessions: {len(agent_sessions)}")
            for session in agent_sessions[:3]:
                print(f"  - {session.get('label', 'Unknown')}")
    
    return monitor


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python agent_monitor.py <command>")
        print("\nCommands:")
        print("  scan           - Scan all agents for recent activity")
        print("  summary        - Generate daily summary")
        print("  log <agent> <type> <desc>")
        sys.exit(1)
    
    command = sys.argv[1]
    monitor = AgentMonitor()
    
    if command == "scan":
        monitor_all_agents()
    elif command == "summary":
        print(monitor.generate_daily_summary())
    elif command == "log" and len(sys.argv) >= 5:
        monitor.log_activity(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(f"Unknown command: {command}")
