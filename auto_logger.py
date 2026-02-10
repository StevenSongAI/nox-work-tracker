"""
Auto Work Tracker - Automatic activity logging for Nox
Call this after EVERY task completion to log work automatically
"""
import json
import os
import subprocess
from datetime import datetime
from typing import Dict, Optional, List
import sys

# Constants
WORK_TRACKER_PATH = "/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo"
ACTIVITY_LOG_PATH = os.path.join(WORK_TRACKER_PATH, "data", "activity-log.json")
META_PATH = os.path.join(WORK_TRACKER_PATH, "data", "meta.json")


def log_activity(
    activity_type: str,
    description: str,
    details: Optional[Dict] = None,
    agent: str = "nox",
    auto_commit: bool = True
) -> bool:
    """
    Log an activity to the work tracker.
    
    Args:
        activity_type: Type of activity (e.g., 'script_build', 'research', 'analysis')
        description: Human-readable description of what was done
        details: Optional dict with additional details
        agent: Agent name (default: 'nox')
        auto_commit: Whether to auto-commit and push (default: True)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read current activity log
        with open(ACTIVITY_LOG_PATH, 'r') as f:
            data = json.load(f)
        
        # Create new entry
        new_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": activity_type,
            "description": description,
            "details": details or {},
            "agent": agent,
            "session": "main"  # or could pass session ID
        }
        
        # Add to entries
        data["entries"].append(new_entry)
        
        # Read and update meta
        with open(META_PATH, 'r') as f:
            meta = json.load(f)
        
        meta["lastUpdated"] = datetime.utcnow().isoformat() + "Z"
        meta["totalActivities"] = len(data["entries"])
        
        # Save files
        with open(ACTIVITY_LOG_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        
        with open(META_PATH, 'w') as f:
            json.dump(meta, f, indent=2)
        
        print(f"✅ Activity logged: {activity_type}")
        print(f"   Description: {description[:60]}...")
        print(f"   Total activities: {meta['totalActivities']}")
        
        # Auto-commit and push
        if auto_commit:
            return _git_commit_and_push(activity_type, description)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to log activity: {e}")
        return False


def _git_commit_and_push(activity_type: str, description: str) -> bool:
    """Auto-commit and push changes to git"""
    try:
        os.chdir(WORK_TRACKER_PATH)
        
        # Check if there are changes
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True
        )
        
        if not result.stdout.strip():
            print("   No changes to commit")
            return True
        
        # Add changes
        subprocess.run(["git", "add", "."], check=True)
        
        # Commit with descriptive message
        commit_msg = f"[nox] {activity_type}: {description[:50]}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        # Push
        subprocess.run(["git", "push", "origin", "main"], check=True)
        
        print(f"   ✅ Committed and pushed to GitHub")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ⚠️ Git operation failed: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️ Commit failed: {e}")
        return False


def log_script_build(script_name: str, description: str, **kwargs):
    """Convenience function for logging script builds"""
    return log_activity(
        activity_type="script_build",
        description=f"Built {script_name}: {description}",
        details={"script": script_name, **kwargs}
    )


def log_research(topic: str, findings: str, source: str = "", **kwargs):
    """Convenience function for logging research"""
    return log_activity(
        activity_type="research",
        description=f"Research on {topic}: {findings[:100]}",
        details={"topic": topic, "source": source, **kwargs}
    )


def log_analysis(subject: str, result: str, **kwargs):
    """Convenience function for logging analysis work"""
    return log_activity(
        activity_type="analysis",
        description=f"Analysis of {subject}: {result[:100]}",
        details={"subject": subject, **kwargs}
    )


def log_cron_completion(cron_name: str, result: str, **kwargs):
    """Convenience function for logging cron job completion"""
    return log_activity(
        activity_type="cron_completion",
        description=f"Cron '{cron_name}' completed: {result}",
        details={"cron_name": cron_name, **kwargs}
    )


def log_dashboard_update(tab: str, items_added: int, description: str, **kwargs):
    """Convenience function for logging dashboard updates"""
    return log_activity(
        activity_type="dashboard_update",
        description=f"Dashboard [{tab}]: {description}",
        details={"tab": tab, "items_added": items_added, **kwargs}
    )


# If run directly, show usage
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python auto_logger.py <type> <description>")
        print("\nConvenience commands:")
        print("  python auto_logger.py script <script_name> <description>")
        print("  python auto_logger.py research <topic> <findings>")
        print("  python auto_logger.py analysis <subject> <result>")
        sys.exit(1)
    
    log_type = sys.argv[1]
    description = " ".join(sys.argv[2:])
    
    if log_type == "script":
        log_script_build(sys.argv[2], " ".join(sys.argv[3:]))
    elif log_type == "research":
        log_research(sys.argv[2], " ".join(sys.argv[3:]))
    elif log_type == "analysis":
        log_analysis(sys.argv[2], " ".join(sys.argv[3:]))
    else:
        log_activity(activity_type=log_type, description=description)
