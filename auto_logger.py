"""
Auto Work Tracker - Automatic activity logging for Nox
Call this after EVERY task completion to log work automatically

Now uses Dashboard API with git fallback.
"""
import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Dict, Optional, List
import sys

# DEFECT-001 FIX: ImportError with diagnostics logging
api_logger = None
try:
    import api_logger as _api_logger
    api_logger = _api_logger
except ImportError as e:
    import_error_msg = str(e)
    print(f"⚠️  api_logger import failed: {import_error_msg}")
    print(f"   Falling back to git-based logging only.")
    api_logger = None

# Constants
WORK_TRACKER_PATH = "/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo"
ACTIVITY_LOG_PATH = os.path.join(WORK_TRACKER_PATH, "data", "activity-log.json")
META_PATH = os.path.join(WORK_TRACKER_PATH, "data", "meta.json")
ROOT_META_PATH = os.path.join(WORK_TRACKER_PATH, "meta.json")


def _detect_agent_from_session() -> str:
    """
    Auto-detect agent name from session path.
    Pattern: ~/.openclaw/sessions/{agent}_{id}/
    Defaults to 'main' if unable to detect.
    """
    try:
        # Check if running in a session with identifiable path
        cwd = os.getcwd()
        if '.openclaw/sessions/' in cwd:
            # Extract agent from path like: ~/.openclaw/sessions/nox_abc123/
            parts = cwd.split('.openclaw/sessions/')
            if len(parts) > 1:
                session_part = parts[1].split('/')[0]
                # Session format: {agent}_{id}
                if '_' in session_part:
                    agent = session_part.split('_')[0]
                    return agent.lower()
        
        # Check environment variable
        agent = os.environ.get('OPENCLAW_AGENT')
        if agent:
            return agent.lower()
        
        # Default to 'main' if no session detected
        return 'main'
    except Exception:
        return 'main'


def _get_git_hash() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=WORK_TRACKER_PATH
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _ensure_data_file_exists():
    """DEFECT-003 FIX: Ensure activity-log.json exists with proper structure."""
    data_dir = os.path.dirname(ACTIVITY_LOG_PATH)
    
    # Ensure data directory exists
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        print(f"   📁 Created data directory: {data_dir}")
    
    # Ensure activity-log.json exists
    if not os.path.exists(ACTIVITY_LOG_PATH):
        initial_data = {"entries": []}
        with open(ACTIVITY_LOG_PATH, 'w') as f:
            json.dump(initial_data, f, indent=2)
        print(f"   📄 Created activity-log.json")
        return True
    
    return False


def _fallback_git_log(activity_type: str, title: str, description: str, **kwargs) -> bool:
    """Fallback to git-based logging when API fails."""
    try:
        print(f"   🔄 Falling back to git logging...")
        
        # DEFECT-003 FIX: Ensure file exists before reading
        _ensure_data_file_exists()
        
        # Read current activity log (now guaranteed to exist)
        with open(ACTIVITY_LOG_PATH, 'r') as f:
            data = json.load(f)
        
        # DEFECT-006 FIX: Standardized entry format matching API structure
        new_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "category": kwargs.get('category', 'youtube'),
            "type": activity_type,
            "title": title,
            "content": description,
            "source": kwargs.get('source', 'auto-logger'),
            "confidence": kwargs.get('confidence', 80),
            "metadata": kwargs,
            "verified": True,
            "agent": _detect_agent_from_session(),
            "session": "main"
        }
        
        # Add to entries
        if "entries" not in data:
            data["entries"] = []
        data["entries"].append(new_entry)
        
        # Ensure meta.json exists
        if not os.path.exists(META_PATH):
            meta = {
                "lastUpdated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "totalActivities": 0
            }
            with open(META_PATH, 'w') as f:
                json.dump(meta, f, indent=2)
        
        # Read and update meta
        with open(META_PATH, 'r') as f:
            meta = json.load(f)
        
        meta["lastUpdated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        meta["totalActivities"] = len(data["entries"])
        
        # Save files
        with open(ACTIVITY_LOG_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        
        with open(META_PATH, 'w') as f:
            json.dump(meta, f, indent=2)
        
        # Also update root meta.json if it exists
        if os.path.exists(ROOT_META_PATH):
            try:
                with open(ROOT_META_PATH, 'r') as f:
                    root_meta = json.load(f)
                root_meta["lastUpdated"] = meta["lastUpdated"]
                root_meta["totalActivities"] = meta["totalActivities"]
                if "cacheBust" in root_meta:
                    try:
                        cache_str = root_meta["cacheBust"].replace("v", "").split("-")[0]
                        version_num = int(cache_str) + 1
                        root_meta["cacheBust"] = f"v{version_num:04d}"
                    except ValueError:
                        root_meta["cacheBust"] = f"v{datetime.now().strftime('%m%d%H%M')}"
                with open(ROOT_META_PATH, 'w') as f:
                    json.dump(root_meta, f, indent=2)
            except Exception as e:
                print(f"   ⚠️ Could not update root meta.json: {e}")
        
        # Commit to git
        return _git_commit_and_push(activity_type, description)
        
    except FileNotFoundError as e:
        print(f"❌ FileNotFoundError in fallback logging: {e}")
        return False
    except Exception as e:
        print(f"❌ Fallback git logging failed: {e}")
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


def log_activity(
    activity_type: str,
    description: str,
    details: Optional[Dict] = None,
    agent: str = None,
    auto_commit: bool = True
) -> bool:
    """
    Log an activity - uses API with git fallback.
    
    Args:
        activity_type: Type of activity (e.g., 'script_build', 'research', 'analysis')
        description: Human-readable description of what was done
        details: Optional dict with additional details
        agent: Agent name (auto-detected from session path if None)
        auto_commit: Whether to auto-commit and push (default: True)
    
    Returns:
        True if successful, False otherwise
    """
    # Auto-detect agent from session path if not provided
    if agent is None:
        agent = _detect_agent_from_session()
    
    agent = agent.lower() if agent else 'main'
    
    # Get git info for metadata
    commit_hash = _get_git_hash()[:8]
    metadata = {
        'git_commit': commit_hash,
        'auto_logged': True,
        'agent': agent,
        **(details or {})
    }
    
    # Try API first if available
    if api_logger is not None:
        try:
            # DEFECT-002 FIX: Check success boolean from create_entry
            success, result = api_logger.create_entry(
                category='youtube',
                type=activity_type,
                title=f'{activity_type}: {description[:50]}',
                content=description,
                metadata=metadata
            )
            
            if success:
                print(f"✅ Activity logged to dashboard: {activity_type}")
                print(f"   Description: {description[:60]}...")
                return True
            else:
                print(f"⚠️  API logging failed, falling back to git...")
        except Exception as e:
            print(f"⚠️  API error: {e}, falling back to git...")
    
    # Fallback to git logging
    return _fallback_git_log(activity_type, activity_type, description, **metadata)


def log_script_build(script_name: str, description: str, **kwargs):
    """Log a script build - posts to dashboard API with git fallback."""
    commit_hash = _get_git_hash()[:8]
    
    metadata = {
        'git_commit': commit_hash,
        'script_name': script_name,
        'auto_logged': True,
        **kwargs
    }
    
    # Try API first
    if api_logger is not None:
        try:
            # DEFECT-002 FIX: Check success boolean from create_entry
            success, result = api_logger.create_entry(
                category='youtube',
                type='script_build',
                title=f'Script: {script_name}',
                content=description,
                metadata=metadata
            )
            
            if success:
                print(f"✅ Script build logged to dashboard: {script_name}")
                return result
            else:
                print(f"⚠️  Failed to log to dashboard, falling back to git")
        except Exception as e:
            print(f"⚠️  API error: {e}, falling back to git")
    
    # Fallback to git
    return _fallback_git_log('script_build', script_name, description, **metadata)


def log_research(topic: str, findings: str, source: str = "", **kwargs):
    """Log research - posts to dashboard API with git fallback."""
    commit_hash = _get_git_hash()[:8]
    
    metadata = {
        'git_commit': commit_hash,
        'topic': topic,
        'source': source,
        'auto_logged': True,
        **kwargs
    }
    
    # Try API first
    if api_logger is not None:
        try:
            # DEFECT-002 FIX: Check success boolean from create_entry
            success, result = api_logger.create_entry(
                category='youtube',
                type='research_note',
                title=f'Research: {topic}',
                content=findings,
                metadata=metadata
            )
            
            if success:
                print(f"✅ Research logged to dashboard: {topic}")
                return result
            else:
                print(f"⚠️  Failed to log to dashboard, falling back to git")
        except Exception as e:
            print(f"⚠️  API error: {e}, falling back to git")
    
    # Fallback to git
    return _fallback_git_log('research', topic, findings, **metadata)


def log_analysis(subject: str, result: str, **kwargs):
    """Log analysis - posts to dashboard API with git fallback."""
    commit_hash = _get_git_hash()[:8]
    
    metadata = {
        'git_commit': commit_hash,
        'subject': subject,
        'auto_logged': True,
        **kwargs
    }
    
    # Try API first
    if api_logger is not None:
        try:
            # DEFECT-002 FIX: Check success boolean from create_entry
            success, api_result = api_logger.create_entry(
                category='business',
                type='analysis',
                title=f'Analysis: {subject}',
                content=result,
                metadata=metadata
            )
            
            if success:
                print(f"✅ Analysis logged to dashboard: {subject}")
                return api_result
            else:
                print(f"⚠️  Failed to log to dashboard, falling back to git")
        except Exception as e:
            print(f"⚠️  API error: {e}, falling back to git")
    
    # Fallback to git
    return _fallback_git_log('analysis', subject, result, **metadata)


def log_cron_completion(cron_name: str, result: str, **kwargs):
    """Log a cron job completion - posts to dashboard API with git fallback."""
    commit_hash = _get_git_hash()[:8]
    
    metadata = {
        'git_commit': commit_hash,
        'cron_name': cron_name,
        'auto_logged': True,
        **kwargs
    }
    
    description = f"Cron '{cron_name}' completed: {result}"
    
    # Try API first
    if api_logger is not None:
        try:
            # DEFECT-002 FIX: Check success boolean from create_entry
            success, api_result = api_logger.create_entry(
                category='business',
                type='cron_completion',
                title=f'Cron: {cron_name}',
                content=description,
                metadata=metadata
            )
            
            if success:
                print(f"✅ Cron completion logged to dashboard: {cron_name}")
                return api_result
            else:
                print(f"⚠️  Failed to log to dashboard, falling back to git")
        except Exception as e:
            print(f"⚠️  API error: {e}, falling back to git")
    
    # Fallback to git
    return _fallback_git_log('cron_completion', cron_name, description, **metadata)


def log_dashboard_update(tab: str, items_added: int, description: str, **kwargs):
    """Log a dashboard update - posts to dashboard API with git fallback."""
    commit_hash = _get_git_hash()[:8]
    
    metadata = {
        'git_commit': commit_hash,
        'tab': tab,
        'items_added': items_added,
        'auto_logged': True,
        **kwargs
    }
    
    full_description = f"Dashboard [{tab}]: {description}"
    
    # Try API first
    if api_logger is not None:
        try:
            # DEFECT-002 FIX: Check success boolean from create_entry
            success, api_result = api_logger.create_entry(
                category='youtube',
                type='dashboard_update',
                title=f'Dashboard Update: {tab}',
                content=full_description,
                metadata=metadata
            )
            
            if success:
                print(f"✅ Dashboard update logged to dashboard: {tab}")
                return api_result
            else:
                print(f"⚠️  Failed to log to dashboard, falling back to git")
        except Exception as e:
            print(f"⚠️  API error: {e}, falling back to git")
    
    # Fallback to git
    return _fallback_git_log('dashboard_update', tab, full_description, **metadata)


# If run directly, show usage
if __name__ == "__main__":
    # DEFECT-007 FIX: Handle missing description gracefully
    if len(sys.argv) < 2:
        print("Usage: python auto_logger.py <type> [args...]")
        print("\nConvenience commands:")
        print("  python auto_logger.py script <script_name> [description]")
        print("  python auto_logger.py research <topic> [findings]")
        print("  python auto_logger.py analysis <subject> [result]")
        print("  python auto_logger.py <activity_type> <description>")
        sys.exit(1)
    
    log_type = sys.argv[1]
    
    # DEFECT-007 FIX: Handle missing arguments for all command types
    if log_type == "script":
        if len(sys.argv) < 3:
            print("❌ Error: script_name is required")
            print("Usage: python auto_logger.py script <script_name> [description]")
            sys.exit(1)
        script_name = sys.argv[2]
        description = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else f"Script build: {script_name}"
        log_script_build(script_name, description)
    elif log_type == "research":
        if len(sys.argv) < 3:
            print("❌ Error: topic is required")
            print("Usage: python auto_logger.py research <topic> [findings]")
            sys.exit(1)
        topic = sys.argv[2]
        findings = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else f"Research on {topic}"
        log_research(topic, findings)
    elif log_type == "analysis":
        if len(sys.argv) < 3:
            print("❌ Error: subject is required")
            print("Usage: python auto_logger.py analysis <subject> [result]")
            sys.exit(1)
        subject = sys.argv[2]
        result = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else f"Analysis of {subject}"
        log_analysis(subject, result)
    else:
        # Generic activity logging
        if len(sys.argv) < 3:
            print(f"❌ Error: description is required for activity type '{log_type}'")
            print(f"Usage: python auto_logger.py {log_type} <description>")
            sys.exit(1)
        description = " ".join(sys.argv[2:])
        log_activity(activity_type=log_type, description=description)
