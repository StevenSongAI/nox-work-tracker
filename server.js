const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const DATA_FILE = path.join(__dirname, 'data', 'activity-log.json');

// Ensure data directory exists
const dataDir = path.join(__dirname, 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

// Initialize empty activity log if not exists
if (!fs.existsSync(DATA_FILE)) {
  fs.writeFileSync(DATA_FILE, JSON.stringify({ entries: [] }, null, 2));
}

// Load activities into memory
let activities = [];
function loadActivities() {
  try {
    const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
    activities = data.entries || [];
    console.log(`Loaded ${activities.length} activities`);
  } catch (err) {
    console.error('Error loading activities:', err);
    activities = [];
  }
}

// Save activities to disk
function saveActivities() {
  try {
    fs.writeFileSync(DATA_FILE, JSON.stringify({ entries: activities }, null, 2));
  } catch (err) {
    console.error('Error saving activities:', err);
  }
}

// Deduplication: Check if similar entry exists in last 5 minutes
function isDuplicate(newEntry) {
  const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000);
  
  return activities.some(entry => {
    if (entry.agent !== newEntry.agent) return false;
    if (entry.type !== newEntry.type) return false;
    if (entry.description !== newEntry.description) return false;
    
    const entryTime = new Date(entry.timestamp);
    if (entryTime < fiveMinutesAgo) return false;
    
    return true;
  });
}

// Add new activity with deduplication
function addActivity(entry) {
  if (isDuplicate(entry)) {
    console.log(`Duplicate skipped: ${entry.description}`);
    return false;
  }
  
  activities.unshift(entry); // Add to beginning
  saveActivities();
  return true;
}

// Clean up old activities (keep last 7 days)
function cleanupOldActivities() {
  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  const originalCount = activities.length;
  
  activities = activities.filter(entry => {
    return new Date(entry.timestamp) >= sevenDaysAgo;
  });
  
  const removed = originalCount - activities.length;
  if (removed > 0) {
    console.log(`Cleaned up ${removed} old activities`);
    saveActivities();
  }
  return removed;
}

// Get paginated activities
function getActivities({ limit = 100, offset = 0, agent, type, sort = '-timestamp' }) {
  let result = [...activities];
  
  // Filter by agent
  if (agent) {
    result = result.filter(e => e.agent === agent);
  }
  
  // Filter by type
  if (type) {
    result = result.filter(e => e.type === type);
  }
  
  // Sort
  if (sort === '-timestamp') {
    result.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  } else if (sort === 'timestamp') {
    result.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  }
  
  // Get total before pagination
  const total = result.length;
  
  // Paginate
  result = result.slice(offset, offset + limit);
  
  return { entries: result, total, limit, offset };
}

// Get stats
function getStats() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  
  const agentCounts = {};
  const typeCounts = {};
  let todayCount = 0;
  let weekCount = 0;
  
  activities.forEach(a => {
    // Agent counts
    agentCounts[a.agent] = (agentCounts[a.agent] || 0) + 1;
    
    // Type counts
    typeCounts[a.type] = (typeCounts[a.type] || 0) + 1;
    
    // Today count
    if (new Date(a.timestamp) >= today) todayCount++;
    
    // Week count
    if (new Date(a.timestamp) >= weekAgo) weekCount++;
  });
  
  return {
    total: activities.length,
    today: todayCount,
    thisWeek: weekCount,
    byAgent: agentCounts,
    byType: typeCounts
  };
}

// Load activities on startup
loadActivities();

// Periodic cleanup (every hour)
setInterval(cleanupOldActivities, 60 * 60 * 1000);

const mimeTypes = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpg',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.woff': 'application/font-woff',
  '.ttf': 'application/font-ttf'
};

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;
  
  console.log(`${new Date().toISOString()} - ${req.method} ${pathname}`);
  
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  // Health check
  if (pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', time: new Date().toISOString(), count: activities.length }));
    return;
  }
  
  // API: Get activities with pagination
  if (pathname === '/api/activities' && req.method === 'GET') {
    const params = {
      limit: parseInt(url.searchParams.get('limit')) || 100,
      offset: parseInt(url.searchParams.get('offset')) || 0,
      agent: url.searchParams.get('agent'),
      type: url.searchParams.get('type'),
      sort: url.searchParams.get('sort') || '-timestamp'
    };
    
    const result = getActivities(params);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(result));
    return;
  }
  
  // API: Add activity (with deduplication)
  if (pathname === '/api/activities' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const entry = JSON.parse(body);
        entry.timestamp = entry.timestamp || new Date().toISOString();
        entry.id = entry.id || `act-${Date.now()}`;
        
        const added = addActivity(entry);
        res.writeHead(added ? 201 : 409, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: added, id: entry.id }));
      } catch (err) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid JSON' }));
      }
    });
    return;
  }
  
  // API: Get stats
  if (pathname === '/api/stats' && req.method === 'GET') {
    const stats = getStats();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(stats));
    return;
  }
  
  // API: Cleanup old activities
  if (pathname === '/api/cleanup' && req.method === 'POST') {
    const removed = cleanupOldActivities();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ removed, remaining: activities.length }));
    return;
  }
  
  // Static files
  let filePath = path.join(__dirname, pathname);
  if (pathname === '/') {
    filePath = path.join(__dirname, 'index.html');
  }
  
  const extname = String(path.extname(filePath)).toLowerCase();
  const contentType = mimeTypes[extname] || 'application/octet-stream';
  
  fs.readFile(filePath, (error, content) => {
    if (error) {
      if (error.code === 'ENOENT') {
        res.writeHead(404, { 'Content-Type': 'text/html' });
        res.end('<h1>404 Not Found</h1>');
      } else {
        res.writeHead(500);
        res.end('Server error');
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running at http://0.0.0.0:${PORT}/`);
  console.log(`Loaded ${activities.length} activities`);
});
