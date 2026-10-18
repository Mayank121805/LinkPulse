/**
 * LinkPulse CSV Bulk Import Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  setupCsvDropzone();
});

function setupCsvDropzone() {
  const dropzone = document.getElementById('csvDropzone');
  const fileInput = document.getElementById('csvFileInput');
  const selectedInfo = document.getElementById('selectedFileInfo');
  const fileNameText = document.getElementById('selectedFileName');
  const submitBtn = document.getElementById('importSubmitBtn');
  const form = document.getElementById('csvUploadForm');

  if (!dropzone || !fileInput) return;

  dropzone.addEventListener('click', () => fileInput.click());

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--primary)';
      dropzone.style.backgroundColor = 'var(--primary-subtle)';
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--border-subtle)';
      dropzone.style.backgroundColor = 'transparent';
    });
  });

  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelected(fileInput.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  function handleFileSelected(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      showToast('Please select a valid .csv file', 'error');
      fileInput.value = '';
      return;
    }
    fileNameText.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    selectedInfo.style.display = 'flex';
    submitBtn.disabled = false;
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!fileInput.files || fileInput.files.length === 0) {
        showToast('Please select a CSV file first', 'error');
        return;
      }

      const formData = new FormData();
      formData.append('file', fileInput.files[0]);

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner"></span> Processing CSV...';

      try {
        const resp = await fetch('/api/v1/import/csv', {
          method: 'POST',
          body: formData
        });
        const res = await resp.json();

        if (!resp.ok || !res.success) {
          showToast(res.message || 'Error processing CSV file', 'error');
        } else {
          showToast('CSV import completed!', 'success');
          renderImportResults(res.results);
        }
      } catch (err) {
        showToast('Network error while uploading CSV', 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Upload & Process Links';
      }
    });
  }
}

function renderImportResults(results) {
  const container = document.getElementById('importResultsContainer');
  if (!container) return;

  container.style.display = 'block';

  document.getElementById('importTotalCount').textContent = results.total_rows || 0;
  document.getElementById('importValidCount').textContent = results.valid_count || 0;
  document.getElementById('importErrorCount').textContent = results.error_count || 0;

  // Render Error Rows Table if any
  const errorsCard = document.getElementById('importErrorsCard');
  const errorsTbody = document.getElementById('importErrorsTableBody');
  if (results.errors && results.errors.length > 0) {
    errorsCard.style.display = 'block';
    errorsTbody.innerHTML = results.errors.map(err => `
      <tr>
        <td style="font-weight: 600; color: #DC2626;">Row ${err.row}</td>
        <td style="font-family: monospace; font-size: 0.8125rem; color: var(--text-secondary); max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
          ${err.url || '—'}
        </td>
        <td style="color: #991B1B; font-size: 0.8125rem;">${err.reason}</td>
      </tr>
    `).join('');
  } else {
    errorsCard.style.display = 'none';
  }

  // Render Valid Imported Links Table
  const validCard = document.getElementById('importValidCard');
  const validTbody = document.getElementById('importValidTableBody');
  if (results.imported_links && results.imported_links.length > 0) {
    validCard.style.display = 'block';
    validTbody.innerHTML = results.imported_links.map(l => `
      <tr>
        <td style="font-weight: 600; color: #059669;">Row ${l.row}</td>
        <td style="font-weight: 600; color: var(--text-primary);">${l.title}</td>
        <td style="font-family: monospace; font-size: 0.8125rem; color: var(--primary);">/${l.short_code}</td>
        <td style="font-size: 0.8125rem; color: var(--text-muted);">${l.campaign}</td>
      </tr>
    `).join('');
  } else {
    validCard.style.display = 'none';
  }

  // Scroll into view
  container.scrollIntoView({ behavior: 'smooth' });
}
