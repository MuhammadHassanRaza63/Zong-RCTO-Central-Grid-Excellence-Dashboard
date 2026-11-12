"""Everything on the landing page that shows a number is taken from the computed snapshot - nothing is typed in by hand."""
from django.contrib.staticfiles import finders
from django.db.models import Count
from .models import Complaint, OfcBreak, SiteAvailability, Snapshot

MONTHS_FULL = {'Jan': 'January', 'Feb': 'February', 'Mar': 'March', 'Apr': 'April', 'May': 'May', 'Jun': 'June',
               'Jul': 'July', 'Aug': 'August', 'Sep': 'September', 'Oct': 'October', 'Nov': 'November', 'Dec': 'December'}


def _fmt(n):
    return f'{n:,}'


def _sgn(v, d=1):
    return ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v):.{d}f}'


def _yoy(now, before, unit='%', d=1, up_is_good=True):
    """'+12.3% vs same months 2025' pill text + good/bad class (None when 2025 has no value)."""
    if not before:
        return None, ''
    diff = (100 * (now - before) / before) if unit == '%' else (now - before)
    txt = _sgn(diff, d) + ('%' if unit == '%' else f' {unit}')
    return txt, ('' if abs(diff) < 10 ** -d else 'good' if (diff > 0) == up_is_good else 'bad')


def _r(v):
    return ('+' if v >= 0 else '−') + f'{abs(v):.2f}'


def _spark(comp, cuts, w=520, h=150):
    """bars = complaints, line = OFC cuts (own scale); returns ready-to-draw SVG numbers"""
    n = len(comp); pad = 6; slot = (w - 2 * pad) / n; bw = slot * 0.56
    top_c, top_k = max(comp) * 1.12, max(cuts) * 1.12
    bars = [{'x': round(pad + i * slot + (slot - bw) / 2, 1), 'y': round(h - 22 - (v / top_c) * (h - 34), 1),
             'h': round((v / top_c) * (h - 34), 1), 'w': round(bw, 1), 'last': i == n - 1} for i, v in enumerate(comp)]
    pts = [(pad + i * slot + slot / 2, h - 22 - (v / top_k) * (h - 34)) for i, v in enumerate(cuts)]
    return {'w': w, 'h': h, 'bars': bars, 'line': ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts),
            'dots': [{'x': round(x, 1), 'y': round(y, 1)} for x, y in pts],
            'ticks': [{'x': round(pad + i * slot + slot / 2, 1), 'y': h - 4} for i in range(n)]}


def _grid_module():
    """Live numbers for the Grid Excellence module card; the landing page must never break if the Grid data is missing."""
    try:
        from grid_report.views import _load
        D = _load()
        return {'score': f"{D['summary'][0]['now']:.1f}", 'grids': int(D['summary'][0]['grids']), 'period': D['meta']['period']}
    except Exception:
        return None


def build():
    snap = Snapshot.objects.filter(key='dashboard').first()
    if snap is None:
        return None
    P = snap.payload
    C, D, S = P['complaints'], P['drivers'], P['scorecard']
    H = S['head']; labels = C['labels']
    chronic = {x['label']: x['per100'] for x in D['attr']['chronic']}
    lo, hi = D['kpis']['low_avail'], D['kpis']['high_avail']
    fc = D['fops']['central']
    span = f"{MONTHS_FULL[labels[0]]}–{MONTHS_FULL[labels[-1]]} 2026"
    comp_mom = H['complaints_mom']
    nm = f"{labels[0]}–{labels[-1]}"
    cy, cyc = _yoy(C['kpis']['cuts'], C['kpis']['cuts_py'], up_is_good=False)
    ay, ayc = _yoy(D['kpis']['avail_avg'], D['kpis']['avail_avg_py'], 'pp', 2)
    ly, lyc = _yoy(D['kpis']['ls_avg'], D['kpis']['ls_avg_py'], 'h', 2, up_is_good=False)
    hc, hcc = _yoy(H['cuts'], H['cuts_py'], up_is_good=False)
    ha, hac = _yoy(H['avail'], H['avail_py'], 'pp', 2)
    hl, hlc = _yoy(H['ls'], H['ls_py'], 'h', 2, up_is_good=False)
    py = S['fiber']['overall']['median_h_py']
    ctx = {
        'period': span, 'last': H['label'], 'prev': H['prev_label'],
        'refreshed': snap.computed_at,
        'spark': _spark(C['monthly']['complaints'], C['monthly']['cuts']),
        'spark_labels': labels,
        'hero': {
            'complaints': _fmt(H['complaints']), 'mom': _sgn(comp_mom), 'mom_good': comp_mom <= 0,
            'cuts': _fmt(H['cuts']), 'cuts_y': hc, 'cuts_yc': hcc,
            'avail': f"{H['avail']:.2f}", 'avail_y': ha, 'avail_yc': hac,
            'ls': f"{H['ls']:.1f}", 'ls_y': hl, 'ls_yc': hlc,
        },
        'stats': [
            {'v': _fmt(C['kpis']['complaints']), 'u': '', 'l': f'Customer complaints, {span}', 'c': 'var(--m-complaints)'},
            {'v': _fmt(C['kpis']['cuts']), 'u': '', 'l': f'OFC cuts, {span}', 'c': 'var(--m-cuts)', 'd': cy and f'{cy} vs {nm} 2025', 'dc': cyc},
            {'v': f"{D['kpis']['avail_avg']:.2f}", 'u': '%', 'l': 'Average cell availability', 'c': 'var(--m-avail)', 'd': ay and f'{ay} vs {nm} 2025', 'dc': ayc},
            {'v': f"{D['kpis']['ls_avg']:.1f}", 'u': 'h', 'l': 'Average load shedding per site, per day', 'c': 'var(--m-ls)', 'd': ly and f'{ly} vs {nm} 2025', 'dc': lyc},
        ],
        'insights': [
            {'c': 'var(--m-complaints)', 'tag': 'Sites', 'num': f"{D['kpis']['multiple']:.1f}", 'u': '×',
             't': 'Weakest sites, most complaints',
             'p': f'Site-months under 95% availability generate {D["kpis"]["multiple"]:.1f} times the complaints of site-months at 99% or better ({lo:.1f} vs {hi:.1f} per 100).'},
            {'c': 'var(--m-avail)', 'tag': 'Network', 'num': _r(fc['r_avail']), 'u': '',
             't': 'Availability moves with complaints',
             'p': 'Month on month, lower Central cell availability goes with more complaints (correlation r, Pearson).'},
            {'c': 'var(--m-ls)', 'tag': 'Power', 'num': _r(fc['r_ls']), 'u': '',
             't': 'Load shedding moves with complaints',
             'p': 'Months with more load shedding hours per site bring more complaints (correlation r, Pearson).'},
            {'c': 'var(--m-cuts)', 'tag': 'Fiber', 'num': _r(fc['r_cuts']), 'u': '',
             't': 'Fiber cuts alone: a weak link',
             'p': f'OFC cuts and complaints rise and fall together only weakly across the {len(labels)} months; the network measures explain more.'},
            {'c': 'var(--m-complaints)', 'tag': 'Chronic', 'num': f"{chronic['Chronic below target'] / chronic['Other sites']:.1f}", 'u': '×',
             't': 'Chronic below-target sites',
             'p': f'{chronic["Chronic below target"]:.1f} complaints per 100 site-months at chronic below-target sites against {chronic["Other sites"]:.1f} at all other sites.'},
            {'c': 'var(--m-cuts)', 'tag': 'Restoration', 'num': f"{S['fiber']['overall']['median_h']:.1f}", 'u': 'h',
             't': 'Median fiber restoration',
             'p': f'Median time from fiber break to restoration across {_fmt(S["fiber"]["overall"]["with_time"])} OFC cuts, against {py:.1f} h in the same months of 2025.'},
        ],
        'sources': [
            {'n': 'Customer complaints', 'd': 'CPM · NOMC-E2E-REGIONS, routed to FOPs C1–C6', 'rows': _fmt(Complaint.objects.count())},
            {'n': 'OFC break logs, 2026', 'd': 'Region, link type, sections, restoration time', 'rows': _fmt(OfcBreak.objects.filter(year=2026).count())},
            {'n': 'OFC break logs, 2025', 'd': 'Year-on-year comparison', 'rows': _fmt(OfcBreak.objects.filter(year=2025).count())},
            {'n': 'Network availability & load shedding', 'd': 'Per site, monthly, January 2025 – October 2026', 'rows': _fmt(SiteAvailability.objects.count()) + ' sites'},
        ],
        'dashboards': [
            {'k': 'complaints', 'n': '01', 'c': 'var(--m-complaints)', 'icon': 'bars', 't': 'Complaints & Fiber Cuts',
             'p': 'Every complaint against OFC cuts, month on month.',
             'li': ['Monthly correlation and trend line', 'By site region and by link type', 'Sites on a cut section vs the rest', '2025 vs 2026 cuts']},
            {'k': 'fops', 'n': '02', 'c': 'var(--m-cuts)', 'icon': 'team', 't': 'FOPs C1 to C6',
             'p': 'The routing-team view of RCTO Central.',
             'li': ['Share and trend by FOPs team', 'Team × month heat map', 'Top cities and complaint types', 'When complaints arrive']},
            {'k': 'drivers', 'n': '03', 'c': 'var(--m-avail)', 'icon': 'signal', 't': 'Availability · LS · Fiber',
             'p': 'Complaints mapped to cell availability, load shedding and cuts.',
             'li': ['Four measures, same months, per team', 'Correlations and site buckets', '2025 vs 2026 network stats', 'Group, backup, DG, chronic sites, grids']},
            {'k': 'scorecard', 'n': '04', 'c': 'var(--m-ls)', 'icon': 'card', 't': 'Executive scorecard',
             'p': 'The latest month at a glance.',
             'li': ['FOPs scorecard vs last month', 'Biggest city movers', 'Fiber restoration by vendor', 'Sites with most complaints']},
        ],
    }
    g = _grid_module()
    ctx['modules'] = [
        {'k': 'rcto', 'n': '01', 'c': 'var(--m-complaints)', 'icon': 'bars', 'img': 'site/img/card-complaints.svg', 'url': 'dashboards',
         't': 'RCTO Central performance', 'p': 'What drives customer complaints across FOPs C1–C6.',
         'li': ['Complaints and OFC (fiber) cuts', 'FOPs C1–C6 team view', 'Availability, load shedding and fiber drivers', 'Executive scorecard'],
         'meta': f'4 dashboards · {span}'},
        {'k': 'grid', 'n': '02', 'c': 'var(--m-avail)', 'icon': 'grid', 'img': 'site/img/card-drivers.svg', 'url': 'grid_report:home',
         't': 'Grid Excellence', 'p': 'Score, KPIs and cross-metric analysis for every grid.',
         'li': ['Grid score, rank and trend', '10 network KPIs per grid', 'Correlations and critical pairs', 'Grid action list'],
         'meta': (f"{g['grids']} grids · {g['period']} · score {g['score']}%" if g else '2 dashboards')},
    ]
    logo = finders.find('site/brand/company-logo.svg') and 'site/brand/company-logo.svg' or \
        (finders.find('site/brand/company-logo.png') and 'site/brand/company-logo.png')
    ctx['company_logo'] = logo or None
    for d in ctx['dashboards']:   # real photo wins: drop card-<key>.jpg/.webp/.png into static/site/photos/
        photo = next((f'site/photos/card-{d["k"]}.{e}' for e in ('jpg', 'jpeg', 'webp', 'png') if finders.find(f'site/photos/card-{d["k"]}.{e}')), None)
        d['img'] = photo or f'site/img/card-{d["k"]}.svg'
    ctx['hero_photo'] = next((f'site/photos/hero.{e}' for e in ('jpg', 'jpeg', 'webp', 'png') if finders.find(f'site/photos/hero.{e}')), None)
    return ctx


def portal():
    """Context for the single landing page: one card per module, each with a few live numbers. Never raises."""
    rcto = None
    try:
        c = build()
        if c:
            h = c['hero']
            rcto = {'period': c['period'], 'last': c['last'],
                    'm': [{'v': h['complaints'], 'l': 'Complaints'}, {'v': h['cuts'], 'l': 'OFC cuts'}, {'v': h['avail'] + '%', 'l': 'Availability'}]}
    except Exception:
        rcto = None
    grid = None
    try:
        from grid_report.views import _load
        D = _load(); S, C, M = D['summary'][0], D['regions'][0], D['meta']
        grid = {'period': M['period'], 'now': M['now'],
                'm': [{'v': f"{S['now']:.1f}%", 'l': 'Grid score'}, {'v': str(int(S['grids'])), 'l': 'Grids'}, {'v': f"{C['avl']:.2f}%", 'l': 'Availability'}]}
    except Exception:
        grid = None
    return {'modules': [
        {'k': 'rcto', 'n': '01', 'c': 'var(--m-complaints)', 'icon': 'bars', 'img': 'site/img/card-complaints.svg', 'url': 'dashboards',
         't': 'RCTO Central', 'p': 'What drives customer complaints: fiber cuts, cell availability and load shedding for FOPs C1–C6.',
         'li': ['4 dashboards', 'FOPs C1–C6 view', 'Executive scorecard'],
         'tag': rcto and f"{rcto['last']} 2026", 'm': rcto and rcto['m']},
        {'k': 'grid', 'n': '02', 'c': 'var(--m-avail)', 'icon': 'grid', 'img': 'site/img/card-drivers.svg', 'url': 'grid_report:report',
         't': 'Grid Excellence', 'p': 'Score, ranking and KPIs for every grid, with a cross-metric analysis lab.',
         'li': ['2 dashboards', 'Grid ranking and drill-down', 'Analysis lab'],
         'tag': grid and grid['period'], 'm': grid and grid['m']},
    ]}
