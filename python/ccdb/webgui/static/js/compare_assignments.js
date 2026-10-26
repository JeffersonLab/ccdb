// Compare page: a changed table reloads the page with that table alone, so the variation selects list the
// table's variations. The sides are dropped on purpose: they named assignments of the previous table.
const form = document.getElementById('compare-form');
if (form) {
  form.elements.table.addEventListener('change', () => {
    const table = form.elements.table.value.trim();
    location.assign(location.pathname + (table ? '?table=' + encodeURIComponent(table) : ''));
  });
}
