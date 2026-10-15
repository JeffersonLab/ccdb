// Compare page: a changed variation reloads the page with that variation and its own direct parent; a changed
// parent reloads the comparison. Run and time submit through the Compare button or Enter. Empty fields stay
// out of the URL, so the address bar shows the same URL the form would produce.
const form = document.getElementById('compare-form');
if (form) {
  function reload() {
    const params = new URLSearchParams(new FormData(form));
    for (const [key, value] of [...params]) if (value === '') params.delete(key);
    location.assign(location.pathname + '?' + params.toString());
  }
  form.elements.variation.addEventListener('change', () => {
    form.elements.parent.value = '';  // the default parent of the new variation
    reload();
  });
  form.elements.parent.addEventListener('change', reload);
}
