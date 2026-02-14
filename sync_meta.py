#!/usr/bin/env python3
"""
Force-sync both meta.json files with actual activity-log.json count
Run this when work tracker shows stale data
"""
import json
import os
from datetime import datetime, timezone

WORK_TRACKER_PATH = "/Users/stevenai/Desktop/Nox Builds/nox-work-tracker-repo"
ACTIVITY_LOG_PATH = os.path.join(WORK_TRACKER_PATH, "data", "activity-log.json")
DATA_META_PATH = os.path.join(WORK_TRACKER_PATH, "data", "meta.json")
ROOT_META_PATH = os.path.join(WORK_TRACKER_PATH, "meta.json")

def sync_meta_files():
    # Read actual activity count
    with open(ACTIVITY_LOG_PATH, 'r') as f:
        data = json.load(f)
    actual_count = len(data.get("entries", []))
    
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Update data/meta.json
    with open(DATA_META_PATH, 'r') as f:
        data_meta = json.load(f)
    
    old_data_count = data_meta.get("totalActivities", 0)
    data_meta["totalActivities"] = actual_count
    data_meta["totalEntries"] = actual_count
    data_meta["lastUpdated"] = now
    
    # Bump cache version
    current_cache = data_meta.get("cacheBust", "v0000")
    version_num = int(current_cache.replace("v", "")) + 1
    data_meta["cacheBust"] = f"v{version_num:04d}"
    
    with open(DATA_META_PATH, 'w') as f:
        json.dump(data_meta, f, indent=2)
    
    # Update root meta.json
    with open(ROOT_META_PATH, 'r') as f:
        root_meta = json.load(f)
    
    old_root_count = root_meta.get("totalActivities", 0)
    root_meta["totalActivities"] = actual_count
    root_meta["lastUpdated"] = now
    
    current_cache = root_meta.get("cacheBust", "v0000")
    version_num = int(current_cache.replace("v", "")) + 1
    root_meta["cacheBust"] = f"v{version_num:04d}"
    
    with open(ROOT_META_PATH, 'w') as f:
        json.dump(root_meta, f, indent=2)
    
    print(f"✅ Synced both meta.json files")
    print(f"   Activity count: {old_data_count} → {actual_count}")
    print(f"   Cache bust: {data_meta['cacheBust']}")
    print(f"   Last updated: {now}")
    
    # Git status
    os.chdir(WORK_TRACKER_PATH)
    os.system("git status --short")
    
    return actual_count

if __name__ == "__main__":
    sync_meta_files()
