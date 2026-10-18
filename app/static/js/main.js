/**
 * LinkPulse Core JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide icons
  if (window.lucide) {
    lucide.createIcons();
  }

  // Mobile sidebar drawer
  const mobileToggle = document.getElementById('mobileSidebarToggle');
  const sidebar = document.getElementById('appSidebar');
  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && !mobileToggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  // Setup modals close buttons and backdrop clicks
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        closeModal(backdrop.id);
      }
    });
  });

  document.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('.modal-backdrop');
      if (modal) {
        closeModal(modal.id);
      }
    });
  });

  // Setup Landing Page Instant Shortener
  initLandingShortener();
});

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    if (window.lucide) lucide.createIcons({ root: modal });
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

function initLandingShortener() {
  const shortenForm = document.getElementById('landingShortenForm');
  if (!shortenForm) return;

  const urlInput = document.getElementById('landingUrlInput');
  const aliasInput = document.getElementById('landingAliasInput');
  const aliasRow = document.getElementById('landingAliasRow');
  const toggleAliasBtn = document.getElementById('toggleAliasBtn');
  const resultContainer = document.getElementById('landingShortenResult');
  const submitBtn = shortenForm.querySelector('button[type="submit"]');

  if (toggleAliasBtn && aliasRow) {
    toggleAliasBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const isHidden = aliasRow.style.display === 'none';
      aliasRow.style.display = isHidden ? 'block' : 'none';
      toggleAliasBtn.innerHTML = isHidden 
        ? '<i data-lucide="minus-circle" style="width: 14px; height: 14px;"></i> Hide custom alias'
        : '<i data-lucide="plus-circle" style="width: 14px; height: 14px;"></i> Add custom alias';
      if (window.lucide) lucide.createIcons({ root: toggleAliasBtn });
    });
  }

  shortenForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const destUrl = (urlInput.value || '').trim();
    const alias = aliasInput ? (aliasInput.value || '').trim() : '';

    if (!destUrl) {
      showToast('Please enter a destination URL', 'error');
      urlInput.focus();
      return;
    }

    const originalBtnHtml = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Shortening...';

    try {
      const resp = await fetch('/api/v1/links/quick-shorten', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination_url: destUrl,
          custom_alias: alias
        })
      });

      const res = await resp.json();
      if (!resp.ok || !res.success) {
        showToast(res.message || 'Error creating short link', 'error');
      } else {
        showToast('Link shortened successfully!', 'success');
        renderLandingResult(res.link, res.qr_data_uri);
      }
    } catch (err) {
      showToast('Network error while creating link', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnHtml;
      if (window.lucide) lucide.createIcons({ root: submitBtn });
    }
  });

  function renderLandingResult(link, qrDataUri) {
    if (!resultContainer) return;
    resultContainer.style.display = 'block';
    resultContainer.innerHTML = `
      <div style="background-color: var(--primary-subtle); border: 1px solid rgba(37,99,235,0.2); border-radius: var(--radius-lg); padding: 1.25rem;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
          <div style="flex: 1; min-width: 200px;">
            <div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: var(--primary); margin-bottom: 0.25rem;">Your Short Link is Ready:</div>
            <div style="font-family: monospace; font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">${link.short_url}</div>
            <div style="font-size: 0.8125rem; color: var(--text-muted); margin-top: 0.25rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 380px;">
              Destination: ${link.destination_url}
            </div>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <button class="btn btn-primary btn-sm" onclick="copyToClipboard('${link.short_url}')">
              <i data-lucide="copy" style="width: 14px; height: 14px;"></i> Copy
            </button>
            <a href="${link.short_url}" target="_blank" class="btn btn-secondary btn-sm">
              <i data-lucide="external-link" style="width: 14px; height: 14px;"></i> Test Link
            </a>
          </div>
        </div>
      </div>
    `;
    if (window.lucide) lucide.createIcons({ root: resultContainer });
  }
}
