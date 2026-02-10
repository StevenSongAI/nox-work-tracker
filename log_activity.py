#!/usr/bin/env python3
import json
from datetime import datetime

# Read current activity log
with open('data/activity-log.json', 'r') as f:
    data = json.load(f)

# Add new activity
new_activity = {
    "id": f"act-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
    "timestamp": datetime.utcnow().isoformat() + 'Z',
    "type": "research",
    "project": "nox-dashboard",
    "description": "YouTube Outlier Research - Hourly cron: Added 8 new outlier videos from viewstats.com (yt-viewstats-104 through yt-viewstats-111)",
    "details": {
        "source": "viewstats.com/pro/outliers",
        "searches": ["AI creature", "dragon pet", "creature evolution"],
        "videosAdded": 8,
        "highlights": [
            "86.6x - Alice vs Nemesis (Resident Evil)",
            "24.5x - Zombified Dogs Chase (Resident Evil)",
            "14.5x - Strongest Flying Dragon Evolved",
            "11.7x - He Found a Real Dragon",
            "10.4x - Super Cute Dragon ASMR",
            "10.2x - Dragon Grows Up 2024",
            "9.2x - Brainrot Evolution in Roblox",
            "8.9x - With Cute Dragon ASMR"
        ],
        "totalOutliersInDashboard": 114
    },
    "automated": True,
    "source": "cron"
}

data['activities'].append(new_activity)

# Update meta
if 'meta' not in data:
    data['meta'] = {}
data['meta']['lastUpdated'] = datetime.utcnow().isoformat() + 'Z'
data['meta']['totalActivities'] = len(data['activities'])

# Write updated data
with open('data/activity-log.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"Activity logged: {new_activity['id']}")
print(f"Total activities: {data['meta']['totalActivities']}")
