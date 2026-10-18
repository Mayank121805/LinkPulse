/**
 * LinkPulse Single Link Detailed Analytics Controller
 */

let singleTrendChart = null;
let singleDeviceChart = null;
let singleBrowserChart = null;
let currentSingleRange = '30d';

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('linkDetailContainer');
  if (!container) return;

  const linkId = container.getAttribute('data-link-id');
  if (!linkId) return;

  setupSingleRangeListeners(linkId);
  loadSingleLinkAnalytics(linkId);
});

function setupSingleRangeListeners(linkId) {
  document.querySelectorAll('.single-date-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.single-date-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentSingleRange = pill.getAttribute('data-range') || '30d';
      loadSingleLinkAnalytics(linkId);
    });
  });
}

async function loadSingleLinkAnalytics(linkId) {
  try {
    const resp = await fetch(`/api/v1/analytics/link/${linkId}?range=${currentSingleRange}`);
    const res = await resp.json();

    if (!resp.ok || !res.success) {
      showToast(res.message || 'Error loading link analytics', 'error');
      return;
    }

    const data = res.analytics;
    document.getElementById('singleTotalClicks').textContent = Number(data.kpis.total_clicks || 0).toLocaleString();
    document.getElementById('singleUniqueVisitors').textContent = Number(data.kpis.unique_visitors || 0).toLocaleString();
    document.getElementById('singleLifetimeClicks').textContent = Number(data.kpis.lifetime_clicks || 0).toLocaleString();

    renderSingleTrendChart(data.clicks_over_time);
    renderSingleDeviceChart(data.device_breakdown);
    renderSingleBrowserChart(data.browser_breakdown);
    renderSingleReferrers(data.referrer_breakdown);
    renderRecentClicksTable(data.recent_clicks);

  } catch (err) {
    console.error('Failed to load link analytics:', err);
    showToast('Failed to load link analytics', 'error');
  } finally {
    if (window.lucide) lucide.createIcons();
  }
}

function renderSingleTrendChart(chartData) {
  const ctx = document.getElementById('singleTrendCanvas');
  if (!ctx) return;

  if (singleTrendChart) singleTrendChart.destroy();

  const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 240);
  gradient.addColorStop(0, 'rgba(37, 99, 235, 0.25)');
  gradient.addColorStop(1, 'rgba(37, 99, 235, 0.00)');

  singleTrendChart = new Chart(ctx, {
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
        pointRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94A3B8' } },
        y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { color: '#94A3B8', precision: 0 } }
      }
    }
  });
}

function renderSingleDeviceChart(devices) {
  const ctx = document.getElementById('singleDeviceCanvas');
  if (!ctx) return;
  if (singleDeviceChart) singleDeviceChart.destroy();

  const total = (devices.desktop || 0) + (devices.mobile || 0) + (devices.tablet || 0) + (devices.bot || 0);
  singleDeviceChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Desktop', 'Mobile', 'Tablet', 'Bots'],
      datasets: [{
        data: total > 0 ? [devices.desktop, devices.mobile, devices.tablet, devices.bot] : [1],
        backgroundColor: total > 0 ? ['#2563EB', '#0EA5E9', '#10B981', '#94A3B8'] : ['#E2E8F0'],
        borderWidth: 2,
        borderColor: '#FFFFFF'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 10 } } }
    }
  });
}

function renderSingleBrowserChart(browsers) {
  const ctx = document.getElementById('singleBrowserCanvas');
  if (!ctx) return;
  if (singleBrowserChart) singleBrowserChart.destroy();

  singleBrowserChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: browsers.map(b => b.label),
      datasets: [{
        data: browsers.map(b => b.count),
        backgroundColor: '#3B82F6',
        borderRadius: 4,
        barThickness: 16
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#94A3B8' } },
        y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { color: '#94A3B8', precision: 0 } }
      }
    }
  });
}

function renderSingleReferrers(referrers) {
  const container = document.getElementById('singleReferrersList');
  if (!container) return;

  if (!referrers || referrers.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-muted);">No referrer data yet</div>`;
    return;
  }

  const total = referrers.reduce((acc, curr) => acc + curr.count, 0) || 1;
  container.innerHTML = referrers.map(r => {
    const pct = ((r.count / total) * 100).toFixed(1);
    return `
      <div style="margin-bottom: 0.875rem;">
        <div style="display: flex; justify-content: space-between; font-size: 0.8125rem; margin-bottom: 0.2rem;">
          <span style="font-weight: 500; color: var(--text-primary);">${r.source}</span>
          <span style="color: var(--text-muted);">${r.count} (${pct}%)</span>
        </div>
        <div style="height: 6px; background-color: var(--bg-subtle); border-radius: 9999px; overflow: hidden;">
          <div style="height: 100%; width: ${pct}%; background: var(--brand-gradient);"></div>
        </div>
      </div>
    `;
  }).join('');
}

function renderRecentClicksTable(clicks) {
  const tbody = document.getElementById('singleClicksTableBody');
  if (!tbody) return;

  if (!clicks || clicks.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-muted);">No click events recorded yet</td></tr>`;
    return;
  }

  tbody.innerHTML = clicks.map(c => `
    <tr>
      <td style="font-size: 0.8125rem; color: var(--text-muted); white-space: nowrap;">
        ${new Date(c.timestamp).toLocaleString()}
      </td>
      <td style="font-weight: 500; color: var(--text-primary);">${c.country} (${c.city})</td>
      <td>
        <span class="badge ${c.device_category === 'bot' ? 'badge-limit' : 'badge-disabled'}">
          ${c.device_category}
        </span>
      </td>
      <td style="color: var(--text-secondary);">${c.browser} / ${c.os}</td>
      <td style="color: var(--text-muted); font-size: 0.8125rem;">${c.referrer_domain}</td>
      <td>
        <span class="badge ${c.is_bot ? 'badge-limit' : 'badge-active'}">
          ${c.is_bot ? 'Bot Detected' : 'Verified Visit'}
        </span>
      </td>
    </tr>
  `).join('');
}
