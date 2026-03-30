/* ── Drop Zone Interactions ─────────────────────────────────────────── */

document.querySelectorAll('.drop-zone').forEach(zone => {
  const input = zone.querySelector('input[type="file"]');
  const fileList = zone.querySelector('.file-list');
  const isMultiple = input && input.hasAttribute('multiple');
  zone.dt = new DataTransfer();

  ['dragenter','dragover'].forEach(ev => {
    zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add('dragover'); });
  });
  ['dragleave','drop'].forEach(ev => {
    zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove('dragover'); });
  });
  
  function addFiles(files) {
    if (!isMultiple) zone.dt = new DataTransfer(); // Reset if single file
    [...files].forEach(f => {
      // Prevent exact duplicates based on name, size, type
      if (![...zone.dt.files].some(existing => existing.name === f.name && existing.size === f.size)) {
        zone.dt.items.add(f);
      }
    });
    if (input) input.files = zone.dt.files;
    updateFileList(input, fileList);
  }

  zone.addEventListener('drop', e => {
    e.preventDefault();
    if (input) addFiles(e.dataTransfer.files);
  });
  
  if (input) {
    input.addEventListener('change', (e) => addFiles(e.target.files));
  }
});

function updateFileList(input, container) {
  if (!container) return;
  container.innerHTML = '';
  [...input.files].forEach(f => {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `<span class="fi-icon">📄</span> ${f.name} <span style="margin-left:auto;color:var(--text-muted)">${formatBytes(f.size)}</span>`;
    container.appendChild(item);
  });
  
  if (input && input.hasAttribute('multiple') && input.files.length > 0) {
    const hint = document.createElement('div');
    hint.style.marginTop = '0.5rem';
    hint.style.fontSize = '0.85rem';
    hint.style.fontWeight = '500';
    hint.style.color = 'var(--text-muted)';
    hint.textContent = '+ Click or drop more files here';
    container.appendChild(hint);
  }
}

function formatBytes(b) {
  if (b < 1024) return b + ' B';
  if (b < 1048576) return (b/1024).toFixed(1) + ' KB';
  return (b/1048576).toFixed(1) + ' MB';
}


/* ── Form Submit Handler ────────────────────────────────────────────── */

document.querySelectorAll('.tool-form').forEach(form => {
  form.addEventListener('submit', async e => {
    e.preventDefault();

    const formEl    = e.currentTarget;
    const spinnerEl = document.getElementById('spinner');
    const resultEl  = document.getElementById('result');
    const errorEl   = document.getElementById('error-msg');
    const submitBtn = formEl.querySelector('button[type="submit"]');

    // Reset state
    hideAll(spinnerEl, resultEl, errorEl);
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing…';
    show(spinnerEl);

    // Build FormData
    const data = new FormData(formEl);

    try {
      const res  = await fetch(formEl.dataset.action, { method: 'POST', body: data });
      const json = await res.json();

      hide(spinnerEl);

      if (json.success && json.download_url) {
        const dlBtn = document.getElementById('dl-btn');
        if (dlBtn) dlBtn.href = json.download_url;

        // Show saved location
        const pathEl = document.getElementById('result-path');
        if (pathEl && json.file_name) {
          pathEl.textContent = `📁 Saved to: Downloads\\${json.file_name}`;
        }

        show(resultEl);
      } else {
        showError(errorEl, json.error || 'An unexpected error occurred.');
      }
    } catch (err) {
      hide(spinnerEl);
      showError(errorEl, 'Network error — please try again.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = submitBtn.dataset.label || 'Process';
    }
  });
});

function show(el)  { if (el) el.classList.add('visible'); }
function hide(el)  { if (el) el.classList.remove('visible'); }
function hideAll(...els) { els.forEach(hide); }
function showError(el, msg) {
  if (!el) return;
  el.textContent = '⚠ ' + msg;
  show(el);
}
