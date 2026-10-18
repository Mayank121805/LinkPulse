/**
 * LinkPulse Link Management & 2-Step Creation Wizard
 */

let currentPage = 1;
let currentSearch = '';
let currentStatus = 'all';
let currentCampaign = '';
let currentSort = 'created_desc';

document.addEventListener('DOMContentLoaded', () => {
  setupLinkTableFilters();
  setupCreateWizard();
  loadLinks();
});

function setupLinkTableFilters() {
  const searchInput = document.getElementById('linkSearchInput');
  if (searchInput) {
    let timeout = null;
    searchInput.addEventListener('input', () => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        currentSearch = searchInput.value.trim();
        currentPage = 1;
        loadLinks();
      }, 300);
    });
  }

  const statusSelect = document.getElementById('linkStatusFilter');
  if (statusSelect) {
    statusSelect.addEventListener('change', () => {
      currentStatus = statusSelect.value;
      currentPage = 1;
      loadLinks();
    });
  }

  const campSelect = document.getElementById('linkCampaignFilter');
  if (campSelect) {
    campSelect.addEventListener('change', () => {
      currentCampaign = campSelect.value;
      currentPage = 1;
      loadLinks();
    });
  }

  const sortSelect = document.getElementById('linkSortSelect');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      currentSort = sortSelect.value;
      currentPage = 1;
      loadLinks();
    });
  }
}

async function loadLinks() {
  const tbody = document.getElementById('linksTableBody');
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 3rem;"><div class="skeleton" style="height: 24px; max-width: 200px; margin: 0 auto;"></div></td></tr>`;

  try {
    let url = `/api/v1/links?page=${currentPage}&status=${currentStatus}&sort_by=${currentSort}`;
    if (currentSearch) url += `&search=${encodeURIComponent(currentSearch)}`;
    if (currentCampaign) url += `&campaign_id=${currentCampaign}`;

    const resp = await fetch(url);
    const data = await resp.json();

    if (!resp.ok || !data.success) {
      showToast(data.message || 'Error fetching links', 'error');
      return;
    }

    renderLinksTable(data.links);
    renderPagination(data.pagination);

  } catch (err) {
    console.error('Failed to load links:', err);
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #DC2626; padding: 2rem;">Error connecting to API.</td></tr>`;
  }
}

function renderLinksTable(links) {
  const tbody = document.getElementById('linksTableBody');
  if (!tbody) return;

  if (!links || links.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 3.5rem 1rem;">
          <div style="max-width: 320px; margin: 0 auto; color: var(--text-muted);">
            <i data-lucide="link-2-off" style="width: 40px; height: 40px; margin-bottom: 0.75rem; stroke-width: 1.5;"></i>
            <h4 style="color: var(--text-primary); margin-bottom: 0.25rem;">No links found</h4>
            <p style="font-size: 0.8125rem;">Create a new link or try adjusting your search filters.</p>
          </div>
        </td>
      </tr>
    `;
    if (window.lucide) lucide.createIcons({ root: tbody });
    return;
  }

  tbody.innerHTML = links.map(l => {
    const formattedCreated = new Date(l.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
    const tagsHtml = (l.tags || []).map(t => `<span class="tag-pill" style="border-left: 2px solid ${t.color_code};">${t.name}</span>`).join(' ');

    return `
      <tr>
        <td style="max-width: 280px;">
          <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${l.title}
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <a href="${l.short_url}" target="_blank" style="font-family: monospace; font-size: 0.8125rem; font-weight: 600; color: var(--primary);">
              ${l.short_url}
            </a>
            <button class="btn btn-icon btn-sm" style="padding: 2px 4px;" title="Copy Short Link" onclick="copyToClipboard('${l.short_url}')">
              <i data-lucide="copy" style="width: 12px; height: 12px;"></i>
            </button>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 0.25rem;">
            ${l.destination_url}
          </div>
        </td>
        <td>
          <span class="badge badge-${l.status}">
            <span class="badge-dot"></span>
            ${l.status.replace('_', ' ')}
          </span>
          ${l.is_password_protected ? '<span title="Password Protected" style="margin-left: 4px; color: var(--text-muted);"><i data-lucide="lock" style="width: 12px; height: 12px;"></i></span>' : ''}
        </td>
        <td style="font-weight: 700; color: var(--text-primary); font-size: 0.9375rem;">
          ${l.clicks_count}
          ${l.max_clicks ? `<span style="font-size: 0.75rem; font-weight: normal; color: var(--text-muted);">/ ${l.max_clicks}</span>` : ''}
        </td>
        <td>
          <div style="font-size: 0.8125rem; color: var(--text-secondary);">${l.campaign_name || '—'}</div>
          <div style="margin-top: 0.25rem; display: flex; flex-wrap: wrap; gap: 0.25rem;">${tagsHtml}</div>
        </td>
        <td style="font-size: 0.8125rem; color: var(--text-muted); white-space: nowrap;">
          ${formattedCreated}
          ${l.expires_at ? `<div style="font-size: 0.6875rem; color: #D97706;">Exp: ${new Date(l.expires_at).toLocaleDateString([], {month:'short', day:'numeric'})}</div>` : ''}
        </td>
        <td style="text-align: right; white-space: nowrap;">
          <div style="display: inline-flex; align-items: center; gap: 0.25rem;">
            <button class="btn btn-icon btn-sm" title="View QR Code" onclick="openQrModal(${l.id}, '${l.effective_code}', '${l.short_url}')">
              <i data-lucide="qr-code" style="width: 15px; height: 15px;"></i>
            </button>
            <a href="/links/${l.id}" class="btn btn-icon btn-sm" title="Analytics Details">
              <i data-lucide="bar-chart-2" style="width: 15px; height: 15px;"></i>
            </a>
            <button class="btn btn-icon btn-sm" title="${l.is_active ? 'Disable Link' : 'Enable Link'}" onclick="toggleLinkStatus(${l.id})">
              <i data-lucide="${l.is_active ? 'pause-circle' : 'play-circle'}" style="width: 15px; height: 15px; color: ${l.is_active ? '#64748B' : '#059669'};"></i>
            </button>
            <button class="btn btn-icon btn-sm" title="Delete Link" onclick="confirmDeleteLink(${l.id})">
              <i data-lucide="trash-2" style="width: 15px; height: 15px; color: #DC2626;"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons({ root: tbody });
}

function renderPagination(pg) {
  const container = document.getElementById('linksPagination');
  if (!container || !pg) return;

  if (pg.total_pages <= 1) {
    container.innerHTML = `<span style="font-size: 0.8125rem; color: var(--text-muted);">Showing ${pg.total_count} link(s)</span>`;
    return;
  }

  container.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between; width: 100%;">
      <span style="font-size: 0.8125rem; color: var(--text-muted);">
        Page ${pg.page} of ${pg.total_pages} (${pg.total_count} total links)
      </span>
      <div style="display: flex; gap: 0.5rem;">
        <button class="btn btn-secondary btn-sm" ${pg.page <= 1 ? 'disabled' : ''} onclick="goToPage(${pg.page - 1})">
          Previous
        </button>
        <button class="btn btn-secondary btn-sm" ${pg.page >= pg.total_pages ? 'disabled' : ''} onclick="goToPage(${pg.page + 1})">
          Next
        </button>
      </div>
    </div>
  `;
}

function goToPage(page) {
  currentPage = page;
  loadLinks();
}

async function toggleLinkStatus(linkId) {
  try {
    const resp = await fetch(`/api/v1/links/${linkId}/toggle`, { method: 'POST' });
    const res = await resp.json();
    if (!resp.ok || !res.success) {
      showToast(res.message || 'Error toggling link', 'error');
    } else {
      showToast(res.message, 'success');
      loadLinks();
    }
  } catch (err) {
    showToast('Failed to toggle link status', 'error');
  }
}

async function confirmDeleteLink(linkId) {
  if (!confirm('Are you sure you want to delete this short link? All click analytics will be permanently removed.')) {
    return;
  }

  try {
    const resp = await fetch(`/api/v1/links/${linkId}`, { method: 'DELETE' });
    const res = await resp.json();
    if (!resp.ok || !res.success) {
      showToast(res.message || 'Error deleting link', 'error');
    } else {
      showToast('Link deleted successfully', 'success');
      loadLinks();
    }
  } catch (err) {
    showToast('Network error while deleting link', 'error');
  }
}

function openQrModal(linkId, code, shortUrl) {
  const modal = document.getElementById('qrPreviewModal');
  if (!modal) return;

  const img = document.getElementById('qrModalImage');
  const codeText = document.getElementById('qrModalCode');
  const downloadBtn = document.getElementById('qrModalDownloadBtn');
  const testBtn = document.getElementById('qrModalTestBtn');

  if (img) img.src = `/api/v1/links/${linkId}/qr`;
  if (codeText) codeText.textContent = shortUrl;
  if (downloadBtn) downloadBtn.href = `/api/v1/links/${linkId}/qr?download=true`;
  if (testBtn) testBtn.href = shortUrl;

  openModal('qrPreviewModal');
}

// ==================== 2-STEP CREATE WIZARD ====================

function setupCreateWizard() {
  const wizardModal = document.getElementById('createLinkModal');
  if (!wizardModal) return;

  const btnNext = document.getElementById('wizardNextBtn');
  const btnPrev = document.getElementById('wizardPrevBtn');
  const btnSubmit = document.getElementById('wizardSubmitBtn');
  const stepIndicator1 = document.getElementById('stepIndicator1');
  const stepIndicator2 = document.getElementById('stepIndicator2');
  const pane1 = document.getElementById('wizardPane1');
  const pane2 = document.getElementById('wizardPane2');
  const paneSuccess = document.getElementById('wizardPaneSuccess');

  let currentStep = 1;

  function switchStep(step) {
    currentStep = step;
    if (step === 1) {
      stepIndicator1.classList.add('active');
      stepIndicator1.classList.remove('completed');
      stepIndicator2.classList.remove('active');
      pane1.classList.add('active');
      pane2.classList.remove('active');
      paneSuccess.classList.remove('active');
      btnPrev.style.display = 'none';
      btnNext.style.display = 'inline-flex';
      btnSubmit.style.display = 'none';
    } else if (step === 2) {
      stepIndicator1.classList.remove('active');
      stepIndicator1.classList.add('completed');
      stepIndicator2.classList.add('active');
      pane1.classList.remove('active');
      pane2.classList.add('active');
      paneSuccess.classList.remove('active');
      btnPrev.style.display = 'inline-flex';
      btnNext.style.display = 'none';
      btnSubmit.style.display = 'inline-flex';
      
      // Update review items in step 2
      document.getElementById('reviewDestUrl').textContent = document.getElementById('createDestUrl').value;
      const aliasVal = document.getElementById('createCustomAlias').value.trim();
      document.getElementById('reviewAlias').textContent = aliasVal ? '/' + aliasVal : 'Auto-generated code';
    }
  }

  if (btnNext) {
    btnNext.addEventListener('click', () => {
      const destUrl = document.getElementById('createDestUrl').value.trim();
      if (!destUrl) {
        showToast('Please enter a destination URL', 'error');
        document.getElementById('createDestUrl').focus();
        return;
      }
      try {
        const u = new URL(destUrl);
        if (!['http:', 'https:'].includes(u.protocol)) {
          showToast('Destination URL must start with http:// or https://', 'error');
          return;
        }
      } catch (e) {
        showToast('Please enter a valid URL (including https://)', 'error');
        return;
      }
      switchStep(2);
    });
  }

  if (btnPrev) {
    btnPrev.addEventListener('click', () => switchStep(1));
  }

  // Password toggle checkbox
  const pwCheckbox = document.getElementById('enablePasswordProtection');
  const pwInputGroup = document.getElementById('passwordInputGroup');
  if (pwCheckbox && pwInputGroup) {
    pwCheckbox.addEventListener('change', () => {
      pwInputGroup.style.display = pwCheckbox.checked ? 'block' : 'none';
    });
  }

  // Form Submit
  const createForm = document.getElementById('createLinkForm');
  if (createForm) {
    createForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const payload = {
        destination_url: document.getElementById('createDestUrl').value.trim(),
        custom_alias: document.getElementById('createCustomAlias').value.trim(),
        title: document.getElementById('createTitle').value.trim(),
        campaign_id: document.getElementById('createCampaign').value || null,
        tags: document.getElementById('createTags').value.split(',').map(t => t.trim()).filter(Boolean),
        max_clicks: document.getElementById('createMaxClicks').value || null,
        expires_at: document.getElementById('createExpiresAt').value || null,
        password: pwCheckbox && pwCheckbox.checked ? document.getElementById('createPassword').value : null
      };

      btnSubmit.disabled = true;
      btnSubmit.innerHTML = 'Creating...';

      try {
        const resp = await fetch('/api/v1/links', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const res = await resp.json();
        if (!resp.ok || !res.success) {
          showToast(res.message || 'Error creating link', 'error');
        } else {
          showToast('Short link published successfully!', 'success');
          // Show Step 3 Success View
          pane1.classList.remove('active');
          pane2.classList.remove('active');
          paneSuccess.classList.add('active');
          document.querySelector('.wizard-progress').style.display = 'none';
          document.querySelector('.modal-footer').style.display = 'none';

          document.getElementById('successShortUrl').textContent = res.link.short_url;
          document.getElementById('successQrImage').src = res.qr_data_uri;
          document.getElementById('successCopyBtn').onclick = () => copyToClipboard(res.link.short_url);
          document.getElementById('successTestBtn').href = res.link.short_url;

          // Reload table
          loadLinks();
        }
      } catch (err) {
        showToast('Network error while creating link', 'error');
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = 'Publish Short Link';
      }
    });
  }
}
