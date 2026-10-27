// Pick to compare, on the versions page: the toggle button reveals a checkbox per assignment; the first two picked
// are A and B, a third pick drops the oldest one. The picks and the mode live in sessionStorage under the table's
// path, so paging, live search (which swaps the table fragment) and a reload keep them; the bar above the table
// shows the pair and links to the comparison. Without JavaScript the button stays hidden: the header's Compare
// button is the path to the form.
const bar = document.getElementById('pick-bar');
const toggle = document.getElementById('pick-toggle');
const fragment = document.getElementById('table-fragment');
if (bar && toggle && fragment) {
  const key = 'ccdb-pick:' + bar.dataset.table;
  const slots = [bar.querySelector('[data-slot=a]'), bar.querySelector('[data-slot=b]')];
  const compare = bar.querySelector('[data-compare]');
  let state = { on: false, picks: [] };
  try { state = { ...state, ...JSON.parse(sessionStorage.getItem(key) || '{}') }; } catch (e) { /* no storage: the mode lasts for this page only */ }

  function save() {
    try { sessionStorage.setItem(key, JSON.stringify(state)); } catch (e) { /* see above */ }
  }

  function render() {
    document.body.classList.toggle('picking', state.on);
    toggle.classList.toggle('active', state.on);
    toggle.setAttribute('aria-pressed', String(state.on));
    bar.hidden = !state.on;
    const picked = state.picks.map(pick => pick.request);
    fragment.querySelectorAll('input.pick').forEach(box => { box.checked = picked.includes(box.value); });
    slots.forEach((slot, i) => { slot.textContent = state.picks[i] ? state.picks[i].label : 'not picked'; slot.classList.toggle('text-body-secondary', !state.picks[i]); });
    if (state.picks.length === 2) {
      compare.href = bar.dataset.compareUrl + '?a=' + encodeURIComponent(picked[0]) + '&b=' + encodeURIComponent(picked[1]);
      compare.classList.remove('disabled');
      compare.removeAttribute('aria-disabled');
    } else {
      compare.removeAttribute('href');
      compare.classList.add('disabled');
      compare.setAttribute('aria-disabled', 'true');
    }
  }

  toggle.hidden = false;
  toggle.addEventListener('click', () => { state.on = !state.on; save(); render(); });
  bar.querySelector('[data-clear]').addEventListener('click', () => { state.picks = []; save(); render(); });
  fragment.addEventListener('change', event => {
    const box = event.target.closest('input.pick');
    if (!box) return;
    state.picks = state.picks.filter(pick => pick.request !== box.value);
    if (box.checked) {
      state.picks.push({ request: box.value, label: box.closest('tr').dataset.label });
      while (state.picks.length > 2) state.picks.shift();  // the oldest pick makes room
    }
    save();
    render();
  });
  new MutationObserver(render).observe(fragment, { childList: true });  // live search and paging swap the rows
  render();
}
