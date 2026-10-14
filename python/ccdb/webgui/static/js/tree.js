// Directory tree page: remembered open state, a path filter, and info popups.
import { loadIntoModal } from './common.js';

const tree = document.getElementById('tree');
const filter = document.getElementById('tree-filter');
const OPEN_PREFIX = 'ccdb-open:';

function remember(key, open) {
  try { open ? localStorage.setItem(key, '1') : localStorage.removeItem(key); } catch (e) { /* storage blocked: nothing to remember */ }
}

tree.querySelectorAll('details').forEach(details => {
  const key = OPEN_PREFIX + details.dataset.path;
  try { if (localStorage.getItem(key)) details.open = true; } catch (e) {}
  details.addEventListener('toggle', () => remember(key, details.open));
});

// Hide the nodes whose path does not contain the text; open every folder while a filter is active,
// so the matches are visible, and fall back to the remembered state when the box is cleared.
filter.addEventListener('input', () => {
  const needle = filter.value.trim().toLowerCase();
  tree.querySelectorAll('li').forEach(item => {
    item.hidden = Boolean(needle) && !item.dataset.path.toLowerCase().includes(needle);
  });
  tree.querySelectorAll('details').forEach(details => {
    let open = true;
    if (!needle) { try { open = Boolean(localStorage.getItem(OPEN_PREFIX + details.dataset.path)); } catch (e) { open = false; } }
    details.open = open;
  });
});

tree.addEventListener('click', event => {
  const button = event.target.closest('button.info');
  if (!button) return;
  event.preventDefault();
  loadIntoModal(button.dataset.url);
});
