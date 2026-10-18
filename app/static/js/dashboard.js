/**
 * LinkPulse Dashboard Analytics Controller
 */

let clicksTrendChartInstance = null;
let deviceChartInstance = null;
let browserChartInstance = null;
let currentRange = '7d';
let currentCampaign = '';

document.addEventListener('DOMContentLoaded', () => {
  setupFilterListeners();
  loadDashboardData();
});

function setupFilterListeners() {
  // Date range pills
  document.querySelectorAll('.date-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.date-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentRange = pill.getAttribute('data-range') || '7d';
      loadDashboardData();
    });
  });

  // Campaign filter dropdown
  const campSelect = document.getElementById('dashboardCampaignFilter');
  if (campSelect) {
    campSelect.addEventListener('change', () => {
      currentCampaign = campSelect.value;
      loadDashboardData();
    });
  }
}

async function loadDashboardData() {
  const loadingOverlay = document.getElementById('dashboardLoading');
  if (loadingOverlay) loadingOverlay.style.display = 'flex';

  try {
    let url = `/api/v1/analytics/overview?range=${currentRange}`;
    if (currentCampaign) {
      url += `&campaign_id=${currentCampaign}`;
    }

    const response = await fetch(url);
    const result = await response.json();

    if (!response.ok || !result.success) {
      showToast(result.message || 'Error loading dashboard analytics', 'error');
      return;
    }

    const data = result.analytics;
    updateKPIs(data.kpis);
    renderClicksTrendChart(data.clicks_over_time);
    renderDeviceChart(data.device_breakdown);
    renderBrowserChart(data.browser_breakdown);
    renderReferrersList(data.referrer_breakdown);
    renderCampaignPerformance(data.campaign_performance);
    renderTopLinks(data.top_links);
    renderRecentActivity(data.recent_activity);
    renderExpiringAlerts(data.expiring_alerts);

  } catch (err) {
    console.error('Failed to load dashboard data:', err);
    showToast('Failed to load real-time analytics data', 'error');
  } finally {
    if (loadingOverlay) loadingOverlay.style.display = 'none';
    if (window.lucide) lucide.createIcons();
  }
}

function updateKPIs(kpis) {
  if (!kpis) return;
  animateValue('kpiTotalClicks', kpis.total_clicks || 0);
  animateValue('kpiActiveLinks', kpis.active_links || 0);
  animateValue('kpiTotalLinks', kpis.total_links || 0);
  animateValue('kpiDisabledLinks', kpis.disabled_or_expired || 0);
  
  const uniqueEl = document.getElementById('kpiUniqueVisitors');
  if (uniqueEl) animateValue('kpiUniqueVisitors', kpis.unique_visitors || 0);
}

function animateValue(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = Number(value).toLocaleString();
}

function renderClicksTrendChart(chartData) {
  const ctx = document.getElementById('clicksTrendCanvas');
  if (!ctx) return;

  if (clicksTrendChartInstance) {
    clicksTrendChartInstance.destroy();
  }

  const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 260);
  gradient.addColorStop(0, 'rgba(37, 99, 235, 0.25)');
  gradient.addColorStop(1, 'rgba(37, 99, 235, 0.00)');

  clicksTrendChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: chartData.labels || [],
      datasets: [{
        label: 'Clicks',
        data: chartData.data || [],
        borderColor: '#2563EB',
        borderWidth: 2.5,
        backgroundColor: gradient,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: '#FFFFFF',
        pointBorderColor: '#2563EB',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0F172A',
          titleColor: '#94A3B8',
          bodyColor: '#FFFFFF',
          padding: 10,
          cornerRadius: 8,
          displayColors: false,
          callbacks: {
            label: (item) => `${item.parsed.y} click${item.parsed.y === 1 ? '' : 's'}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#94A3B8', font: { size: 11 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: '#F1F5F9' },
          ticks: {
            color: '#94A3B8',
            font: { size: 11 },
            precision: 0
          }
        }
      }
    }
  });
}

function renderDeviceChart(deviceBreakdown) {
  const ctx = document.getElementById('deviceChartCanvas');
  if (!ctx) return;

  if (deviceChartInstance) {
    deviceChartInstance.destroy();
  }

  const total = (deviceBreakdown.desktop || 0) + (deviceBreakdown.mobile || 0) + 
                (deviceBreakdown.tablet || 0) + (deviceBreakdown.bot || 0);

  const labels = ['Desktop', 'Mobile', 'Tablet', 'Bots'];
  const values = [
    deviceBreakdown.desktop || 0,
    deviceBreakdown.mobile || 0,
    deviceBreakdown.tablet || 0,
    deviceBreakdown.bot || 0
  ];

  deviceChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: total > 0 ? values : [1],
        backgroundColor: total > 0 
          ? ['#2563EB', '#0EA5E9', '#10B981', '#94A3B8']
          : ['#E2E8F0'],
        borderWidth: 2,
        borderColor: '#FFFFFF',
        hoverOffset: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            boxWidth: 12,
            padding: 14,
            color: '#475569',
            font: { size: 12 }
          }
        },
        tooltip: {
          enabled: total > 0,
          backgroundColor: '#0F172A',
          callbacks: {
            label: (item) => {
              const count = values[item.dataIndex];
              const pct = total > 0 ? ((count / total) * 100).toFixed(1) : 0;
              return `${labels[item.dataIndex]}: ${count} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

function renderBrowserChart(browserData) {
  const ctx = document.getElementById('browserChartCanvas');
  if (!ctx) return;

  if (browserChartInstance) {
    browserChartInstance.destroy();
  }

  const labels = browserData.map(b => b.label);
  const data = browserData.map(b => b.count);

  browserChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels.length > 0 ? labels : ['None'],
      datasets: [{
        label: 'Clicks',
        data: data.length > 0 ? data : [0],
        backgroundColor: '#3B82F6',
        borderRadius: 6,
        barThickness: 20
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#94A3B8', font: { size: 11 } }
        },
        y: {
          beginAtZero: true,
          grid: { color: '#F1F5F9' },
          ticks: { color: '#94A3B8', precision: 0 }
        }
      }
    }
  });
}

function renderReferrersList(referrers) {
  const container = document.getElementById('referrersList');
  if (!container) return;

  if (!referrers || referrers.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem;">No traffic source data available yet</div>`;
    return;
  }

  const total = referrers.reduce((acc, curr) => acc + curr.count, 0) || 1;
  container.innerHTML = referrers.map(r => {
    const pct = ((r.count / total) * 100).toFixed(1);
    return `
      <div style="margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; font-size: 0.8125rem; font-weight: 500; margin-bottom: 0.25rem;">
          <span style="color: var(--text-primary);">${r.source}</span>
          <span style="color: var(--text-muted);">${r.count} (${pct}%)</span>
        </div>
        <div style="height: 6px; background-color: var(--bg-subtle); border-radius: var(--radius-full); overflow: hidden;">
          <div style="height: 100%; width: ${pct}%; background: var(--brand-gradient); border-radius: var(--radius-full);"></div>
        </div>
      </div>
    `;
  }).join('');
}

function renderCampaignPerformance(campaigns) {
  const container = document.getElementById('campaignPerformanceList');
  if (!container) return;

  if (!campaigns || campaigns.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem;">No campaigns created yet</div>`;
    return;
  }

  container.innerHTML = campaigns.map(c => `
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 0; border-bottom: 1px solid var(--border-subtle);">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <div style="width: 12px; height: 12px; border-radius: 50%; background-color: ${c.color || '#2563EB'};"></div>
        <div>
          <div style="font-size: 0.875rem; font-weight: 600; color: var(--text-primary);">${c.name}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${c.links_count} links linked</div>
        </div>
      </div>
      <div style="text-align: right;">
        <div style="font-size: 0.9375rem; font-weight: 700; color: var(--text-primary);">${c.total_clicks}</div>
        <div style="font-size: 0.6875rem; color: var(--text-muted);">clicks</div>
      </div>
    </div>
  `).join('');
}

function renderTopLinks(links) {
  const tbody = document.getElementById('topLinksTableBody');
  if (!tbody) return;

  if (!links || links.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-muted);">No links created yet. Click "Create Link" to begin.</td></tr>`;
    return;
  }

  tbody.innerHTML = links.map(l => `
    <tr>
      <td>
        <div style="font-weight: 600; color: var(--text-primary);">${l.title}</div>
        <div style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">${l.short_url}</div>
      </td>
      <td>
        <span class="badge badge-${l.status}">
          <span class="badge-dot"></span>
          ${l.status.replace('_', ' ')}
        </span>
      </td>
      <td style="font-weight: 700; color: var(--text-primary);">${l.clicks_count}</td>
      <td style="color: var(--text-muted); font-size: 0.8125rem;">${l.campaign_name || '—'}</td>
      <td style="text-align: right;">
        <div style="display: inline-flex; gap: 0.25rem;">
          <button class="btn btn-icon btn-sm" title="Copy Short Link" onclick="copyToClipboard('${l.short_url}')">
            <i data-lucide="copy" style="width: 14px; height: 14px;"></i>
          </button>
          <a href="/links/${l.id}" class="btn btn-icon btn-sm" title="View Detailed Analytics">
            <i data-lucide="bar-chart-2" style="width: 14px; height: 14px;"></i>
          </a>
        </div>
      </td>
    </tr>
  `).join('');
}

function renderRecentActivity(events) {
  const container = document.getElementById('recentActivityFeed');
  if (!container) return;

  if (!events || events.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.875rem;">No recent click events</div>`;
    return;
  }

  container.innerHTML = events.map(ev => {
    const formattedDate = new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return `
      <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.625rem 0; border-bottom: 1px solid var(--border-subtle); font-size: 0.8125rem;">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
          <span style="font-weight: 600; color: var(--primary); font-family: monospace;">/${ev.short_code}</span>
          <span style="color: var(--text-muted);">from</span>
          <span style="color: var(--text-secondary);">${ev.country} (${ev.browser})</span>
        </div>
        <div style="color: var(--text-muted); font-size: 0.75rem;">${formattedDate}</div>
      </div>
    `;
  }).join('');
}

function renderExpiringAlerts(alerts) {
  const container = document.getElementById('expiringAlertsContainer');
  if (!container) return;

  if (!alerts || alerts.length === 0) {
    container.style.display = 'none';
    return;
  }

  container.style.display = 'block';
  container.innerHTML = `
    <div style="background-color: var(--status-expired-bg); border: 1px solid var(--status-expired-border); border-radius: var(--radius-lg); padding: 1rem 1.25rem; display: flex; align-items: flex-start; gap: 0.75rem;">
      <i data-lucide="alert-circle" style="color: var(--status-expired-text); width: 20px; height: 20px; flex-shrink: 0; margin-top: 2px;"></i>
      <div style="flex: 1;">
        <div style="font-size: 0.875rem; font-weight: 600; color: var(--status-expired-text);">Links Expiring Soon</div>
        <div style="font-size: 0.8125rem; color: #92400E; margin-top: 0.25rem;">
          You have ${alerts.length} link(s) scheduled to expire in the next 7 days: 
          <strong>${alerts.map(a => '/' + a.effective_code).join(', ')}</strong>.
        </div>
      </div>
    </div>
  `;
}
