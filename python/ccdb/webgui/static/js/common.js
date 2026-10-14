// Shared by every page: the theme menu and loading a fragment into the modal.
// The head of base.html already applied the theme before first paint; this module keeps it current.

const THEME_KEY = 'ccdb-theme';
const darkMedia = matchMedia('(prefers-color-scheme: dark)');

function storedTheme() {
  try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; }
}

function applyTheme() {
  const stored = storedTheme();
  const theme = stored === 'light' || stored === 'dark' ? stored : (darkMedia.matches ? 'dark' : 'light');
  document.documentElement.setAttribute('data-bs-theme', theme);
  document.querySelectorAll('#theme-menu [data-theme]').forEach(button => {
    button.classList.toggle('active', button.dataset.theme === (stored || 'auto'));
  });
}

export function initTheme() {
  applyTheme();
  document.querySelectorAll('#theme-menu [data-theme]').forEach(button => button.addEventListener('click', () => {
    try {
      if (button.dataset.theme === 'auto') localStorage.removeItem(THEME_KEY);
      else localStorage.setItem(THEME_KEY, button.dataset.theme);
    } catch (e) { /* private mode: the choice lasts for this page only */ }
    applyTheme();
  }));
  darkMedia.addEventListener('change', applyTheme);  // auto follows the OS while the page is open
}

// Fetches `url` and shows the returned HTML in the shared #info-modal. A non-OK response shows its text.
export async function loadIntoModal(url) {
  const modal = document.getElementById('info-modal');
  const content = modal.querySelector('.modal-content');
  try {
    const response = await fetch(url, { headers: { 'X-Fragment': '1' } });
    const text = await response.text();
    content.innerHTML = response.ok ? text : `<div class="modal-body text-danger">${escapeHtml(text)}</div>`;
  } catch (error) {
    content.innerHTML = `<div class="modal-body text-danger">${escapeHtml(String(error))}</div>`;
  }
  bootstrap.Modal.getOrCreateInstance(modal).show();  // `bootstrap` is the vendored bundle's global
}

export function escapeHtml(text) {
  return text.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

// Copy button of the assignment page (present on that page only; the guard keeps this inert elsewhere).
const button = document.getElementById('copy-request');
if (button) {
  const label = button.innerHTML;
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(button.dataset.text);
      button.textContent = 'Copied';
    } catch (error) {
      // Clipboard access needs a secure context (https or localhost); select the text so Ctrl+C works instead.
      const range = document.createRange();
      range.selectNodeContents(document.getElementById('request-string'));
      getSelection().removeAllRanges();
      getSelection().addRange(range);
      button.textContent = 'Select and press Ctrl+C';
    }
    setTimeout(() => { button.innerHTML = label; }, 1500);
  });
}

initTheme();
