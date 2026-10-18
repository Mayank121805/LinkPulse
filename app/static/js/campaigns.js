/**
 * LinkPulse Campaigns Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  setupCampaignForms();
});

function setupCampaignForms() {
  const form = document.getElementById('createCampaignForm');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('campName').value.trim();
      const description = document.getElementById('campDesc').value.trim();
      const color = document.getElementById('campColor').value;

      if (!name) {
        showToast('Campaign name is required', 'error');
        return;
      }

      try {
        const resp = await fetch('/api/v1/campaigns', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, description, color_code: color })
        });
        const res = await resp.json();
        if (!resp.ok || !res.success) {
          showToast(res.message || 'Error creating campaign', 'error');
        } else {
          showToast('Campaign created successfully!', 'success');
          closeModal('createCampaignModal');
          window.location.reload();
        }
      } catch (err) {
        showToast('Network error while creating campaign', 'error');
      }
    });
  }
}

async function deleteCampaign(campaignId) {
  if (!confirm('Are you sure you want to delete this campaign? Links will not be deleted, but will become unassigned.')) {
    return;
  }
  try {
    const resp = await fetch(`/api/v1/campaigns/${campaignId}`, { method: 'DELETE' });
    const res = await resp.json();
    if (!resp.ok || !res.success) {
      showToast(res.message || 'Error deleting campaign', 'error');
    } else {
      showToast('Campaign deleted successfully', 'success');
      window.location.reload();
    }
  } catch (err) {
    showToast('Network error', 'error');
  }
}
