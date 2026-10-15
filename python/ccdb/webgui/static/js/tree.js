// Directory tree: remembered open state, a remembered order, a path filter, Expand / Collapse, and info popups.
// The tables page and the variation comparison page render the same markup (templates/_tree.html);
// a page opts out of the remembered open state with data-remember="no" on #tree. The order is a
// preference rather than a view state, so it applies on both pages.
import { loadIntoModal } from './common.js';

const OPEN_PREFIX = 'ccdb-open:';
const SORT_KEY = 'ccdb-tree-sort';  // 'id' after Sort by ID; absent for the default order, A…Z

function storeOpen(key, open) {
  try { open ? localStorage.setItem(key, '1') : localStorage.removeItem(key); } catch (e) { /* storage blocked: nothing to remember */ }
}

function storedOpen(key) {
  try { return Boolean(localStorage.getItem(key)); } catch (e) { return false; }
}

function storedSort() {
  try { return localStorage.getItem(SORT_KEY) === 'id' ? 'id' : 'name'; } catch (e) { return 'name'; }
}

function storeSort(by) {
  try { by === 'id' ? localStorage.setItem(SORT_KEY, 'id') : localStorage.removeItem(SORT_KEY); } catch (e) { /* storage blocked */ }
}

// Plain text matches anywhere in the path, case-insensitively. With * (any text) or ? (one character) the
// pattern must match the whole name, or the whole path when it contains a slash: the rule of `ccdb ls`.
function matcher(text) {
  if (!/[*?]/.test(text)) {
    const needle = text.toLowerCase();
    return path => path.toLowerCase().includes(needle);
  }
  const pattern = new RegExp('^' + text.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.') + '$', 'i');
  if (text.includes('/')) return path => pattern.test(path);
  return path => pattern.test(path.slice(path.lastIndexOf('/') + 1));
}

// The name of a node split for the natural order: digit runs compare as numbers, so layer2 comes before layer10.
// The server renders the tree in exactly this order (views.natural_key); the two must agree, or Sort A…Z would
// shuffle a page that was just loaded. split() with a capturing group alternates text and digit chunks, text first.
function nameKey(item) {
  const path = item.dataset.path;
  return path.slice(path.lastIndexOf('/') + 1).toLowerCase().split(/(\d+)/);
}

function compareNames(a, b) {
  const ka = nameKey(a), kb = nameKey(b);
  for (let i = 0; i < Math.min(ka.length, kb.length); i++) {
    const [x, y] = i % 2 ? [Number(ka[i]), Number(kb[i])] : [ka[i], kb[i]];
    if (x !== y) return x < y ? -1 : 1;
  }
  return ka.length - kb.length;
}

// Reorders the children of every list: directories first, then tables, each kind by name or by database id (the
// two kinds have separate id sequences, so they are never interleaved). Moving a <details> keeps its open state.
export function sortTree(tree, by) {
  const rank = item => (item.dataset.kind === 'dir' ? 0 : 1);
  const compare = by === 'id'
    ? (a, b) => rank(a) - rank(b) || Number(a.dataset.id) - Number(b.dataset.id)
    : (a, b) => rank(a) - rank(b) || compareNames(a, b);
  tree.querySelectorAll('ul').forEach(list => [...list.children].sort(compare).forEach(item => list.appendChild(item)));
}

export function initTree(tree, { filter = null, expandAll = null, collapseAll = null, sortButtons = [], remember = true } = {}) {
  const folders = [...tree.querySelectorAll('details')];
  const keyOf = folder => OPEN_PREFIX + folder.dataset.path;
  const filtering = () => Boolean(filter && filter.value.trim());

  // The order first, so the page never shows the name order to someone who chose ids.
  const sorters = [...sortButtons];
  const markSort = by => sorters.forEach(button => {
    const pressed = button.dataset.sort === by;
    button.classList.toggle('active', pressed);
    button.setAttribute('aria-pressed', String(pressed));
  });
  const initialSort = storedSort();
  if (initialSort === 'id') sortTree(tree, 'id');  // the page arrives in name order
  markSort(initialSort);
  sorters.forEach(button => button.addEventListener('click', () => {
    sortTree(tree, button.dataset.sort);
    storeSort(button.dataset.sort);
    markSort(button.dataset.sort);
  }));

  if (remember) {
    folders.forEach(folder => {
      folder.open = storedOpen(keyOf(folder));
      // `toggle` also fires, asynchronously, for the folders the filter opens. The filter view is transient,
      // so the state is recorded only while the filter box is empty.
      folder.addEventListener('toggle', () => { if (!filtering()) storeOpen(keyOf(folder), folder.open); });
    });
  }

  // The two buttons set every folder; the toggle listener above records the result.
  if (expandAll) expandAll.addEventListener('click', () => folders.forEach(folder => { folder.open = true; }));
  if (collapseAll) collapseAll.addEventListener('click', () => folders.forEach(folder => { folder.open = false; }));

  if (filter) {
    // A node is shown when it matches, when an ancestor matches (the whole subtree of a matching directory) or
    // when a descendant matches (the path down to a matching table stays visible). Every folder opens while a
    // filter is active, so the matches are in view; the remembered state returns when the box is cleared.
    filter.addEventListener('input', () => {
      const needle = filter.value.trim();
      const matches = needle ? matcher(needle) : null;
      const items = [...tree.querySelectorAll('li')];
      const shown = new Map();
      for (const item of items) {  // document order: a parent is decided before its children
        const parent = item.parentElement.closest('li');
        shown.set(item, !matches || matches(item.dataset.path) || Boolean(parent && shown.get(parent)));
      }
      for (const item of items.reverse()) {  // reverse order: a shown child makes its parent shown
        const parent = item.parentElement.closest('li');
        if (shown.get(item) && parent) shown.set(parent, true);
      }
      items.forEach(item => { item.hidden = !shown.get(item); });
      folders.forEach(folder => { folder.open = needle ? true : remember && storedOpen(keyOf(folder)); });
    });
    // A link such as /tree?filter=/test/mydir lands with the box prefilled by the server; apply it once.
    if (filter.value) filter.dispatchEvent(new Event('input'));
  }

  tree.addEventListener('click', event => {
    const button = event.target.closest('button.info');
    if (!button) return;
    event.preventDefault();
    loadIntoModal(button.dataset.url);
  });
}

const tree = document.getElementById('tree');
if (tree) {
  initTree(tree, {
    filter: document.getElementById('tree-filter'),
    expandAll: document.getElementById('tree-expand'),
    collapseAll: document.getElementById('tree-collapse'),
    sortButtons: document.querySelectorAll('button[data-sort]'),
    remember: tree.dataset.remember !== 'no',
  });
}
