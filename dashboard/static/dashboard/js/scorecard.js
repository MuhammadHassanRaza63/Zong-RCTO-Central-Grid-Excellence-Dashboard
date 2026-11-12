/* Executive scorecard: latest month at a glance, city movers, critical sites and fiber restoration.
   Every figure comes from DATA.scorecard (computed from the raw files, nothing typed in by hand). */
VIEWS.scorecard = {
  h1: 'Executive scorecard',
  sub: 'RCTO Central · latest month, hotspots and fiber restoration · January to October 2026',
  body: `
<section class="grid">
  <article class="card c12">
    <div class="head"><div><h2 id="sc-fop-h">FOPs scorecard</h2><p class="cap" id="sc-fop-cap"></p></div></div>
    <div class="tscroll"><table class="tbl" id="sc-fops"></table></div>
  </article>
</section>
<section class="grid">
  <article class="card c6">
    <div class="head"><div><h2 id="sc-mv-h">Biggest movers</h2><p class="cap">Cities with the largest change in complaints</p></div></div>
    <div class="split2">
      <div><h3 class="sub bad">Rising</h3><div class="tscroll"><table class="tbl compact" id="sc-up"></table></div></div>
      <div><h3 class="sub good">Falling</h3><div class="tscroll"><table class="tbl compact" id="sc-down"></table></div></div>
    </div>
    <p class="note" id="sc-mv-note"></p>
  </article>
  <article class="card c6">
    <div class="head"><div><h2>Fiber restoration time</h2><p class="cap" id="sc-fib-cap"></p></div><span class="badge neutral" id="sc-fib-badge"></span></div>
    <div class="tscroll"><table class="tbl compact" id="sc-vendors"></table></div>
    <h3 class="sub">By link type</h3>
    <div class="tscroll"><table class="tbl compact" id="sc-links"></table></div>
  </article>
</section>
<section class="grid">
  <article class="card c12">
    <div class="head"><div><h2>Sites with the most complaints</h2><p class="cap" id="sc-site-cap"></p></div></div>
    <div class="tscroll"><table class="tbl" id="sc-sites"></table></div>
  </article>
</section>`
};

pages.scorecard = function (C) {
  const { D, T, fmt, f1, f2 } = C;
  const H = D.head, L = H.label, Pv = H.prev_label;
  const sgn = (v, d = 1) => (v == null ? '–' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d));
  const pill = (v, goodWhenUp, unit = '%', d = 1) => {
    if (v == null) return '<span class="dl">–</span>';
    const up = v > 0, flat = v === 0;
    const good = flat ? null : (up === goodWhenUp);
    return `<span class="dl ${flat ? '' : good ? 'good' : 'bad'}">${flat ? '' : up ? '▲' : '▼'} ${sgn(v, d).replace(/^[+−]/, '')}${unit}</span>`;
  };
  const pc = (a, b) => (b ? +(100 * (a - b) / b).toFixed(1) : null);
  const hdr = cols => '<thead><tr>' + cols.map(c => `<th class="${c[1] || ''}">${c[0]}</th>`).join('') + '</tr></thead>';
  const tag = t => `<span class="tm" style="--tc:${T.teams[t - 1]}">C${t}</span>`;

  /* hero + takeaways */
  C.kpis([
    { v: fmt(H.complaints), l: `Complaints in ${L} · ${sgn(H.complaints_mom)}% vs ${Pv}` },
    { v: fmt(H.cuts), l: `OFC cuts in ${L} · ${sgn(pc(H.cuts, H.cuts_py))}% vs ${L} 2025 (${fmt(H.cuts_py)})` },
    { v: f2(H.avail), unit: '%', l: `Cell availability in ${L} · ${sgn(H.avail - H.avail_py, 2)} pp vs ${L} 2025` },
  ]);
  const top = D.rows.slice().sort((a, b) => b.per100 - a.per100)[0];
  const HAS_T = H.cuts_target != null;   // CUTS_TARGET = None in settings.py hides the target
  const gap = HAS_T ? H.cuts_target - H.cuts : 0;
  C.story([
    { c: T.complaints, t: `${L} complaints are <b>${sgn(H.complaints_vs_h1)}%</b> against the January–June average` },
    { c: T.cuts, t: `OFC cuts January–${L}: <b>${fmt(H.cuts_ytd)}</b> · <b>${sgn(pc(H.cuts_ytd, H.cuts_ytd_py))}%</b> vs the same months of 2025` },
    ...(HAS_T ? [{ c: T.cuts, t: `${L} OFC cuts: ${gap >= 0 ? `<b>${fmt(gap)}</b> under` : `<b>${fmt(-gap)}</b> over`} the ${fmt(H.cuts_target)} target` }] : []),
    { c: T.teams[top.team - 1], t: `Highest complaint rate in ${L}: <b>C${top.team}</b> · ${f2(top.per100)} per 100 sites` },
    { c: T.avail, t: `Median fiber restoration: <b>${f1(D.fiber.overall.median_h)} h</b> · ${f1(D.fiber.overall.median_h_py)} h in the same months of 2025` },
  ]);

  /* FOPs scorecard */
  document.getElementById('sc-fop-h').textContent = `FOPs scorecard · ${L} 2026`;
  document.getElementById('sc-fop-cap').textContent =
    `Complaints are routed to the team; availability, load shedding, cuts and sites belong to the matching site region · change vs ${Pv} and vs ${L} 2025 (no 2025 complaints file is loaded)`;
  const rows = D.rows.map(r => `<tr>
      <td>${tag(r.team)}</td><td class="num">${fmt(r.complaints)}</td><td class="num">${pill(r.mom, false)}</td>
      <td class="num">${pill(r.vs_h1, false)}</td><td class="num">${fmt(r.ytd)}</td><td class="num">${f1(r.share)}%</td>
      <td class="num">${f2(r.per100)}</td>
      <td class="num">${f2(r.avail)}%</td><td class="num">${pill(+(r.avail - r.avail_prev).toFixed(2), true, ' pp', 2)}</td><td class="num">${pill(+(r.avail - r.avail_py).toFixed(2), true, ' pp', 2)}</td>
      <td class="num">${f2(r.ls)} h</td><td class="num">${pill(+(r.ls - r.ls_prev).toFixed(2), false, ' h', 2)}</td><td class="num">${pill(+(r.ls - r.ls_py).toFixed(2), false, ' h', 2)}</td>
      <td class="num">${fmt(r.cuts)}</td><td class="num">${fmt(r.cuts_py)}</td><td class="num">${pill(pc(r.cuts, r.cuts_py), false)}</td></tr>`).join('');
  const t = D.total;
  document.getElementById('sc-fops').innerHTML = hdr([
    ['FOPs team'], [`Complaints ${L}`, 'num'], [`vs ${Pv}`, 'num'], ['vs Jan–Jun avg', 'num'], ['Jan–' + L, 'num'], ['Share', 'num'],
    ['Per 100 sites', 'num'], [`Availability ${L}`, 'num'], [`vs ${Pv}`, 'num'], [`vs ${L} 2025`, 'num'], [`Load shedding ${L}`, 'num'], [`vs ${Pv}`, 'num'], [`vs ${L} 2025`, 'num'],
    [`OFC cuts ${L}`, 'num'], [`${L} 2025`, 'num'], ['YoY', 'num'],
  ]) + `<tbody>${rows}</tbody><tfoot><tr><td>Central</td><td class="num">${fmt(t.complaints)}</td><td class="num">${pill(t.mom, false)}</td>
      <td class="num">${pill(t.vs_h1, false)}</td><td class="num">${fmt(t.ytd)}</td><td class="num">100%</td><td class="num"></td>
      <td class="num">${f2(t.avail)}%</td><td class="num">${pill(+(H.avail - H.avail_prev).toFixed(2), true, ' pp', 2)}</td><td class="num">${pill(+(H.avail - H.avail_py).toFixed(2), true, ' pp', 2)}</td>
      <td class="num">${f2(t.ls)} h</td><td class="num">${pill(+(H.ls - H.ls_prev).toFixed(2), false, ' h', 2)}</td><td class="num">${pill(+(H.ls - H.ls_py).toFixed(2), false, ' h', 2)}</td>
      <td class="num">${fmt(t.cuts)}</td><td class="num">${fmt(t.cuts_py)}</td><td class="num">${pill(pc(t.cuts, t.cuts_py), false)}</td></tr></tfoot>`;

  /* movers */
  document.getElementById('sc-mv-h').textContent = `Biggest movers · ${D.movers.prev} → ${D.movers.now}`;
  const mv = list => hdr([['City'], [D.movers.prev, 'num'], [D.movers.now, 'num'], ['Change', 'num']]) + '<tbody>' +
    (list.length ? list.map(m => `<tr><td>${m.city}</td><td class="num">${fmt(m.prev)}</td><td class="num">${fmt(m.now)}</td>
      <td class="num"><b>${sgn(m.diff, 0)}</b>${m.pct == null ? '' : ` <span class="mut">(${sgn(m.pct, 0)}%)</span>`}</td></tr>`).join('')
      : '<tr><td colspan="4" class="mut">None</td></tr>') + '</tbody>';
  document.getElementById('sc-up').innerHTML = mv(D.movers.up);
  document.getElementById('sc-down').innerHTML = mv(D.movers.down);
  const al = Object.entries(D.movers.aliases || {}).map(([a, b]) => `${a} is counted with ${b}`).join('; ');
  document.getElementById('sc-mv-note').textContent = al ? `Note: ${al} (same city, spelled two ways in the complaints file).` : '';

  /* fiber restoration */
  const F = D.fiber, maxH = Math.max(...F.vendors.map(v => v.median_h), ...F.links.map(v => v.median_h));
  document.getElementById('sc-fib-cap').textContent =
    `Median hours from fiber break to restoration · OFC cuts January–${L} 2026 against the same months of 2025 · vendors with ${F.min_cuts}+ cuts in 2026`;
  document.getElementById('sc-fib-badge').textContent = `Overall ${f1(F.overall.median_h)} h · 2025: ${f1(F.overall.median_h_py)} h`;
  const bar = h => `<span class="ib"><i style="width:${(100 * h / maxH).toFixed(1)}%"></i></span>`;
  const frow = (name, v) => `<tr><td>${name}</td><td class="num">${fmt(v.cuts)}</td><td class="num"><b>${f1(v.median_h)} h</b></td><td class="num mut">${v.median_h_py == null ? '–' : f1(v.median_h_py) + ' h'}</td><td class="num">${v.median_h_py ? pill(+(v.median_h - v.median_h_py).toFixed(1), false, ' h', 1) : '–'}</td><td class="barcell">${bar(v.median_h)}</td></tr>`;
  document.getElementById('sc-vendors').innerHTML = hdr([['Vendor'], ['OFC cuts', 'num'], ['Median 2026', 'num'], ['Median 2025', 'num'], ['Change', 'num'], ['']]) + '<tbody>' + F.vendors.map(v => frow(v.vendor, v)).join('') + '</tbody>';
  document.getElementById('sc-links').innerHTML = hdr([['Link type'], ['OFC cuts', 'num'], ['Median 2026', 'num'], ['Median 2025', 'num'], ['Change', 'num'], ['']]) + '<tbody>' + F.links.map(v => frow(v.link, v)).join('') + '</tbody>';

  /* sites */
  document.getElementById('sc-site-cap').textContent =
    `Top 10 sites by complaints, January–${L} · availability and load shedding are the site's average over the same months`;
  document.getElementById('sc-sites').innerHTML = hdr([['Site'], ['Grid'], ['FOPs'], ['City'], ['Complaints', 'num'], ['Avg availability', 'num'], ['Avg load shedding', 'num'], [`Availability ${L}`, 'num'], [`Load shedding ${L}`, 'num']]) +
    '<tbody>' + D.sites.map(s => `<tr><td><b>${s.site}</b></td><td>${s.grid}</td><td>${tag(s.team)}</td><td>${s.city}</td><td class="num"><b>${fmt(s.complaints)}</b></td>
      <td class="num">${f2(s.avail)}%</td><td class="num">${f2(s.ls)} h</td>
      <td class="num">${s.avail_last == null ? '–' : f2(s.avail_last) + '%'}</td><td class="num">${s.ls_last == null ? '–' : f2(s.ls_last) + ' h'}</td></tr>`).join('') + '</tbody>';

  [['#sc-fops', '2026']].forEach(() => {});
};
