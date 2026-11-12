/* Router: one dashboard per hash (#complaints, #fops, #drivers, #scorecard). */
const MONTHS_FULL = { Jan: 'January', Feb: 'February', Mar: 'March', Apr: 'April', May: 'May', Jun: 'June', Jul: 'July',
  Aug: 'August', Sep: 'September', Oct: 'October', Nov: 'November', Dec: 'December' };

function show() {
  const k = (location.hash || '#complaints').slice(1);
  const key = VIEWS[k] ? k : 'complaints';
  const v = VIEWS[key];
  const lab = DATA[key].labels;
  const span = `${MONTHS_FULL[lab[0]]} to ${MONTHS_FULL[lab[lab.length - 1]]} 2026`;
  document.getElementById('h1').innerHTML = v.h1;
  document.getElementById('sub').innerHTML = v.sub.replace('January to October 2026', span);
  document.getElementById('view').innerHTML = v.body;
  document.querySelectorAll('#tabs a').forEach(a => { const on = a.dataset.k === key; a.classList.toggle('on', on); a.setAttribute('aria-current', on ? 'page' : 'false'); });
  document.title = v.h1.replace(/&amp;/g, '&') + ' · RCTO Central Performance Hub';
  const C = initCharts({ theme: THEME, data: DATA[key] });
  pages[key](C);
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', show);
show();
