/**
 * Nox Work Tracker - Main Application
 * Tracks all agent activity, audits, ralph chains, and agent profiles
 */

// ============================================
// GLOBAL STATE
// ============================================
const AppState = {
  data: {
    activityLog: { entries: [] },
    audits: { audits: [], agentStats: {} },
    ralphChains: { chains: [] },
    agents: { agents: [] },
    meta: { lastUpdated: null, syncStatus: 'unknown' }
  },
  settings: {
    theme: 'dark',
    timeFormat: '24h',
    autoRefresh: true,
    refreshInterval: 30
  },
  filters: {
    activity: { agent: '', type: '', status: '', search: '' },
    audits: { agent: '', gradeMin: '', gradeMax: '', category: '' },
    ralph: { status: '' }
  },
  currentTab: 'activity',
  charts: {},
  autoRefreshTimer: null
};

// ============================================
// CONSTANTS
// ============================================
const AGENT_COLORS = {
  nox: '#3B82F6',
  sage: '#10B981',
  joy: '#8B5CF6'
};

const AGENT_LABELS = {
  nox: 'Nox',
  sage: 'Sage',
  joy: 'Joy'
};

const TYPE_ICONS = {
  heartbeat: '💓',
  subagent_spawn: '🚀',
  subagent_complete: '✅',
  proactive_work: '🔨',
  ralph_chain: '🔄',
  user_request: '👤',
  error: '❌',
  system: '⚙️'
};

const TYPE_LABELS = {
  heartbeat: 'Heartbeat',
  subagent_spawn: 'Subagent Spawn',
  subagent_complete: 'Subagent Complete',
  proactive_work: 'Proactive Work',
  ralph_chain: 'Ralph Chain',
  user_request: 'User Request',
  error: 'Error',
  system: 'System'
};

const DATA_URLS = {
  activity: 'data/activity-log.json',
  audits: 'data/audits.json',
  ralphChains: 'data/ralph-chains.json',
  agents: 'data/agents.json',
  meta: 'data/meta.json',
  calendar: 'data/calendar.json',
  searchIndex: 'data/search-index.json'
};

// ============================================
// CACHE CONTROL & VERSIONING
// ============================================
const CACHE_VERSION = 'v4-nuclear';
const CACHE_KEY = 'workTracker_cacheVersion';
const LAST_REFRESH_KEY = 'workTracker_lastRefresh';

// Clear all browser caches and reload
async function clearAllCaches() {
  console.log('[Cache] Clearing all caches...');
  
  // Clear localStorage cache tracking
  localStorage.removeItem(CACHE_KEY);
  localStorage.removeItem(LAST_REFRESH_KEY);
  
  // Clear service worker caches
  await clearServiceWorkerCaches();
  
  // Clear session cache if available
  if (window.caches) {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map(cacheName => caches.delete(cacheName)));
    console.log(`[Cache] Deleted ${cacheNames.length} caches`);
  }
  
  // Unregister service workers
  if ('serviceWorker' in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map(reg => reg.unregister()));
    console.log(`[Cache] Unregistered ${registrations.length} service workers`);
  }
  
  // Force reload with cache-busting
  window.location.reload(true);
}

// Check if cache version has changed (indicates new deployment)
function checkCacheVersion() {
  const storedVersion = localStorage.getItem(CACHE_KEY);
  
  if (storedVersion !== CACHE_VERSION) {
    console.log(`[Cache] Version mismatch: stored=${storedVersion}, current=${CACHE_VERSION}`);
    localStorage.setItem(CACHE_KEY, CACHE_VERSION);
    return true; // Version changed
  }
  return false;
}

// Detect stale data by comparing last activity timestamp
function detectStaleData(currentActivities) {
  const now = new Date();
  const lastActivity = currentActivities.length > 0 
    ? new Date(currentActivities[0].timestamp) 
    : null;
  
  if (lastActivity) {
    const hoursSinceActivity = (now - lastActivity) / (1000 * 60 * 60);
    
    // If no activity in last 12 hours, might be stale (during active work periods)
    // This is a heuristic - adjust based on expected activity patterns
    if (hoursSinceActivity > 12) {
      console.warn(`[Cache] Possible stale data: Last activity ${hoursSinceActivity.toFixed(1)} hours ago`);
      return true;
    }
  }
  
  return false;
}

// Show stale data warning banner
function showStaleDataWarning() {
  const warning = document.createElement('div');
  warning.id = 'stale-data-warning';
  warning.className = 'fixed top-0 left-0 right-0 bg-yellow-600 text-white text-center py-2 px-4 z-50';
  warning.innerHTML = `
    <span>⚠️ Data may be stale. </span>
    <button onclick="clearAllCaches()" class="underline font-bold">Clear Cache & Refresh</button>
    <button onclick="this.parentElement.remove()" class="ml-4 text-sm">✕</button>
  `;
  document.body.prepend(warning);
}

// ============================================
// DATA LOADING
// ============================================
async function loadAllData() {
  console.log('[WorkTracker] Loading all data...');
  
  // Cache-busting timestamp to force fresh data load
  const cacheBust = `?_=${Date.now()}`;
  
  try {
    const [activityRes, auditsRes, ralphRes, agentsRes, metaRes] = await Promise.all([
      fetchWithRetry(DATA_URLS.activity + cacheBust).catch(() => ({ json: () => ({ entries: [] }) })),
      fetchWithRetry(DATA_URLS.audits + cacheBust).catch(() => ({ json: () => ({ audits: [], agentStats: {} }) })),
      fetchWithRetry(DATA_URLS.ralphChains + cacheBust).catch(() => ({ json: () => ({ chains: [] }) })),
      fetchWithRetry(DATA_URLS.agents + cacheBust).catch(() => ({ json: () => ({ agents: [] }) })),
      fetchWithRetry(DATA_URLS.meta + cacheBust).catch(() => ({ json: () => ({ lastUpdated: null, syncStatus: 'offline' }) }))
    ]);

    AppState.data.activityLog = await activityRes.json();
    AppState.data.audits = await auditsRes.json();
    AppState.data.ralphChains = await ralphRes.json();
    AppState.data.agents = await agentsRes.json();
    AppState.data.meta = await metaRes.json();

    // Ensure arrays exist
    AppState.data.activityLog.entries = AppState.data.activityLog.entries || [];
    AppState.data.audits.audits = AppState.data.audits.audits || [];
    AppState.data.ralphChains.chains = AppState.data.ralphChains.chains || [];
    AppState.data.agents.agents = AppState.data.agents.agents || [];

    console.log('[WorkTracker] Data loaded:', {
      activities: AppState.data.activityLog.entries.length,
      audits: AppState.data.audits.audits.length,
      chains: AppState.data.ralphChains.chains.length,
      agents: AppState.data.agents.agents.length
    });

    updateLastRefreshTime();
    updateFreshnessIndicator();
    renderCurrentTab();
    startFreshnessMonitoring();
    
    // Check for stale data after rendering
    if (detectStaleData(AppState.data.activityLog.entries)) {
      showStaleDataWarning();
    }
    
    // Load calendar and search data
    loadCalendarData();
    loadSearchIndex();
  } catch (error) {
    console.error('[WorkTracker] Error loading data:', error);
    showError('Failed to load data. Please check the data files exist.');
  }
}

function refreshData() {
  console.log('[WorkTracker] Refreshing data...');
  loadAllData();
}

// ============================================
// TAB NAVIGATION
// ============================================
function showTab(tabName) {
  AppState.currentTab = tabName;
  
  // Update tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('tab-active');
  });
  document.getElementById(`tab-btn-${tabName}`)?.classList.add('tab-active');
  
  // Update tab content
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.add('hidden');
  });
  document.getElementById(`tab-${tabName}`)?.classList.remove('hidden');
  
  // Render the tab
  renderCurrentTab();
}

function renderCurrentTab() {
  switch (AppState.currentTab) {
    case 'activity':
      renderActivityTab();
      break;
    case 'sage':
      renderAgentTab('sage', 'Health');
      break;
    case 'joy':
      renderAgentTab('joy', 'Fun');
      break;
    case 'audits':
      renderAuditsTab();
      break;
    case 'ralph':
      renderRalphTab();
      break;
    case 'agents':
      renderAgentsTab();
      break;
    case 'settings':
      renderSettingsTab();
      break;
  }
}

// ============================================
// ACTIVITY TAB
// ============================================
function renderActivityTab() {
  const container = document.getElementById('activity-feed');
  if (!container) return;

  let entries = [...AppState.data.activityLog.entries];
  
  // Apply filters
  const agentFilter = document.getElementById('activity-agent-filter')?.value || '';
  const typeFilter = document.getElementById('activity-type-filter')?.value || '';
  
  if (agentFilter) {
    entries = entries.filter(e => e.agent === agentFilter);
  }
  if (typeFilter) {
    entries = entries.filter(e => e.type === typeFilter);
  }
  
  // Sort by timestamp (newest first)
  entries.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  
  if (entries.length === 0) {
    container.innerHTML = `
      <div class="card rounded p-8 text-center text-gray-500">
        <div class="text-4xl mb-2">📭</div>
        <p>No activity entries found.</p>
        <p class="text-sm mt-1">Activities will appear here when agents log their work.</p>
      </div>
    `;
    return;
  }
  
  let currentDate = null;
  let html = '';
  
  entries.forEach((entry, index) => {
    const entryDate = new Date(entry.timestamp).toDateString();
    const dateLabel = getDateLabel(entry.timestamp);
    
    // Add date separator if new date
    if (entryDate !== currentDate) {
      currentDate = entryDate;
      html += `
        <div class="flex items-center gap-4 my-4">
          <div class="flex-1 h-px bg-dark-700"></div>
          <span class="text-xs text-gray-500 font-medium">${dateLabel}</span>
          <div class="flex-1 h-px bg-dark-700"></div>
        </div>
      `;
    }
    
    const agentColor = AGENT_COLORS[entry.agent] || '#6B7280';
    const icon = TYPE_ICONS[entry.type] || '📄';
    const time = formatTime(entry.timestamp);
    const statusColor = getStatusColor(entry.status);
    const duration = entry.duration_ms ? formatDuration(entry.duration_ms) : '';
    
    html += `
      <div class="card rounded p-3 hover:bg-dark-800 transition-colors cursor-pointer" 
           onclick="toggleActivityDetails('${entry.id}')">
        <div class="flex items-start gap-3">
          <span class="text-lg select-none" title="${TYPE_LABELS[entry.type] || entry.type}">${icon}</span>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs text-gray-500 font-mono">${time}</span>
              <span class="px-2 py-0.5 rounded text-xs font-medium text-white" 
                    style="background-color: ${agentColor}">${AGENT_LABELS[entry.agent] || entry.agent}</span>
              ${entry.status ? `<span class="text-xs ${statusColor}">● ${entry.status}</span>` : ''}
              ${duration ? `<span class="text-xs text-gray-500">⏱️ ${duration}</span>` : ''}
            </div>
            <p class="text-sm mt-1 text-gray-200">${escapeHtml(entry.action)}</p>
          </div>
        </div>
        <div id="activity-details-${entry.id}" class="hidden mt-3 pt-3 border-t border-dark-700">
          <div class="text-xs text-gray-400 space-y-1 font-mono">
            <p><span class="text-gray-500">ID:</span> ${entry.id}</p>
            <p><span class="text-gray-500">Type:</span> ${entry.type}</p>
            <p><span class="text-gray-500">Timestamp:</span> ${entry.timestamp}</p>
            ${entry.details ? `<p><span class="text-gray-500">Details:</span> ${escapeHtml(entry.details)}</p>` : ''}
            ${entry.relatedIds?.length ? `<p><span class="text-gray-500">Related:</span> ${entry.relatedIds.join(', ')}</p>` : ''}
          </div>
        </div>
      </div>
    `;
  });
  
  html += `
    <div class="text-center text-xs text-gray-500 py-4">
      Showing ${entries.length} of ${AppState.data.activityLog.entries.length} entries
    </div>
  `;
  
  container.innerHTML = html;
}

function toggleActivityDetails(entryId) {
  const details = document.getElementById(`activity-details-${entryId}`);
  if (details) {
    details.classList.toggle('hidden');
  }
}

// ============================================
// AGENT-SPECIFIC TABS (Sage/Joy)
// ============================================
function renderAgentTab(agentKey, agentName) {
  const container = document.getElementById(`${agentKey}-feed`);
  const countEl = document.getElementById(`${agentKey}-activity-count`);
  if (!container) return;

  // Map agentKey to agent id used in data
  const agentId = agentKey === 'sage' ? 'health' : 'fun';

  let entries = AppState.data.activityLog.entries?.filter(e => e.agent === agentId) || [];

  // Sort by timestamp (newest first)
  entries.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  // Update count
  if (countEl) {
    const today = new Date().toDateString();
    const todayCount = entries.filter(e => new Date(e.timestamp).toDateString() === today).length;
    countEl.textContent = todayCount;
  }

  if (entries.length === 0) {
    container.innerHTML = `
      <div class="card rounded p-8 text-center text-gray-500">
        <div class="text-4xl mb-2">🌿</div>
        <p>No ${agentName} agent activity yet.</p>
        <p class="text-sm mt-1">Activities will appear when ${agentName} agent completes tasks.</p>
      </div>
    `;
    return;
  }

  let currentDate = null;
  let html = '';

  entries.slice(0, 50).forEach((entry) => {
    const entryDate = new Date(entry.timestamp).toDateString();
    const dateLabel = getDateLabel(entry.timestamp);

    // Add date separator if new date
    if (entryDate !== currentDate) {
      currentDate = entryDate;
      html += `
        <div class="flex items-center gap-4 my-4">
          <div class="flex-1 h-px bg-dark-700"></div>
          <span class="text-xs text-gray-500 font-medium">${dateLabel}</span>
          <div class="flex-1 h-px bg-dark-700"></div>
        </div>
      `;
    }

    const agentColor = AGENT_COLORS[entry.agent] || '#6B7280';
    const icon = TYPE_ICONS[entry.type] || '📄';
    const time = formatTime(entry.timestamp);
    const statusColor = getStatusColor(entry.status);
    const duration = entry.duration_ms ? formatDuration(entry.duration_ms) : '';

    html += `
      <div class="card rounded p-3 hover:bg-dark-800 transition-colors">
        <div class="flex items-start gap-3">
          <span class="text-lg select-none" title="${TYPE_LABELS[entry.type] || entry.type}">${icon}</span>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs text-gray-500 font-mono">${time}</span>
              <span class="px-2 py-0.5 rounded text-xs font-medium text-white" 
                    style="background-color: ${agentColor}">${AGENT_LABELS[entry.agent] || entry.agent}</span>
              ${entry.status ? `<span class="text-xs ${statusColor}">● ${entry.status}</span>` : ''}
              ${duration ? `<span class="text-xs text-gray-500">⏱️ ${duration}</span>` : ''}
            </div>
            <p class="text-sm mt-1 text-gray-200">${escapeHtml(entry.action)}</p>
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

// ============================================
// AUDITS TAB
// ============================================
function renderAuditsTab() {
  renderAuditSummary();
  renderAuditDistributionChart();
  renderAuditList();
}

function renderAuditSummary() {
  const container = document.getElementById('audit-summary');
  if (!container) return;

  const audits = AppState.data.audits.audits || [];
  const agents = AppState.data.agents.agents || [];
  
  if (audits.length === 0) {
    container.innerHTML = `
      <div class="col-span-3 card rounded-lg p-6 text-center text-gray-500">
        <div class="text-4xl mb-2">📋</div>
        <p>No audits recorded yet.</p>
      </div>
    `;
    return;
  }
  
  let html = '';
  
  agents.forEach(agent => {
    const agentAudits = audits.filter(a => a.agent === agent.id);
    if (agentAudits.length === 0) return;
    
    const avgGrade = Math.round(agentAudits.reduce((sum, a) => sum + (a.grade || 0), 0) / agentAudits.length);
    const grades = agentAudits.map(a => a.grade).sort((a, b) => a - b);
    const minGrade = grades[0];
    const maxGrade = grades[grades.length - 1];
    
    // Calculate trend (compare last 5 vs previous 5)
    const recent = agentAudits.slice(-5).map(a => a.grade);
    const previous = agentAudits.slice(-10, -5).map(a => a.grade);
    const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
    const previousAvg = previous.length > 0 ? previous.reduce((a, b) => a + b, 0) / previous.length : recentAvg;
    const trend = recentAvg > previousAvg + 2 ? '↑' : recentAvg < previousAvg - 2 ? '↓' : '→';
    const trendColor = trend === '↑' ? 'text-green-400' : trend === '↓' ? 'text-red-400' : 'text-gray-400';
    
    const gradeClass = avgGrade >= 80 ? 'grade-high' : avgGrade >= 60 ? 'grade-med' : 'grade-low';
    
    html += `
      <div class="card rounded-lg p-4">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-3 h-3 rounded-full" style="background-color: ${agent.color || AGENT_COLORS[agent.id]}"></div>
          <span class="font-medium">${agent.name}</span>
        </div>
        <div class="flex items-baseline gap-2">
          <span class="text-3xl font-bold ${gradeClass}">${avgGrade}</span>
          <span class="text-sm text-gray-500">avg</span>
          <span class="text-lg ${trendColor} ml-2" title="${trend === '↑' ? 'Improving' : trend === '↓' ? 'Declining' : 'Stable'}">${trend}</span>
        </div>
        <div class="text-sm text-gray-400 mt-1">${agentAudits.length} audits · ${minGrade}—${maxGrade}</div>
      </div>
    `;
  });
  
  container.innerHTML = html || '<div class="col-span-3 text-center text-gray-500">No audit data available</div>';
}

function renderAuditDistributionChart() {
  const ctx = document.getElementById('audit-distribution-chart');
  if (!ctx) return;

  const audits = AppState.data.audits.audits || [];
  
  // Create grade distribution (0-9, 10-19, ..., 90-100)
  const distribution = new Array(10).fill(0);
  audits.forEach(audit => {
    const grade = audit.grade || 0;
    const bucket = Math.min(Math.floor(grade / 10), 9);
    distribution[bucket]++;
  });
  
  // Destroy existing chart
  if (AppState.charts.auditDistribution) {
    AppState.charts.auditDistribution.destroy();
  }
  
  AppState.charts.auditDistribution = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['0-9', '10-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80-89', '90-100'],
      datasets: [{
        label: 'Number of Audits',
        data: distribution,
        backgroundColor: distribution.map((_, i) => {
          if (i >= 8) return '#10B981'; // Green for 80-100
          if (i >= 6) return '#F59E0B'; // Yellow for 60-79
          return '#EF4444'; // Red for <60
        }),
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { color: '#6B7280' },
          grid: { color: '#1e1e30' }
        },
        x: {
          ticks: { color: '#6B7280' },
          grid: { display: false }
        }
      }
    }
  });
}

function renderAuditList() {
  const container = document.getElementById('audit-list');
  if (!container) return;

  let audits = [...AppState.data.audits.audits];
  
  // Sort by date (newest first)
  audits.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  
  if (audits.length === 0) {
    container.innerHTML = `
      <div class="card rounded-lg p-8 text-center text-gray-500">
        <div class="text-4xl mb-2">📋</div>
        <p>No audits available.</p>
      </div>
    `;
    return;
  }
  
  let html = '';
  
  audits.forEach(audit => {
    const agentColor = AGENT_COLORS[audit.agent] || '#6B7280';
    const gradeClass = audit.grade >= 80 ? 'grade-high' : audit.grade >= 60 ? 'grade-med' : 'grade-low';
    const date = formatDate(audit.timestamp);
    const time = formatTime(audit.timestamp);
    
    html += `
      <div class="card rounded-lg p-4 hover:bg-dark-800 transition-colors cursor-pointer"
           onclick="toggleAuditDetails('${audit.id}')">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div class="flex items-center gap-3">
            <span class="px-2 py-1 rounded text-xs font-medium text-white" 
                  style="background-color: ${agentColor}">${AGENT_LABELS[audit.agent] || audit.agent}</span>
            <span class="text-sm font-medium">${escapeHtml(audit.project)}</span>
            ${audit.category ? `<span class="px-2 py-0.5 rounded text-xs bg-dark-700 text-gray-300">${audit.category}</span>` : ''}
          </div>
          <div class="flex items-center gap-3">
            <span class="text-2xl font-bold ${gradeClass}">${audit.grade}</span>
            <span class="text-xs text-gray-500">${date} ${time}</span>
          </div>
        </div>
        ${audit.summary ? `<p class="text-sm text-gray-400 mt-2">${escapeHtml(audit.summary)}</p>` : ''}
        
        <div id="audit-details-${audit.id}" class="hidden mt-4 pt-4 border-t border-dark-700">
          <div class="space-y-3 text-sm">
            ${audit.fullReport ? `
              <div>
                <h4 class="text-gray-500 mb-1">Full Report</h4>
                <div class="bg-dark-900 rounded p-3 text-gray-300 whitespace-pre-wrap">${escapeHtml(audit.fullReport)}</div>
              </div>
            ` : ''}
            ${audit.feedback ? `
              <div>
                <h4 class="text-gray-500 mb-1">Feedback</h4>
                ${audit.feedback.strengths?.length ? `
                  <div class="mb-2">
                    <span class="text-green-400 text-xs">Strengths:</span>
                    <ul class="list-disc list-inside text-gray-300 mt-1">
                      ${audit.feedback.strengths.map(s => `<li>${escapeHtml(s)}</li>`).join('')}
                    </ul>
                  </div>
                ` : ''}
                ${audit.feedback.weaknesses?.length ? `
                  <div class="mb-2">
                    <span class="text-red-400 text-xs">Weaknesses:</span>
                    <ul class="list-disc list-inside text-gray-300 mt-1">
                      ${audit.feedback.weaknesses.map(w => `<li>${escapeHtml(w)}</li>`).join('')}
                    </ul>
                  </div>
                ` : ''}
                ${audit.feedback.actionItems?.length ? `
                  <div>
                    <span class="text-blue-400 text-xs">Action Items:</span>
                    <ul class="list-disc list-inside text-gray-300 mt-1">
                      ${audit.feedback.actionItems.map(a => `<li>${escapeHtml(a)}</li>`).join('')}
                    </ul>
                  </div>
                ` : ''}
              </div>
            ` : ''}
            ${audit.evidenceOfResearch?.length ? `
              <div>
                <h4 class="text-gray-500 mb-1">Evidence of Research</h4>
                <ul class="list-disc list-inside text-gray-300">
                  ${audit.evidenceOfResearch.map(e => `<li>${escapeHtml(e)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
}

function toggleAuditDetails(auditId) {
  const details = document.getElementById(`audit-details-${auditId}`);
  if (details) {
    details.classList.toggle('hidden');
  }
}

// ============================================
// RALPH CHAINS TAB
// ============================================
function renderRalphTab() {
  renderActiveChainBanner();
  renderRalphChainHistory();
}

function renderActiveChainBanner() {
  const banner = document.getElementById('ralph-active-banner');
  const chains = AppState.data.ralphChains.chains || [];
  const activeChain = chains.find(c => c.status === 'in_progress');
  
  if (!activeChain || !banner) {
    if (banner) banner.classList.add('hidden');
    return;
  }
  
  banner.classList.remove('hidden');
  
  const currentBatch = activeChain.batchPlan?.find(b => b.status === 'in_progress') || 
                       activeChain.batchPlan?.[activeChain.completedBatches] ||
                       activeChain.batchPlan?.[activeChain.batchPlan?.length - 1];
  
  document.getElementById('ralph-active-name').textContent = activeChain.name;
  document.getElementById('ralph-active-batch').textContent = currentBatch ? `${currentBatch.batch}: ${currentBatch.name}` : '-';
  document.getElementById('ralph-active-phase').textContent = 'Building...'; // Could be more specific
  document.getElementById('ralph-active-progress').textContent = `${activeChain.completedBatches}/${activeChain.totalBatches}`;
  
  const progressPercent = (activeChain.completedBatches / activeChain.totalBatches) * 100;
  document.getElementById('ralph-progress-bar').style.width = `${progressPercent}%`;
}

function renderRalphChainHistory() {
  const container = document.getElementById('ralph-history');
  if (!container) return;

  let chains = [...AppState.data.ralphChains.chains];
  
  // Sort by started date (newest first)
  chains.sort((a, b) => new Date(b.startedAt) - new Date(a.startedAt));
  
  if (chains.length === 0) {
    container.innerHTML = `
      <div class="card rounded-lg p-8 text-center text-gray-500">
        <div class="text-4xl mb-2">🔄</div>
        <p>No ralph chains recorded yet.</p>
        <p class="text-sm mt-1">Ralph chains orchestrate multi-batch build processes.</p>
      </div>
    `;
    return;
  }
  
  let html = '';
  
  chains.forEach(chain => {
    const statusColors = {
      completed: 'text-green-400',
      in_progress: 'text-blue-400',
      stopped: 'text-red-400'
    };
    
    const duration = chain.completedAt ? 
      formatDuration(new Date(chain.completedAt) - new Date(chain.startedAt)) : 
      'In progress';
    
    const avgGrade = chain.averageAuditGrade ? 
      `<span class="${chain.averageAuditGrade >= 80 ? 'grade-high' : chain.averageAuditGrade >= 60 ? 'grade-med' : 'grade-low'}">${chain.averageAuditGrade} avg</span>` : 
      '<span class="text-gray-500">No audits</span>';
    
    html += `
      <div class="card rounded-lg p-4 hover:bg-dark-800 transition-colors">
        <div class="flex items-center justify-between flex-wrap gap-2 cursor-pointer" onclick="toggleChainDetails('${chain.id}')">
          <div>
            <div class="flex items-center gap-2">
              <h3 class="font-semibold">${escapeHtml(chain.name)}</h3>
              <span class="text-xs ${statusColors[chain.status] || 'text-gray-400'}">● ${chain.status}</span>
            </div>
            <div class="text-sm text-gray-400 mt-1">
              ${formatDate(chain.startedAt)} · ${chain.totalBatches} batches · ${chain.totalDefectsFound || 0} defects · ${avgGrade}
            </div>
          </div>
          <div class="text-right">
            <div class="text-sm font-medium">${duration}</div>
            <div class="text-xs text-gray-500">${chain.completedBatches}/${chain.totalBatches} complete</div>
          </div>
        </div>
        
        <div class="mt-3 h-2 bg-dark-700 rounded">
          <div class="h-full bg-blue-500 rounded transition-all" style="width: ${(chain.completedBatches / chain.totalBatches) * 100}%"></div>
        </div>
        
        <div id="chain-details-${chain.id}" class="hidden mt-4 pt-4 border-t border-dark-700">
          ${chain.batchPlan?.length ? `
            <h4 class="text-sm font-medium text-gray-400 mb-3">Batch Breakdown</h4>
            <div class="space-y-2">
              ${chain.batchPlan.map(batch => `
                <div class="bg-dark-900 rounded p-3 text-sm">
                  <div class="flex items-center justify-between">
                    <span class="font-medium">${batch.batch}. ${escapeHtml(batch.name)}</span>
                    <span class="text-xs ${batch.status === 'completed' ? 'text-green-400' : batch.status === 'in_progress' ? 'text-blue-400' : 'text-gray-500'}">${batch.status}</span>
                  </div>
                  <p class="text-gray-400 text-xs mt-1">${escapeHtml(batch.scope)}</p>
                  <div class="flex gap-4 mt-2 text-xs text-gray-500">
                    ${batch.defectsFound !== undefined ? `<span>Defects: ${batch.defectsFound}/${batch.defectsFixed || 0}</span>` : ''}
                    ${batch.builderIterations ? `<span>Builder iterations: ${batch.builderIterations}</span>` : ''}
                    ${batch.redTeamIterations ? `<span>Red team: ${batch.redTeamIterations}</span>` : ''}
                    ${batch.auditGrade ? `<span class="${batch.auditGrade >= 80 ? 'text-green-400' : batch.auditGrade >= 60 ? 'text-yellow-400' : 'text-red-400'}">Grade: ${batch.auditGrade}</span>` : ''}
                  </div>
                </div>
              `).join('')}
            </div>
          ` : ''}
          ${chain.requirements ? `
            <div class="mt-4">
              <h4 class="text-sm font-medium text-gray-400 mb-2">Requirements</h4>
              <div class="bg-dark-900 rounded p-3 text-xs text-gray-300 whitespace-pre-wrap">${escapeHtml(chain.requirements)}</div>
            </div>
          ` : ''}
          <div class="mt-4 grid grid-cols-3 gap-4 text-center">
            <div class="bg-dark-900 rounded p-2">
              <div class="text-lg font-bold text-blue-400">${chain.totalBuilderIterations || 0}</div>
              <div class="text-xs text-gray-500">Builder Iterations</div>
            </div>
            <div class="bg-dark-900 rounded p-2">
              <div class="text-lg font-bold text-purple-400">${chain.totalRedTeamIterations || 0}</div>
              <div class="text-xs text-gray-500">Red Team Iterations</div>
            </div>
            <div class="bg-dark-900 rounded p-2">
              <div class="text-lg font-bold text-green-400">${chain.totalDefectsFound || 0}</div>
              <div class="text-xs text-gray-500">Defects Found</div>
            </div>
          </div>
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
}

function toggleChainDetails(chainId) {
  const details = document.getElementById(`chain-details-${chainId}`);
  if (details) {
    details.classList.toggle('hidden');
  }
}

// ============================================
// AGENTS TAB
// ============================================
let selectedAgentId = null;

function renderAgentsTab() {
  renderAgentCards();
  if (selectedAgentId) {
    renderAgentDetail(selectedAgentId);
  }
}

function renderAgentCards() {
  const container = document.getElementById('agent-cards');
  if (!container) return;

  const agents = AppState.data.agents.agents || [];
  
  if (agents.length === 0) {
    container.innerHTML = `
      <div class="col-span-3 card rounded-lg p-8 text-center text-gray-500">
        <div class="text-4xl mb-2">👥</div>
        <p>No agent profiles found.</p>
      </div>
    `;
    return;
  }
  
  let html = '';
  
  agents.forEach(agent => {
    const stats = agent.stats || {};
    const avgGrade = stats.averageAuditGrade || 0;
    const gradeClass = avgGrade >= 80 ? 'grade-high' : avgGrade >= 60 ? 'grade-med' : 'grade-low';
    const trend = stats.auditGradeTrend || 'stable';
    const trendIcon = trend === 'improving' ? '↑' : trend === 'declining' ? '↓' : '→';
    const trendColor = trend === 'improving' ? 'text-green-400' : trend === 'declining' ? 'text-red-400' : 'text-gray-400';
    
    html += `
      <div class="card rounded-lg p-4 cursor-pointer hover:bg-dark-800 transition-colors ${selectedAgentId === agent.id ? 'ring-2 ring-blue-500' : ''}"
           onclick="selectAgent('${agent.id}')">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-12 h-12 rounded-full flex items-center justify-center text-white text-xl font-bold"
               style="background-color: ${agent.color || AGENT_COLORS[agent.id]}">
            ${agent.name.charAt(0)}
          </div>
          <div>
            <h3 class="font-semibold">${agent.name}</h3>
            <p class="text-xs text-gray-400">${agent.role}</p>
          </div>
        </div>
        <div class="flex items-baseline gap-2 mb-2">
          <span class="text-3xl font-bold ${gradeClass}">${avgGrade || '-'}</span>
          <span class="text-xs text-gray-500">avg grade</span>
          <span class="text-lg ${trendColor}">${trendIcon}</span>
        </div>
        <div class="text-xs text-gray-500">
          ${stats.lastActive ? `Last active: ${timeAgo(stats.lastActive)}` : 'Never active'}
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
}

function selectAgent(agentId) {
  selectedAgentId = agentId;
  renderAgentCards(); // Re-render to update selection highlight
  renderAgentDetail(agentId);
}

function renderAgentDetail(agentId) {
  const container = document.getElementById('agent-detail');
  const content = document.getElementById('agent-detail-content');
  if (!container || !content) return;

  const agent = AppState.data.agents.agents.find(a => a.id === agentId);
  if (!agent) return;
  
  container.classList.remove('hidden');
  
  const stats = agent.stats || {};
  const audits = AppState.data.audits.audits.filter(a => a.agent === agentId);
  
  // Calculate grade history for chart
  const gradeHistory = audits
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    .map((a, i) => ({ x: i + 1, y: a.grade }));
  
  content.innerHTML = `
    <div class="flex items-start justify-between flex-wrap gap-4 mb-6">
      <div class="flex items-center gap-4">
        <div class="w-16 h-16 rounded-full flex items-center justify-center text-white text-2xl font-bold"
             style="background-color: ${agent.color || AGENT_COLORS[agent.id]}">
          ${agent.name.charAt(0)}
        </div>
        <div>
          <h2 class="text-2xl font-bold">${agent.name}</h2>
          <p class="text-gray-400">${agent.role}</p>
        </div>
      </div>
      <button onclick="closeAgentDetail()" class="text-gray-500 hover:text-gray-300">
        ✕ Close
      </button>
    </div>
    
    <p class="text-gray-300 mb-4">${agent.description}</p>
    
    <div class="flex flex-wrap gap-2 mb-6">
      ${(agent.focusAreas || []).map(area => `
        <span class="px-3 py-1 rounded-full text-sm bg-dark-700 text-gray-300">${area}</span>
      `).join('')}
    </div>
    
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-dark-900 rounded p-3 text-center">
        <div class="text-2xl font-bold text-blue-400">${stats.totalHeartbeats || 0}</div>
        <div class="text-xs text-gray-500">Heartbeats</div>
      </div>
      <div class="bg-dark-900 rounded p-3 text-center">
        <div class="text-2xl font-bold text-purple-400">${stats.totalSubagentsSpawned || 0}</div>
        <div class="text-xs text-gray-500">Subagents</div>
      </div>
      <div class="bg-dark-900 rounded p-3 text-center">
        <div class="text-2xl font-bold text-green-400">${stats.totalProactiveWorkItems || 0}</div>
        <div class="text-xs text-gray-500">Work Items</div>
      </div>
      <div class="bg-dark-900 rounded p-3 text-center">
        <div class="text-2xl font-bold text-yellow-400">${stats.totalRalphChains || 0}</div>
        <div class="text-xs text-gray-500">Ralph Chains</div>
      </div>
    </div>
    
    <div class="mb-6">
      <h3 class="font-semibold mb-3">Grade History</h3>
      <canvas id="agent-grade-chart" height="100"></canvas>
    </div>
    
    ${stats.topFeedback?.length ? `
      <div class="mb-6">
        <h3 class="font-semibold mb-3">Top Feedback Themes</h3>
        <div class="space-y-2">
          ${stats.topFeedback.map(fb => `
            <div class="flex items-center gap-3">
              <div class="flex-1 bg-dark-700 rounded h-6 relative overflow-hidden">
                <div class="absolute inset-y-0 left-0 bg-blue-500/30" style="width: ${Math.min(fb.frequency * 10, 100)}%"></div>
                <span class="absolute inset-0 flex items-center px-3 text-sm">${escapeHtml(fb.feedback)}</span>
              </div>
              <span class="text-sm text-gray-500 w-8 text-right">${fb.frequency}</span>
            </div>
          `).join('')}
        </div>
      </div>
    ` : ''}
    
    ${agent.recentActivity?.length ? `
      <div>
        <h3 class="font-semibold mb-3">Recent Activity</h3>
        <div class="space-y-2 max-h-64 overflow-y-auto">
          ${agent.recentActivity.slice(0, 20).map(activity => `
            <div class="text-sm py-2 border-b border-dark-700 last:border-0">
              <span class="text-gray-500 text-xs">${formatDateTime(activity.timestamp)}</span>
              <p class="text-gray-300 mt-0.5">${escapeHtml(activity.action)}</p>
            </div>
          `).join('')}
        </div>
      </div>
    ` : ''}
  `;
  
  // Render grade chart
  setTimeout(() => {
    const ctx = document.getElementById('agent-grade-chart');
    if (ctx && gradeHistory.length > 0) {
      if (AppState.charts.agentGrade) {
        AppState.charts.agentGrade.destroy();
      }
      
      AppState.charts.agentGrade = new Chart(ctx, {
        type: 'line',
        data: {
          labels: gradeHistory.map((_, i) => `#${i + 1}`),
          datasets: [{
            label: 'Audit Grade',
            data: gradeHistory.map(g => g.y),
            borderColor: agent.color || AGENT_COLORS[agent.id],
            backgroundColor: (agent.color || AGENT_COLORS[agent.id]) + '20',
            fill: true,
            tension: 0.3
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: {
              min: 0,
              max: 100,
              ticks: { color: '#6B7280' },
              grid: { color: '#1e1e30' }
            },
            x: {
              ticks: { color: '#6B7280' },
              grid: { display: false }
            }
          }
        }
      });
    }
  }, 0);
}

function closeAgentDetail() {
  selectedAgentId = null;
  document.getElementById('agent-detail')?.classList.add('hidden');
  renderAgentCards();
}

// ============================================
// SETTINGS TAB
// ============================================
function renderSettingsTab() {
  // Settings are rendered server-side in HTML, just update values
  document.getElementById('theme-setting').value = AppState.settings.theme;
  document.getElementById('time-format-setting').value = AppState.settings.timeFormat;
  document.getElementById('auto-refresh-toggle').checked = AppState.settings.autoRefresh;
  document.getElementById('refresh-interval').value = AppState.settings.refreshInterval;
}

function initSettings() {
  // Theme toggle
  document.getElementById('theme-setting')?.addEventListener('change', (e) => {
    AppState.settings.theme = e.target.value;
    document.documentElement.classList.toggle('dark', AppState.settings.theme === 'dark');
  });
  
  // Time format toggle
  document.getElementById('time-format-setting')?.addEventListener('change', (e) => {
    AppState.settings.timeFormat = e.target.value;
    renderCurrentTab(); // Re-render to update timestamps
  });
  
  // Auto-refresh toggle
  document.getElementById('auto-refresh-toggle')?.addEventListener('change', (e) => {
    AppState.settings.autoRefresh = e.target.checked;
    setupAutoRefresh();
  });
  
  // Refresh interval
  document.getElementById('refresh-interval')?.addEventListener('change', (e) => {
    AppState.settings.refreshInterval = parseInt(e.target.value);
    setupAutoRefresh();
  });
}

function setupAutoRefresh() {
  if (AppState.autoRefreshTimer) {
    clearInterval(AppState.autoRefreshTimer);
    AppState.autoRefreshTimer = null;
  }
  
  if (AppState.settings.autoRefresh) {
    AppState.autoRefreshTimer = setInterval(() => {
      refreshData();
    }, AppState.settings.refreshInterval * 1000);
  }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================
function getDateLabel(timestamp) {
  const date = new Date(timestamp);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  
  if (date.toDateString() === today.toDateString()) {
    return 'Today';
  } else if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  } else {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }
}

function formatTime(timestamp) {
  const date = new Date(timestamp);
  if (AppState.settings.timeFormat === '12h') {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
  }
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function formatDate(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function formatDateTime(timestamp) {
  return `${formatDate(timestamp)} ${formatTime(timestamp)}`;
}

function timeAgo(timestamp) {
  const seconds = Math.floor((new Date() - new Date(timestamp)) / 1000);
  
  const intervals = {
    year: 31536000,
    month: 2592000,
    week: 604800,
    day: 86400,
    hour: 3600,
    minute: 60
  };
  
  for (const [unit, secondsInUnit] of Object.entries(intervals)) {
    const interval = Math.floor(seconds / secondsInUnit);
    if (interval >= 1) {
      return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
    }
  }
  
  return 'Just now';
}

function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${Math.floor(ms / 1000)}s`;
  if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`;
}

function getStatusColor(status) {
  const colors = {
    success: 'text-green-400',
    failed: 'text-red-400',
    in_progress: 'text-blue-400',
    pending: 'text-yellow-400'
  };
  return colors[status] || 'text-gray-400';
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function updateLastRefreshTime() {
  const el = document.getElementById('last-refresh-time');
  if (el) {
    el.textContent = new Date().toLocaleTimeString();
  }
}

function showError(message) {
  console.error('[WorkTracker]', message);
  // Could show a toast notification here
}

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
  console.log('[WorkTracker] Initializing...');
  
  // Initialize settings
  initSettings();
  
  // Setup filter listeners
  document.getElementById('activity-agent-filter')?.addEventListener('change', renderActivityTab);
  document.getElementById('activity-type-filter')?.addEventListener('change', renderActivityTab);
  
  // Load initial data
  loadAllData();
  
  // Setup search on Enter key
  document.getElementById('global-search')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      showTab('search');
      document.getElementById('search-input').value = e.target.value;
      performGlobalSearch();
    }
  });
  
  document.getElementById('search-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performGlobalSearch();
  });
  
  console.log('[WorkTracker] Initialization complete');
});

// ============================================
// CALENDAR FUNCTIONS
// ============================================
let calendarCurrentWeek = new Date();
let calendarData = { scheduledTasks: [], recurring: [] };

async function loadCalendarData() {
  try {
    const cacheBust = `?t=${Date.now()}`;
    const response = await fetch('data/calendar.json' + cacheBust);
    calendarData = await response.json();
    renderCalendar();
  } catch (err) {
    console.error('[Calendar] Failed to load:', err);
  }
}

function changeWeek(direction) {
  calendarCurrentWeek.setDate(calendarCurrentWeek.getDate() + (direction * 7));
  renderCalendar();
}

function renderCalendar() {
  const grid = document.getElementById('calendar-grid');
  const eventsContainer = document.getElementById('calendar-events');
  const weekLabel = document.getElementById('calendar-week-label');
  
  // Get week start (Sunday)
  const weekStart = new Date(calendarCurrentWeek);
  weekStart.setDate(weekStart.getDate() - weekStart.getDay());
  
  // Update label
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekEnd.getDate() + 6);
  weekLabel.textContent = `${weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} - ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
  
  // Render day headers
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  grid.innerHTML = days.map((day, i) => {
    const date = new Date(weekStart);
    date.setDate(date.getDate() + i);
    const isToday = new Date().toDateString() === date.toDateString();
    return `
      <div class="card rounded p-2 text-center ${isToday ? 'border-accent-blue' : ''}">
        <div class="text-xs text-gray-500">${day}</div>
        <div class="text-lg font-semibold ${isToday ? 'text-accent-blue' : ''}">${date.getDate()}</div>
      </div>
    `;
  }).join('');
  
  // Find tasks for this week
  const weekTasks = calendarData.scheduledTasks?.filter(task => {
    if (!task.nextRun) return false;
    const taskDate = new Date(task.nextRun);
    return taskDate >= weekStart && taskDate <= weekEnd;
  }) || [];
  
  // Render events
  if (weekTasks.length === 0) {
    eventsContainer.innerHTML = `
      <div class="card rounded p-4 text-center text-gray-500">
        No scheduled tasks for this week.
      </div>
    `;
  } else {
    eventsContainer.innerHTML = weekTasks.map(task => `
      <div class="card rounded p-3 flex justify-between items-center">
        <div>
          <div class="flex items-center gap-2">
            <span class="text-lg">${getTaskIcon(task.category)}</span>
            <span class="font-semibold">${task.title}</span>
            <span class="px-2 py-0.5 text-xs rounded ${getStatusClass(task.status)}">${task.status}</span>
          </div>
          <p class="text-sm text-gray-400 ml-6">${task.description}</p>
          <p class="text-xs text-gray-500 ml-6">${formatDateTime(task.nextRun)} • ${task.type}</p>
        </div>
      </div>
    `).join('');
  }
}

function getTaskIcon(category) {
  const icons = {
    'content-research': '🎬',
    'intelligence': '🧠',
    'maintenance': '🔧',
    'monitoring': '👁️'
  };
  return icons[category] || '📋';
}

function getStatusClass(status) {
  const classes = {
    'scheduled': 'bg-green-900/50 text-green-400',
    'pending': 'bg-yellow-900/50 text-yellow-400',
    'completed': 'bg-gray-700 text-gray-400'
  };
  return classes[status] || 'bg-dark-700';
}

function formatDateTime(isoString) {
  if (!isoString) return 'Not scheduled';
  return new Date(isoString).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
}

// ============================================
// SEARCH FUNCTIONS
// ============================================
let searchIndex = { documents: [] };
let currentSearchFilter = 'all';

async function loadSearchIndex() {
  try {
    const cacheBust = `?t=${Date.now()}`;
    const response = await fetch('data/search-index.json' + cacheBust);
    searchIndex = await response.json();
  } catch (err) {
    console.error('[Search] Failed to load index:', err);
  }
}

function setSearchFilter(filter) {
  currentSearchFilter = filter;
  // Update button styles
  ['all', 'memory', 'documents', 'tasks'].forEach(f => {
    const btn = document.getElementById(`filter-${f}`);
    if (btn) {
      btn.className = f === filter 
        ? 'px-2 py-1 text-xs bg-accent-blue rounded'
        : 'px-2 py-1 text-xs bg-dark-700 rounded hover:bg-dark-600';
    }
  });
  // Re-run search if there's a query
  const query = document.getElementById('search-input')?.value;
  if (query) performGlobalSearch();
}

function performGlobalSearch() {
  const query = (document.getElementById('global-search')?.value || 
                 document.getElementById('search-input')?.value || '').toLowerCase();
  
  if (!query) {
    showTab('search');
    return;
  }
  
  showTab('search');
  document.getElementById('search-input').value = query;
  
  const resultsContainer = document.getElementById('search-results');
  
  // Search across all documents
  const results = searchIndex.documents?.filter(doc => {
    // Apply type filter
    if (currentSearchFilter !== 'all' && doc.type !== currentSearchFilter) return false;
    
    // Search in title, content, tags
    const searchable = `${doc.title} ${doc.content} ${doc.tags?.join(' ') || ''}`.toLowerCase();
    return searchable.includes(query);
  }) || [];
  
  // Also search in activity log
  const activityResults = AppState.data.activityLog.entries?.filter(entry => {
    const searchable = `${entry.title} ${entry.description}`.toLowerCase();
    return searchable.includes(query);
  }) || [];
  
  if (results.length === 0 && activityResults.length === 0) {
    resultsContainer.innerHTML = `
      <div class="card rounded p-8 text-center text-gray-500">
        No results found for "${query}".
        <p class="text-sm mt-2">Try different keywords or clear filters.</p>
      </div>
    `;
    return;
  }
  
  let html = '';
  
  // Document results
  if (results.length > 0) {
    html += `<div class="mb-4"><h3 class="text-sm font-semibold text-gray-400 mb-2">Documents & Memory (${results.length})</h3>`;
    html += results.map(doc => `
      <div class="card rounded p-3 mb-2 hover:bg-dark-700/50 transition cursor-pointer">
        <div class="flex items-start gap-3">
          <span class="text-lg">${getDocTypeIcon(doc.type)}</span>
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <span class="font-semibold">${highlightMatch(doc.title, query)}</span>
              <span class="text-xs px-1.5 py-0.5 bg-dark-700 rounded">${doc.type}</span>
            </div>
            <p class="text-sm text-gray-400 mt-1">${highlightMatch(doc.content.substring(0, 150), query)}${doc.content.length > 150 ? '...' : ''}</p>
            <div class="flex gap-1 mt-2">
              ${doc.tags?.map(tag => `<span class="text-xs px-1.5 py-0.5 bg-dark-700/50 rounded text-gray-500">#${tag}</span>`).join('') || ''}
            </div>
            <p class="text-xs text-gray-500 mt-1">${doc.path || ''} • ${formatTimeAgo(doc.timestamp)}</p>
          </div>
        </div>
      </div>
    `).join('');
    html += '</div>';
  }
  
  // Activity results
  if (activityResults.length > 0) {
    html += `<div><h3 class="text-sm font-semibold text-gray-400 mb-2">Activity Log (${activityResults.length})</h3>`;
    html += activityResults.slice(0, 10).map(entry => `
      <div class="card rounded p-3 mb-2">
        <div class="flex items-start gap-3">
          <span class="text-lg">${entry.icon || '🔹'}</span>
          <div class="flex-1">
            <div class="flex items-center gap-2">
              <span class="font-semibold">${highlightMatch(entry.title, query)}</span>
              <span class="text-xs px-1.5 py-0.5 rounded" style="background: ${AGENT_COLORS[entry.agent] || '#666'}33; color: ${AGENT_COLORS[entry.agent] || '#999'}">${entry.agent}</span>
            </div>
            <p class="text-sm text-gray-400 mt-1">${highlightMatch(entry.description, query)}</p>
            <p class="text-xs text-gray-500 mt-1">${formatTimeAgo(entry.timestamp)}</p>
          </div>
        </div>
      </div>
    `).join('');
    html += '</div>';
  }
  
  resultsContainer.innerHTML = html;
}

function getDocTypeIcon(type) {
  const icons = {
    'memory': '🧠',
    'document': '📄',
    'task': '✅',
    'note': '📝'
  };
  return icons[type] || '📄';
}

function highlightMatch(text, query) {
  if (!text || !query) return text;
  const regex = new RegExp(`(${query})`, 'gi');
  return text.replace(regex, '<mark class="bg-yellow-500/30 text-yellow-200">$1</mark>');
}

// ============================================
// ENHANCED FETCH WITH RETRY & TIMEOUT
// ============================================

const FETCH_TIMEOUT = 10000; // 10 second timeout
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // Start with 1 second

// Fetch with timeout and retry logic
async function fetchWithRetry(url, options = {}, retries = MAX_RETRIES) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      cache: 'no-store' // Always bypass browser cache
    });
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (retries > 0) {
      const delay = RETRY_DELAY * (MAX_RETRIES - retries + 1);
      console.log(`[Fetch] Retrying ${url} in ${delay}ms (${retries} retries left)`);
      await new Promise(resolve => setTimeout(resolve, delay));
      return fetchWithRetry(url, options, retries - 1);
    }
    
    throw error;
  }
}

// ============================================
// DATA FRESHNESS MONITORING
// ============================================

let dataFreshnessInterval = null;

// Update visual freshness indicator
function updateFreshnessIndicator() {
  const indicator = document.getElementById('freshness-indicator');
  const lastUpdated = AppState.data.meta?.lastUpdated;
  
  if (!indicator || !lastUpdated) return;
  
  const lastUpdateTime = new Date(lastUpdated);
  const now = new Date();
  const minutesSinceUpdate = Math.floor((now - lastUpdateTime) / (1000 * 60));
  
  let freshnessClass = 'text-green-400';
  let freshnessText = 'Fresh';
  
  if (minutesSinceUpdate > 60) {
    freshnessClass = 'text-red-400';
    freshnessText = `${Math.floor(minutesSinceUpdate / 60)}h ago`;
  } else if (minutesSinceUpdate > 5) {
    freshnessClass = 'text-yellow-400';
    freshnessText = `${minutesSinceUpdate}m ago`;
  }
  
  indicator.innerHTML = `<span class="${freshnessClass} text-xs">● ${freshnessText}</span>`;
  indicator.title = `Last updated: ${lastUpdateTime.toLocaleString()}`;
}

// Start freshness monitoring
function startFreshnessMonitoring() {
  if (dataFreshnessInterval) clearInterval(dataFreshnessInterval);
  
  // Update every 30 seconds
  dataFreshnessInterval = setInterval(() => {
    updateFreshnessIndicator();
    
    // Auto-refresh if data is stale (> 1 hour old)
    const lastUpdated = AppState.data.meta?.lastUpdated;
    if (lastUpdated) {
      const hoursSinceUpdate = (Date.now() - new Date(lastUpdated)) / (1000 * 60 * 60);
      if (hoursSinceUpdate > 1 && AppState.settings.autoRefresh) {
        console.log('[Freshness] Data is stale, triggering auto-refresh');
        refreshData();
      }
    }
  }, 30000);
}

// ============================================
// SERVICE WORKER REGISTRATION
// ============================================

function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js')
      .then((registration) => {
        console.log('[SW] Registered:', registration.scope);
        
        // Listen for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              console.log('[SW] New version available, reloading...');
              window.location.reload();
            }
          });
        });
      })
      .catch((error) => {
        console.warn('[SW] Registration failed:', error);
      });
  }
}

// Clear service worker caches
async function clearServiceWorkerCaches() {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    const messageChannel = new MessageChannel();
    navigator.serviceWorker.controller.postMessage('CLEAR_CACHES', [messageChannel.port2]);
    return new Promise((resolve) => {
      messageChannel.port1.onmessage = (event) => {
        if (event.data === 'CACHES_CLEARED') {
          console.log('[SW] Caches cleared');
          resolve();
        }
      };
    });
  }
}

// ============================================
// REAL-TIME AUDIT SCANNER & AUTO-REFRESH
// ============================================

let autoRefreshInterval = null;
let lastAuditCount = 0;

// Initialize auto-refresh
function initAutoRefresh() {
  const toggle = document.getElementById('auto-refresh-toggle');
  const intervalSelect = document.getElementById('refresh-interval');
  
  if (toggle) {
    toggle.addEventListener('change', (e) => {
      if (e.target.checked) {
        startAutoRefresh();
      } else {
        stopAutoRefresh();
      }
    });
  }
  
  if (intervalSelect) {
    intervalSelect.addEventListener('change', () => {
      if (toggle && toggle.checked) {
        startAutoRefresh();
      }
    });
  }
}

function startAutoRefresh() {
  stopAutoRefresh();
  const intervalSec = parseInt(document.getElementById('refresh-interval')?.value || 60);
  console.log(`[AutoRefresh] Starting ${intervalSec}s interval`);
  
  autoRefreshInterval = setInterval(() => {
    console.log('[AutoRefresh] Refreshing data...');
    loadAllData().then(() => {
      renderCurrentTab();
      scanAuditsFolder();
    });
  }, intervalSec * 1000);
}

function stopAutoRefresh() {
  if (autoRefreshInterval) {
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
    console.log('[AutoRefresh] Stopped');
  }
}

// Real-time audit folder scanner
async function scanAuditsFolder() {
  try {
    const response = await fetch('data/audits.json?t=' + Date.now());
    const data = await response.json();
    
    const currentCount = data.totalAvailable || data.audits?.length || 0;
    const avgGrade = data.agentStats?.nox?.avgGrade || 0;
    
    // Update stats display
    const totalAuditsEl = document.getElementById('stat-total-audits');
    const avgGradeEl = document.getElementById('stat-avg-grade');
    
    if (totalAuditsEl) totalAuditsEl.textContent = currentCount;
    if (avgGradeEl) avgGradeEl.textContent = `${avgGrade}%`;
    
    // Detect new audits
    if (lastAuditCount > 0 && currentCount > lastAuditCount) {
      console.log(`[AuditScanner] ${currentCount - lastAuditCount} new audit(s) detected!`);
      // Flash notification or update indicator
      const indicator = document.getElementById('new-audit-indicator');
      if (indicator) {
        indicator.classList.remove('hidden');
        setTimeout(() => indicator.classList.add('hidden'), 5000);
      }
    }
    
    lastAuditCount = currentCount;
    console.log(`[AuditScanner] ${currentCount} audits, avg: ${avgGrade}%`);
    
  } catch (err) {
    console.error('[AuditScanner] Error:', err);
  }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  console.log(`[WorkTracker] Initializing... Cache version: ${CACHE_VERSION}`);
  
  // Register service worker for enhanced cache control
  registerServiceWorker();
  
  // Check if cache version changed (new deployment)
  const cacheVersionChanged = checkCacheVersion();
  if (cacheVersionChanged) {
    console.log('[Cache] New version detected, cache cleared');
  }
  
  initAutoRefresh();
  
  // Start auto-refresh if enabled (default: true, 30s)
  if (AppState.settings.autoRefresh) {
    startAutoRefresh();
  }
  
  scanAuditsFolder();
  
  // Also scan when tab becomes visible
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      scanAuditsFolder();
      // Refresh data when tab becomes visible after being hidden
      refreshData();
    }
  });
  
  // Keyboard shortcut: Ctrl/Cmd+Shift+R to clear cache and hard reload
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'R') {
      e.preventDefault();
      console.log('[Cache] Hard reload triggered via keyboard');
      clearAllCaches();
    }
  });
  
  // Page visibility change - refresh data when returning to page
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      console.log('[Visibility] Page visible, refreshing data');
      refreshData();
    }
  });
});
