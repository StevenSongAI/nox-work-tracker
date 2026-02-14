# OPUS DIAGNOSIS: Railway Stale Data Issue

## Executive Summary
**Root Cause:** Railway's `railway up` command is using **incremental/delta deployment** that only uploads ~154KB of changed files, while the full repo is 32MB. The `data/activity-log.json` file (2.6MB) is being excluded from uploads.

## Investigation Findings

### File Size Comparison
| Source | File Size | Status |
|--------|-----------|--------|
| Local file | 2,666,894 bytes (2.6MB) | ✅ CORRECT |
| GitHub HEAD commit | 2,666,894 bytes | ✅ CORRECT |
| GitHub raw CDN URL | ~9,273-49,273 bytes | ⚠️ STALE/CACHED |
| Railway serving | ~49,273 bytes | ❌ WRONG |

### Critical Discovery: GitHub CDN Cache Mismatch
- `git show HEAD:data/activity-log.json` returns 2.6MB (correct)
- `https://raw.githubusercontent.com/.../activity-log.json` returns 9-49KB (stale)
- GitHub API confirms file is 2,666,894 bytes with correct SHA
- **Conclusion:** GitHub's raw CDN is serving stale cached content

### Critical Discovery: Railway Upload Size
- `railway up --verbose` shows: "Uploading... 154,316 bytes"
- Full repo size: ~32MB
- Data directory size: 2.6MB
- **Conclusion:** Railway is using incremental deployment and NOT uploading the full activity-log.json

## Root Cause Analysis

### Why Manual Deployment Doesn't Fix It
1. **Incremental Deployment:** Railway CLI only uploads changed files since last deployment
2. **File Size Filtering:** Large JSON files may be excluded from delta uploads
3. **GitHub CDN Cache:** Raw URLs serve stale cached versions for large files
4. **Railway Caching:** Railway may cache deployment artifacts between builds

### Why Meta.json Updates Work
- Meta.json is small (~200 bytes)
- Gets uploaded in every incremental deployment
- Not affected by size-based filtering

## Recommended Fix Approaches

### Option 1: Force Full Redeploy (Quick Fix)
```bash
cd ~/Desktop/Nox\ Builds/nox-work-tracker-repo
railway redeploy --clean  # Force clean rebuild from scratch
```

### Option 2: Delete and Recreate Service (Nuclear Option)
1. Delete existing Railway service
2. Create new service from GitHub repo
3. Let Railway clone fresh from GitHub

### Option 3: Use GitHub Auto-Deploy (Recommended Long-term)
1. Configure Railway to auto-deploy from GitHub pushes
2. This bypasses the `railway up` incremental upload issue
3. Ensure GitHub webhook triggers fresh deployments

### Option 4: Split Large JSON Files
- Split activity-log.json into smaller chunks (e.g., by date)
- Avoids CDN caching issues with large files
- Better incremental update behavior

## Immediate Action Required
The fundamental issue is that **Railway CLI incremental uploads are NOT including the 2.6MB activity-log.json file**. A full clean deployment or service recreation is needed to force the file to be uploaded.

## Verification Steps After Fix
1. Check file size: `curl -s https://work-tracker-production-4f73.up.railway.app/data/activity-log.json | wc -c`
2. Should return ~2,666,894 bytes (not 49,273)
3. Check last entry date: Should be Feb 14, not Feb 8/9
4. Check total entries: Should be 9,173 entries

---
*Diagnosis written by subagent investigation*
*Date: February 14, 2026*
