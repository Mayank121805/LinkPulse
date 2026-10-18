/**
 * LinkPulse Admin Governance Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  loadAdminStats();
  loadAdminUsers();
  loadAdminLinks();
  loadBlockedDomains();
  loadAdminLogs();
  setupBlockedDomainForm();
});

async function loadAdminStats() {
  try {
    const resp = await fetch('/admin/api/stats');
    const res = await resp.json();
    if (res.success && res.stats) {
      document.getElementById('adminTotalUsers').textContent = res.stats.total_users;
      document.getElementById('adminTotalLinks').textContent = res.stats.total_links;
      document.getElementById('adminTotalClicks').textContent = res.stats.total_clicks;
      document.getElementById('adminBlockedDomains').textContent = res.stats.blocked_domains;
      document.getElementById('adminBotClicks').textContent = res.stats.bot_clicks;
    }
  } catch (err) {
    console.error('Failed to load admin stats:', err);
  }
}

async function loadAdminUsers() {
  const tbody = document.getElementById('adminUsersTableBody');
  if (!tbody) return;

  try {
    const resp = await fetch('/admin/api/users');
    const res = await resp.json();

    if (!res.success || !res.users) return;

    tbody.innerHTML = res.users.map(u => `
      <tr>
        <td>
          <div style="font-weight: 600; color: var(--text-primary);">${u.username}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${u.email}</div>
        </td>
        <td>
          <span class="badge ${u.role === 'admin' ? 'badge-active' : 'badge-disabled'}">
            ${u.role}
          </span>
        </td>
        <td>
          <span class="badge ${u.is_active ? 'badge-active' : 'badge-limit'}">
            ${u.is_active ? 'Active' : 'Deactivated'}
          </span>
        </td>
        <td style="font-weight: 600;">${u.links_count}</td>
        <td style="font-weight: 600; color: var(--primary);">${u.total_clicks}</td>
        <td style="text-align: right;">
          <div style="display: inline-flex; gap: 0.35rem;">
            <button class="btn btn-secondary btn-sm" onclick="toggleUserStatus(${u.id})">
              ${u.is_active ? 'Deactivate' : 'Activate'}
            </button>
            <button class="btn btn-outline btn-sm" onclick="toggleUserRole(${u.id})">
              ${u.role === 'admin' ? 'Demote to User' : 'Make Admin'}
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Failed to load admin users:', err);
  }
}

async function toggleUserStatus(userId) {
  try {
    const resp = await fetch(`/admin/api/users/${userId}/toggle-status`, { method: 'POST' });
    const res = await resp.json();
    if (!resp.ok || !res.success) {
      showToast(res.message || 'Error updating status', 'error');
    } else {
      showToast(res.message, 'success');
      loadAdminUsers();
      loadAdminStats();
    }
  } catch (err) {
    showToast('Network error', 'error');
  }
}

async function toggleUserRole(userId) {
  try {
    const resp = await fetch(`/admin/api/users/${userId}/toggle-role`, { method: 'POST' });
    const res = await resp.json();
    if (!resp.ok || !res.success) {
      showToast(res.message || 'Error changing role', 'error');
    } else {
      showToast(res.message, 'success');
      loadAdminUsers();
    }
  } catch (err) {
    showToast('Network error', 'error');
  }
}

async function loadAdminLinks() {
  const tbody = document.getElementById('adminLinksTableBody');
  if (!tbody) return;

  try {
    const resp = await fetch('/admin/api/links');
    const res = await resp.json();
    if (!res.success || !res.links) return;

    tbody.innerHTML = res.links.map(l => `
      <tr>
        <td style="max-width: 260px;">
          <div style="font-weight: 600; color: var(--text-primary);">${l.title}</div>
          <div style="font-family: monospace; font-size: 0.8125rem; color: var(--primary);">${l.short_url}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${l.destination_url}
          </div>
        </td>
        <td>
          <span style="font-size: 0.8125rem; font-weight: 500; color: var(--text-primary);">@${l.owner_username}</span>
        </td>
        <td>
          <span class="badge badge-${l.status}">
            <span class="badge-dot"></span>
            ${l.status}
          </span>
        </td>
        <td style="font-weight: 700;">${l.clicks_count}</td>
        <td style="text-align: right;">
          <button class="btn btn-sm ${l.is_active ? 'btn-danger' : 'btn-secondary'}" onclick="takedownLink(${l.id}, 'disable')">
            ${l.is_active ? 'Take Down' : 'Reactivate'}
          </button>
        </td>
      </tr>
    `).join('');
    if (window.lucide) lucide.createIcons({ root: tbody });
  } catch (err) {
    console.error('Failed to load admin links:', err);
  }
}

async function takedownLink(linkId, action) {
  try {
    const resp = await fetch(`/admin/api/links/${linkId}/takedown`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action })
    });
    const res = await resp.json();
    if (!resp.ok || !res.success) {
      showToast(res.message || 'Error executing action', 'error');
    } else {
      showToast(res.message, 'success');
      loadAdminLinks();
      loadAdminStats();
    }
  } catch (err) {
    showToast('Network error', 'error');
  }
}

async function loadBlockedDomains() {
  const tbody = document.getElementById('blockedDomainsTableBody');
  if (!tbody) return;

  try {
    const resp = await fetch('/admin/api/blocked-domains');
    const res = await resp.json();
    if (!res.success || !res.blocked_domains) return;

    if (res.blocked_domains.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No blocked domains</td></tr>`;
      return;
    }

    tbody.innerHTML = res.blocked_domains.map(b => `
      <tr>
        <td style="font-family: monospace; font-weight: 600; color: #DC2626;">${b.domain}</td>
        <td style="font-size: 0.8125rem; color: var(--text-secondary);">${b.reason}</td>
        <td style="font-size: 0.75rem; color: var(--text-muted);">${b.created_by}</td>
        <td style="text-align: right;">
          <button class="btn btn-outline btn-sm" onclick="removeBlockedDomain(${b.id})">
            Unblock
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Failed to load blocked domains:', err);
  }
}

function setupBlockedDomainForm() {
  const form = document.getElementById('addBlockedDomainForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const domain = document.getElementById('blockDomainInput').value.trim();
    const reason = document.getElementById('blockReasonInput').value.trim();

    if (!domain) {
      showToast('Domain is required', 'error');
      return;
    }

    try {
      const resp = await fetch('/admin/api/blocked-domains', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain, reason })
      });
      const res = await resp.json();

      if (!resp.ok || !res.success) {
        showToast(res.message || 'Error blocking domain', 'error');
      } else {
        showToast(res.message, 'success');
        closeModal('addBlockedDomainModal');
        form.reset();
        loadBlockedDomains();
        loadAdminStats();
      }
    } catch (err) {
      showToast('Network error while blocking domain', 'error');
    }
  });
}

async function removeBlockedDomain(domainId) {
  if (!confirm('Are you sure you want to unblock this domain?')) return;
  try {
    const resp = await fetch(`/admin/api/blocked-domains/${domainId}`, { method: 'DELETE' });
    const res = await resp.json();
    if (res.success) {
      showToast(res.message, 'success');
      loadBlockedDomains();
      loadAdminStats();
    }
  } catch (err) {
    showToast('Network error', 'error');
  }
}

async function loadAdminLogs() {
  const container = document.getElementById('adminLogsFeed');
  if (!container) return;

  try {
    const resp = await fetch('/admin/api/logs');
    const res = await resp.json();
    if (!res.success || !res.logs) return;

    container.innerHTML = res.logs.map(l => `
      <div style="padding: 0.75rem 0; border-bottom: 1px solid var(--border-subtle); font-size: 0.8125rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.2rem;">
          <span style="font-weight: 600; color: var(--text-primary);">${l.action}</span>
          <span style="color: var(--text-muted); font-size: 0.75rem;">${new Date(l.created_at).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}</span>
        </div>
        <div style="color: var(--text-secondary);">${l.details}</div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load admin logs:', err);
  }
}
