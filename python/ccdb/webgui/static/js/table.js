// Live search and paging for the server-paginated tables.
// The page has a plain GET form marked data-live-table="#fragment-id" and the fragment below it. Typing or
// changing a filter re-fetches only the fragment (header X-Fragment: 1, same URL the form would submit to),
// swaps it in, and rewrites the address bar so the view stays shareable. Without JavaScript the form
// still works: Apply reloads the page.

const form = document.querySelector('form[data-live-table]');
const target = form && document.querySelector(form.dataset.liveTable);
if (form && target) {
  let timer = null;
  let inFlight = null;

  function formUrl() {
    const params = new URLSearchParams(new FormData(form));
    for (const [key, value] of [...params]) if (value === '') params.delete(key);  // keep URLs short
    const query = params.toString();
    return location.pathname + (query ? '?' + query : '');
  }

  async function load(url) {
    if (inFlight) inFlight.abort();
    inFlight = new AbortController();
    target.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(url, { headers: { 'X-Fragment': '1' }, signal: inFlight.signal });
      target.innerHTML = await response.text();
      history.replaceState(null, '', url);
      syncSortFields(url);
    } catch (error) {
      if (error.name !== 'AbortError') form.requestSubmit();  // fall back to a full page load
    } finally {
      target.removeAttribute('aria-busy');
    }
  }

  // Sort links live in the fragment; the hidden sort/order fields must follow them so the next filter keeps the order.
  function syncSortFields(url) {
    const params = new URL(url, location.href).searchParams;
    for (const name of ['sort', 'order']) {
      const field = form.elements[name];
      if (field && params.has(name)) field.value = params.get(name);
    }
  }

  form.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(() => load(formUrl()), 250);
  });
  form.addEventListener('submit', event => {
    event.preventDefault();
    clearTimeout(timer);
    load(formUrl());
  });
  target.addEventListener('click', event => {
    const link = event.target.closest('a.page-link, a.sort');
    if (!link || !link.getAttribute('href')) return;
    event.preventDefault();
    load(link.getAttribute('href'));
  });
}
