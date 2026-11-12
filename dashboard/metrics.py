"""
Every number on the three RCTO Central dashboards, computed from the raw data.

Inputs are plain pandas DataFrames (built from the database by `snapshot.py`):

  complaints  : m, geo, fops, cat, site, ts, city, site_class
  sites       : site, team, av0..av10, ls0..ls10      (monthly availability / load shedding, Jan..Nov)
  ofc26/ofc25 : m, ofc (bool), team, net, sections

No assumptions beyond the definitions below, which were checked 1:1 against the reference dashboard.
"""
import re
import numpy as np
import pandas as pd

ALL_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
CAT_ORDER = ['Coverage', 'Data speed', 'Call quality']
WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
INF = float('inf')
# Grid cells with fewer site-months than this are shown blank ("too few sites"). Every real cell is >= 330.
MIN_CELL_SITES = 30
# Attribute groups (power backup, DG status ...) with fewer sites than this are left out of the attribute charts
MIN_ATTR_SITES = 10


def pearson(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def strength(r):
    """Words under the correlation KPI: |r| < 0.3 weak, < 0.5 moderate, otherwise strong."""
    a = abs(r)
    w = 'weak' if a < 0.3 else 'moderate' if a < 0.5 else 'strong'
    return f"{w} {'positive' if r >= 0 else 'negative'}"


def cut_sites(ofc_cuts, n_months):
    """Site ids named at either end of an OFC-cut section, per month ('7908 --- 42450', '5615-MSC --- 4088')."""
    out = {m: set() for m in range(1, n_months + 1)}
    for m, s in zip(ofc_cuts['m'], ofc_cuts['sections']):
        if m in out:
            out[m].update(int(t) for t in re.findall(r'\d+', str(s)))
    return out


def compute(c, a, o26, o25, cuts_target, cuts_target_source):
    N = int(c['m'].max())                      # months with complaint data (Jan..N)
    months = range(1, N + 1)
    labels = ALL_LABELS[:N]
    AV = [f'av{i}' for i in range(N)]
    LS = [f'ls{i}' for i in range(N)]
    f26 = o26[o26['ofc']]; f25 = o25[o25['ofc']]

    def by_month(df, key=None, val=None):
        return [int(((df['m'] == m) & ((df[key] == val) if key else True)).sum()) for m in months]

    comp = by_month(c)
    cuts = [int((f26['m'] == m).sum()) for m in months]
    cuts25_12 = [int((f25['m'] == m).sum()) for m in range(1, 13)]
    r = pearson(comp, cuts)
    slope, intercept = np.polyfit(cuts, comp, 1)
    team_cuts = {t: [int(((f26['m'] == m) & (f26['team'] == t)).sum()) for m in months] for t in range(1, 7)}
    geo_comp = {t: by_month(c, 'geo', t) for t in range(1, 7)}
    fops_comp = {t: by_month(c, 'fops', t) for t in range(1, 7)}

    link = []
    for lt in ['FTTS', 'Metro', 'LH']:
        s = f26[f26['net'] == lt]
        lc = [int((s['m'] == m).sum()) for m in months]
        link.append({'link': lt, 'r': pearson(comp, lc), 'cuts': int(sum(lc))})

    mix = {k: [int(((c['m'] == m) & (c['cat'] == k)).sum()) for m in months] for k in CAT_ORDER}

    # ---------------- site-month table (site x month) ----------------
    cs = cut_sites(f26, N)
    comp_site = c[c['site'].notna()].groupby(['site', 'm']).size()
    parts = []
    for i, m in enumerate(months):
        t = pd.DataFrame({'site': a['site'].values,
                          'avail': a[AV[i]].round(6).values,   # round(6) strips float noise (1.9999999999999998 == 2.0)
                          'ls': a[LS[i]].round(6).values, 'm': m})
        t['comp'] = [comp_site.get((s, m), 0) for s in t['site']]
        t['cut'] = t['site'].isin(cs[m])
        parts.append(t)
    sm = pd.concat(parts)
    sv = sm.dropna(subset=['avail', 'ls'])          # site-months that have both availability and LS

    def per100(df):
        return round(100 * df['comp'].sum() / len(df), 2)

    site_link = [{'label': l, 'per100': per100(sm[sm['cut'] == f]), 'n': int((sm['cut'] == f).sum())}
                 for f, l in [(False, 'No cut on section'), (True, 'On a cut section')]]
    fiber_site = [{'label': l, 'per100': per100(sv[sv['cut'] == f])}
                  for f, l in [(False, 'No cut on section'), (True, 'On a cut section')]]

    A_EDGES = [(-INF, 95), (95, 98), (98, 99), (99, INF)]
    A_LABELS = ['< 95', '95 – 98', '98 – 99', '≥ 99']
    L_EDGES = [(-INF, 2), (2, 3), (3, 4), (4, 6), (6, INF)]
    L_LABELS = ['< 2 h', '2 – 3 h', '3 – 4 h', '4 – 6 h', '6 h +']

    def bucket(col, edges, labs):
        out = []
        for (lo, hi), lab in zip(edges, labs):
            s = sv[(sv[col] >= lo) & (sv[col] < hi)]
            out.append({'label': lab, 'per100': per100(s), 'sites': int(len(s)), 'complaints': int(s['comp'].sum())})
        return out

    ab = bucket('avail', A_EDGES, A_LABELS)
    lb = bucket('ls', L_EDGES, L_LABELS)
    cells = []
    for lo, hi in A_EDGES:
        row = []
        for l2, h2 in L_EDGES:
            s = sv[(sv['avail'] >= lo) & (sv['avail'] < hi) & (sv['ls'] >= l2) & (sv['ls'] < h2)]
            row.append({'per100': round(100 * s['comp'].sum() / len(s), 1) if len(s) >= MIN_CELL_SITES else None, 'n': int(len(s))})
        cells.append(row)

    # ---------------- team series (two bases: routing team, site region) ----------------
    def team_series(comp_by):
        teams = []
        for t in range(1, 7):
            s = a[a['team'] == t]
            av = [round(float(s[x].mean()), 3) for x in AV]
            ls = [round(float(s[x].mean()), 3) for x in LS]
            n = len(s); cp = comp_by[t]
            teams.append({'team': t, 'complaints': cp, 'avail': av, 'ls': ls, 'cuts': team_cuts[t], 'sites': n,
                          'per100': [round(100 * x / n, 2) for x in cp],
                          'r_avail': pearson(cp, av), 'r_ls': pearson(cp, ls), 'r_cuts': pearson(cp, team_cuts[t])})
        cav = [round(float(a[x].mean()), 3) for x in AV]
        cls_ = [round(float(a[x].mean()), 3) for x in LS]
        central = {'complaints': comp, 'avail': cav, 'ls': cls_, 'cuts': cuts,
                   'r_avail': pearson(comp, cav), 'r_ls': pearson(comp, cls_), 'r_cuts': r}
        return {'teams': teams, 'central': central}

    fops_b = team_series(fops_comp)
    geo_b = team_series(geo_comp)

    # ---------------- FOPs page ----------------
    team_total = [sum(fops_comp[t]) for t in range(1, 7)]
    matrix = [fops_comp[t] for t in range(1, 7)]
    team_mix = [{k: int(((c['fops'] == t) & (c['cat'] == k)).sum()) for k in CAT_ORDER} for t in range(1, 7)]
    city = c.groupby('city').size().sort_values(ascending=False, kind='stable')
    cities = []
    for ct, n in city.head(12).items():
        tt = c[c['city'] == ct]['fops'].value_counts().sort_index()
        cities.append({'city': ct, 'n': int(n), 'team': int(tt.idxmax())})
    classes = [{'label': k, 'n': int(v)} for k, v in c['site_class'].value_counts().head(6).items()]
    wh = np.zeros((7, 24), int)
    for wd, hr in zip(c['ts'].dt.weekday, c['ts'].dt.hour):
        wh[wd, hr] += 1
    pk = np.unravel_index(np.argmax(wh), wh.shape)
    top_m = int(np.argmax(comp)); top_t = int(np.argmax(team_total)) + 1
    fkp = {'total': int(sum(comp)), 'avg_month': int(round(sum(comp) / N)), 'top_month': labels[top_m],
           'top_month_n': comp[top_m], 'top_team': top_t,
           'top_team_share': round(100 * max(team_total) / sum(team_total), 1),
           'peak_slot': f"{WEEKDAYS[pk[0]]} {pk[1]:02d}:00", 'cities': int(c['city'].nunique())}

    # ---------------- network stats, 2025 vs 2026 (needs the 2025 columns of the availability file) ----------------
    A25 = [f'av25_{i}' for i in range(12)]; L25 = [f'ls25_{i}' for i in range(12)]
    r3 = lambda x: round(float(x), 3)
    av25 = [r3(a[x].mean()) for x in A25]; ls25 = [r3(a[x].mean()) for x in L25]
    av26 = fops_b['central']['avail']; ls26 = fops_b['central']['ls']
    cuts25_t = lambda t: [int(((f25['m'] == m) & (f25['team'] == t)).sum()) for m in range(1, 13)]
    net_teams = []
    for t in range(1, 7):
        s_ = a[a['team'] == t]
        ta25 = [r3(s_[x].mean()) for x in A25]; tl25 = [r3(s_[x].mean()) for x in L25]
        tc25 = cuts25_t(t); tt = fops_b['teams'][t - 1]
        net_teams.append({'team': t, 'cuts25': int(sum(tc25)), 'cuts26': int(sum(team_cuts[t])),
                          'r_av25': pearson(ta25, tc25), 'r_av26': pearson(tt['avail'], team_cuts[t]),
                          'r_ls25': pearson(tl25, tc25), 'r_ls26': pearson(tt['ls'], team_cuts[t])})
    net = {'labels': ALL_LABELS, 'avail25': av25, 'avail26': av26, 'ls25': ls25, 'ls26': ls26,
           'cuts25': cuts25_12, 'cuts26': cuts,
           'r': {'avail': {'y2025': pearson(av25, cuts25_12), 'y2026': pearson(av26, cuts)},
                 'ls': {'y2025': pearson(ls25, cuts25_12), 'y2026': pearson(ls26, cuts)}},
           'teams': net_teams}

    # ---------------- site attributes: complaints per 100 site-months ----------------
    site_tot = comp_site.groupby(level=0).sum()
    sa = a.copy(); sa['comp'] = sa['site'].map(site_tot).fillna(0).astype(int)
    def by_attr(col, label_fn):
        out = []
        for lab, g_ in sa.groupby(sa[col].map(label_fn)):
            if len(g_) >= MIN_ATTR_SITES:
                out.append({'label': lab, 'per100': round(100 * g_['comp'].sum() / (len(g_) * N), 2),
                            'sites': int(len(g_)), 'complaints': int(g_['comp'].sum())})
        return sorted(out, key=lambda x: (-x['per100'], x['label']))
    gr = []
    for gname, g_ in sa.groupby('grid'):
        gr.append({'grid': gname, 'per100': round(100 * g_['comp'].sum() / (len(g_) * N), 2), 'sites': int(len(g_)),
                   'complaints': int(g_['comp'].sum()), 'avail': round(float(g_[AV].stack().mean()), 2),
                   'ls': round(float(g_[LS].stack().mean()), 2), 'team': int(g_['team'].iloc[0])})
    gr.sort(key=lambda x: (-x['per100'], x['grid']))
    attr = {'group': by_attr('group', lambda v: v),
            'backup': by_attr('bb', lambda v: v),
            'dg': by_attr('dg', lambda v: v if v else 'Not filled'),
            'chronic': by_attr('chronic', lambda v: 'Chronic below target' if v else 'Other sites'),
            'grids': gr[:10]}

    # month N+1 of the OFC log is still running -> carried in the year-on-year chart as "partial"
    has_next = N < 12 and int((f26['m'] == N + 1).sum()) > 0
    y2026 = [int((f26['m'] == m).sum()) for m in range(1, (N + 1 if has_next else N) + 1)]

    return {
        'complaints': {
            'labels': labels,
            'kpis': {'complaints': int(sum(comp)), 'cuts': int(sum(cuts)), 'r': r, 'strength': strength(r),
                     'peak_complaints': labels[top_m], 'peak_cuts': labels[int(np.argmax(cuts))],
                     'peak_complaints_n': comp[top_m], 'peak_cuts_n': int(max(cuts)),
                     'cuts_py': int(sum(cuts25_12[:N]))},
            'monthly': {'complaints': comp, 'cuts': cuts, 'cuts25': cuts25_12[:N]},
            'target': {'cuts': cuts_target, 'source': cuts_target_source},
            'scatter': {'points': [{'m': labels[i], 'cuts': cuts[i], 'complaints': comp[i]} for i in range(N)],
                        'slope': float(slope), 'intercept': float(intercept)},
            'subs': [{'team': t, 'complaints': geo_comp[t], 'cuts': team_cuts[t], 'r': pearson(geo_comp[t], team_cuts[t]),
                      'total': sum(geo_comp[t]), 'cuts_total': sum(team_cuts[t])} for t in range(1, 7)],
            'link_r': link, 'mix': mix,
            'yoy': {'labels': ALL_LABELS, 'y2025': cuts25_12, 'y2026': y2026, 'partial_month': (N + 1) if has_next else None},
            'site_link': site_link,
        },
        'fops': {'labels': labels, 'teams': [1, 2, 3, 4, 5, 6], 'kpis': fkp, 'team_total': team_total, 'matrix': matrix,
                 'team_mix': team_mix, 'cats': CAT_ORDER, 'monthly_total': comp, 'cities': cities, 'classes': classes,
                 'weekday_hour': wh.tolist(), 'weekdays': WEEKDAYS},
        'scorecard': scorecard(c, a, comp_site, N, labels, comp, cuts, fops_b, f26, cuts_target, f25),
        'drivers': {'labels': labels, 'fops': fops_b, 'geo': geo_b, 'net': net, 'attr': attr, 'avail_buckets': ab, 'ls_buckets': lb,
                    'grid': {'rows': A_LABELS, 'cols': L_LABELS, 'cells': cells}, 'fiber_site': fiber_site,
                    'kpis': {'avail_avg': round(float(np.nanmean(a[AV].values)), 2),
                             'ls_avg': round(float(np.nanmean(a[LS].values)), 2),
                             'avail_avg_py': round(float(np.nanmean(a[A25[:N]].values)), 2),
                             'ls_avg_py': round(float(np.nanmean(a[L25[:N]].values)), 2),
                             'multiple': round(ab[0]['per100'] / ab[3]['per100'], 1),
                             'low_avail': ab[0]['per100'], 'high_avail': ab[3]['per100']}},
    }


# ======================================================================================
# Executive scorecard (extra tab). Every figure is a direct count / mean / median of the
# same raw data as the other tabs - nothing is estimated.
# ======================================================================================
# the only city spelled two ways in the complaints file; merged in the scorecard's city comparison only
CITY_ALIASES = {'DG Khan': 'Dera Ghazi Khan'}


def _pct(a, b):
    return None if not b else round(100 * (a - b) / b, 1)


def scorecard(c, a, comp_site, N, labels, comp, cuts, fops_b, f26, cuts_target, f25):
    AV = [f'av{i}' for i in range(N)]
    LS = [f'ls{i}' for i in range(N)]
    L, P = N - 1, N - 2                       # latest month / previous month (0-based)
    h1 = comp[:6]
    h1_avg = sum(h1) / len(h1) if N >= 6 else None
    cen = fops_b['central']

    # --- headline numbers
    head = {
        'label': labels[L], 'prev_label': labels[P],
        'complaints': comp[L], 'complaints_prev': comp[P], 'complaints_mom': _pct(comp[L], comp[P]),
        'complaints_vs_h1': _pct(comp[L], h1_avg) if h1_avg else None,
        'cuts': cuts[L], 'cuts_prev': cuts[P], 'cuts_target': cuts_target,
        'avail': cen['avail'][L], 'avail_prev': cen['avail'][P], 'ls': cen['ls'][L], 'ls_prev': cen['ls'][P],
        # same month of 2025 (OFC logs and availability file cover 2025; complaints do not)
        'cuts_py': int((f25['m'] == L + 1).sum()), 'avail_py': round(float(a[f'av25_{L}'].mean()), 3), 'ls_py': round(float(a[f'ls25_{L}'].mean()), 3),
        'cuts_ytd': int(sum(cuts)), 'cuts_ytd_py': int((f25['m'] <= N).sum()),
    }

    # --- one row per FOPs team
    rows = []
    for t in fops_b['teams']:
        cp = t['complaints']
        rows.append({'team': t['team'], 'complaints': cp[L], 'mom': _pct(cp[L], cp[P]),
                     'vs_h1': _pct(cp[L], sum(cp[:6]) / 6) if N >= 6 else None,
                     'ytd': int(sum(cp)), 'share': round(100 * sum(cp) / sum(comp), 1),
                     'avail': t['avail'][L], 'avail_prev': t['avail'][P], 'ls': t['ls'][L], 'ls_prev': t['ls'][P],
                     'cuts': t['cuts'][L], 'per100': t['per100'][L], 'sites': t['sites'],
                     'avail_py': round(float(a[a['team'] == t['team']][f'av25_{L}'].mean()), 3),
                     'ls_py': round(float(a[a['team'] == t['team']][f'ls25_{L}'].mean()), 3),
                     'cuts_py': int(((f25['m'] == L + 1) & (f25['team'] == t['team'])).sum())})
    total = {'complaints': comp[L], 'mom': head['complaints_mom'], 'vs_h1': head['complaints_vs_h1'], 'ytd': int(sum(comp)),
             'avail': cen['avail'][L], 'ls': cen['ls'][L], 'cuts': cuts[L],
             'avail_py': head['avail_py'], 'ls_py': head['ls_py'], 'cuts_py': head['cuts_py']}

    # --- city movers, previous month -> latest month (absolute change in complaints)
    cty = c['city'].replace(CITY_ALIASES)
    cp_, cl_ = cty[c['m'] == P + 1].value_counts(), cty[c['m'] == L + 1].value_counts()
    mv = pd.DataFrame({'prev': cp_, 'now': cl_}).fillna(0).astype(int)
    mv['diff'] = mv['now'] - mv['prev']
    mv = mv.rename_axis('city').reset_index()
    up = mv[mv['diff'] > 0].sort_values(['diff', 'city'], ascending=[False, True]).head(5)
    down = mv[mv['diff'] < 0].sort_values(['diff', 'city'], ascending=[True, True]).head(5)
    fmt_mv = lambda d: [{'city': r.city, 'prev': int(r.prev), 'now': int(r.now), 'diff': int(r.diff),
                         'pct': _pct(r.now, r.prev)} for r in d.itertuples()]

    s = a[['site', 'grid', 'team'] + AV + LS].copy()
    s['comp'] = s['site'].map(comp_site.groupby(level=0).sum()).fillna(0).astype(int)
    s['avail_avg'] = s[AV].mean(axis=1, skipna=True)
    s['ls_avg'] = s[LS].mean(axis=1, skipna=True)

    # --- sites with most complaints (sites present in the availability file)
    top = s.sort_values(['comp', 'site'], ascending=[False, True]).head(10)
    city_of = c[c['site'].notna()].assign(city=cty).groupby('site')['city'].agg(lambda x: x.value_counts().sort_index().idxmax())
    sites = [{'site': int(r.site), 'grid': r.grid, 'team': int(r.team), 'city': city_of.get(r.site, ''),
              'complaints': int(r.comp), 'avail': round(float(np.nanmean(getattr(r, 'avail_avg'))), 2),
              'ls': round(float(r.ls_avg), 2),
              'avail_last': None if pd.isna(getattr(r, AV[L])) else round(float(getattr(r, AV[L])), 2),
              'ls_last': None if pd.isna(getattr(r, LS[L])) else round(float(getattr(r, LS[L])), 2)} for r in top.itertuples()]

    # --- fiber restoration: median hours from fiber break to restoration (OFC cuts, Jan..latest)
    f = f26[f26['m'] <= N].copy()
    f['vkey'] = f['vendor'].astype(str).str.strip().str.casefold()
    name = f.groupby('vkey')['vendor'].agg(lambda x: x.astype(str).str.strip().value_counts().sort_index().idxmax())
    def stat(df):
        d = df['dur'].dropna()
        return {'cuts': int(len(df)), 'with_time': int(len(d)), 'median_h': round(float(d.median()) / 60, 1) if len(d) else None}
    g25 = f25[f25['m'] <= N].copy(); g25['vkey'] = g25['vendor'].astype(str).str.strip().str.casefold()
    def py(df):
        s_ = stat(df); return {'cuts_py': s_['cuts'], 'median_h_py': s_['median_h']}
    vend = []
    for k, grp in f.groupby('vkey'):
        if len(grp) >= 100:
            vend.append({'vendor': name[k], **stat(grp), **py(g25[g25['vkey'] == k])})
    vend.sort(key=lambda x: (-x['cuts'], x['vendor']))
    link = [{'link': k, **stat(f[f['net'] == k]), **py(g25[g25['net'] == k])} for k in ['FTTS', 'Metro', 'LH']]
    fiber = {'overall': {**stat(f), **py(g25)}, 'vendors': vend, 'links': link, 'min_cuts': 100}

    return {'head': head, 'rows': rows, 'total': total,
            'movers': {'prev': labels[P], 'now': labels[L], 'up': fmt_mv(up), 'down': fmt_mv(down), 'aliases': CITY_ALIASES},
            'sites': sites, 'fiber': fiber, 'labels': labels}
