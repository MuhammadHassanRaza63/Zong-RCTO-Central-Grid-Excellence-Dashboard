"""Build data/report.json from the monthly "Network KPI Report - Grid Excellence" workbook.

Every number on the dashboard comes from this workbook - nothing is hard coded or generated.

Usage (from the folder that holds manage.py):
    python grid_report/tools/build_report_data.py "Network_KPI_Report.xlsb" grid_report/data/report.json
    python grid_report/tools/build_report_data.py "Network_KPI_Report.xlsx" grid_report/data/report.json

or simply:
    python manage.py import_workbook "Network_KPI_Report.xlsb"

.xlsb is read directly (pyxlsb); .xlsx is read with openpyxl. Needs: pandas, openpyxl, pyxlsb.

The script checks the header of every column it reads. If the workbook layout changes in a future
month it stops with a clear message instead of silently showing wrong numbers.
"""
import datetime as dt
import json
import math
import sys
from pathlib import Path

import pandas as pd
from openpyxl.utils import column_index_from_string as ci
from openpyxl.utils import get_column_letter as L


# --------------------------------------------------------------------------- reading
class Book:
    """Uniform access to .xlsx / .xlsb sheets as lists of row tuples (cached cell values)."""

    def __init__(self, path):
        self.path = str(path)
        self.cache = {}
        self.xlsb = self.path.lower().endswith(".xlsb")
        if self.xlsb:
            from pyxlsb import open_workbook
            self.wb = open_workbook(self.path)
        else:
            import openpyxl
            self.wb = openpyxl.load_workbook(self.path, read_only=True, data_only=True)

    def rows(self, name):
        if name not in self.cache:
            if self.xlsb:
                with self.wb.get_sheet(name) as sh:
                    out = []
                    for r in sh.rows():
                        out.append(tuple(c.v for c in r))
            else:
                out = list(self.wb[name].iter_rows(values_only=True))
            self.cache[name] = out
        return self.cache[name]

    def frame(self, name):
        r = self.rows(name)
        hdr = [str(h).strip() if h is not None else "" for h in r[0]]
        return pd.DataFrame([list(x) + [None] * (len(hdr) - len(x)) for x in r[1:]], columns=hdr)


def clean(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, str) and v.startswith("#"):  # Excel error such as #NAME?
        return None
    return v


def to_date(v):
    """Header cell -> date (handles real dates and Excel serial numbers from .xlsb)."""
    if isinstance(v, dt.datetime):
        return v
    if isinstance(v, (int, float)) and 30000 < v < 80000:
        return dt.datetime(1899, 12, 30) + dt.timedelta(days=float(v))
    return None


def to_month(v):
    d = to_date(v)
    return d.month if d else None


MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def build(src, out):
    bk = Book(src)
    rows = bk.rows("Grid Performance")

    def g(r, c):
        i = ci(c) - 1
        return clean(r[i]) if i < len(r) else None

    def hdr(c):
        i = ci(c) - 1
        return " ".join(str(rows[k][i]) for k in (1, 2) if i < len(rows[k]) and rows[k][i] is not None).lower()

    # field -> (column letter, text that must appear in the header above that column)
    F = {
        "name": ("B", ""), "rank": ("C", "ranking"), "score": ("D", "score"), "sites": ("E", "total sites"),
        "plat": ("F", "platinum"), "pgs": ("G", "pgs"), "sb": ("H", "sb"), "rollout": ("L", "rollout"),
        "liion": ("M", "li-ion"), "dgops": ("N", "dg ops"),
        "avl": ("O", "avl"), "avl_p": ("P", "platinum"), "avl_g": ("Q", "pgs"), "avl_s": ("R", "sb"), "avl_dg": ("S", "dg"),
        "chronic": ("T", "chronic"), "avl_ytd": ("U", "ytd"),
        "ls": ("AA", "ls mtd"), "ls_ytd": ("AB", "ls ytd"),
        "voice": ("AD", "voice mtd"), "voice_ytd": ("AE", "voice ytd"), "voice_loss": ("AG", "voice loss"),
        "data": ("AH", "data mtd"), "data_ytd": ("AI", "data ytd"), "data_loss": ("AK", "data loss"),
        "rev": ("AL", "rev"), "rev_ytd": ("AM", "rev ytd"), "rev_py": ("AN", "ytd-25"), "yoy": ("AO", "yoy"), "rev_loss": ("AQ", "revenue loss"),
        "fuel": ("AR", "fuel mtd"), "fuel_ytd": ("AS", "fuel ytd"), "underu": ("AT", "underutil"),
        "highfuel": ("AU", "high fuel"), "notop": ("AV", "not operational"),
        "units": ("AW", "units mtd"), "units_ytd": ("AX", "units ytd"), "chron_exc": ("AY", "chronic excessive"),
        "k_phase": ("AZ", "2 phase"), "k_fluct": ("BA", "fluctuation"), "k_down": ("BB", "down cells"),
        "k_zero": ("BC", "zero traffic"), "k_compl": ("BD", "complaints"), "k_vswr": ("BE", "vswr"),
        "k_temp": ("BF", "high temp"), "k_tprime": ("BG", "t prime"), "k_link": ("BH", "hi cap link"),
        "k_rsl": ("BI", "rsl"), "k_crit": ("BJ", "critical alarm"),
        "s_plat": ("BT", ""), "s_pgs": ("BW", ""), "s_sb": ("BZ", ""), "s_dg": ("CC", ""),
        "s_avl": ("CF", "avl score"), "s_fuel": ("CH", "fuel score"), "s_underu": ("CI", "underu"),
        "s_units": ("CK", "units score"), "s_phase": ("CL", "phase missing"), "s_fluct": ("CM", "fluctuation"),
        "s_down": ("CN", "down cells"), "s_zero": ("CO", "zero traffic"), "s_compl": ("CP", "complaints"),
        "s_vswr": ("CQ", "vswr"), "s_temp": ("CR", "high temp"), "s_link": ("CS", "hi cap link"),
        "s_rsl": ("CT", "rsl"), "s_crit": ("CU", "critical alarm"), "s_basics": ("CV", "3 basics"),
    }
    bad = [f"{k}: column {c} reads '{hdr(c).strip()}' (expected '{want}')" for k, (c, want) in F.items() if want and want not in hdr(c)]
    if bad:
        sys.exit("The 'Grid Performance' layout differs from what this script expects:\n  " + "\n  ".join(bad)
                 + "\nUpdate the column letters in build_report_data.py (dict F) and run again.")

    # trend blocks are located by their title in row 1 and the month dates in row 2
    def trend(title):
        start = next((i for i, v in enumerate(rows[1]) if isinstance(v, str) and v.strip().lower() == title), None)
        if start is None:
            sys.exit(f"Trend block '{title}' not found in Grid Performance row 2")
        end = start
        while end + 1 < len(rows[2]) and to_month(rows[2][end + 1]) is not None and to_month(rows[2][end + 1]) > to_month(rows[2][end]):
            end += 1
        return start, end

    blocks = {"t_avl": "avail% trend", "t_ls": "ls trend", "t_voice": "voice trend", "t_data": "data trend", "t_rev": "revenue trend"}
    # first occurrence of each title = Central / 47-grid table (a second copy for 'Central-A' sits further right)
    pos = {}
    for k, title in blocks.items():
        s, e = trend(title)
        pos[k] = (s, e)
    n_months = max(e - s + 1 for s, e in pos.values())
    first_cell = rows[2][min(s for s, _ in pos.values())]
    first_month, year = to_month(first_cell), to_date(first_cell).year
    months = MON[first_month - 1:first_month - 1 + n_months]

    def rec(r):
        d = {k: g(r, c) for k, (c, _) in F.items()}
        for k, (s, e) in pos.items():
            vals = [clean(r[i]) if i < len(r) else None for i in range(s, e + 1)]
            vals += [None] * (n_months - len(vals))  # shorter series (e.g. revenue lags a month) -> null
            d[k] = vals
        return d

    region_rows = [rec(rows[i]) for i in range(5, 12)]
    gstart = next(i for i, r in enumerate(rows) if i > 11 and r[1] and str(r[1]).startswith("C") and str(r[1])[1:].isdigit())
    gend = gstart
    while gend < len(rows) and rows[gend][1] and str(rows[gend][1])[1:].isdigit():
        gend += 1
    grids = [rec(rows[i]) for i in range(gstart, gend)]
    for d in grids:
        d["region"] = "Central-" + d["name"][1]
    dstart = gend + 1
    districts = []
    for i in range(dstart, len(rows)):
        if rows[i][1] and rows[i][4] is not None:
            districts.append({"name": rows[i][1], "sites": rows[i][4]})

    # Executive summary (period labels come from the sheet itself)
    ex = bk.rows("Ex Summ")
    title = str(ex[0][0] or "")
    hdr_ex = [str(x or "") for x in ex[2]]
    last_lbl = hdr_ex[1].split()[0]
    now_lbl = hdr_ex[2].split()[0]
    summ = []
    for r in ex[3:]:
        if not (isinstance(r[0], str) and r[0].strip().startswith("Central")):
            continue  # skip header / note rows such as ">90% Grids: 41/47"
        summ.append(dict(region=r[0], last=r[1], now=r[2], rank=r[3], grids=r[4], improved=r[5] or 0,
                         sustained=r[6] or 0, declined=r[7] or 0, low=r[8] or 0, remark=r[9]))

    gs = bk.rows("Grid Scoring")
    status = {}
    for r in gs[3:]:
        if r[3] and str(r[3])[0] == "C" and str(r[3])[1:].isdigit():
            status[r[3]] = dict(last=r[4], now=r[5], move=r[6], bin=r[1])
    for d in grids:
        s = status[d["name"]]
        d["last"], d["move"], d["bin"] = s["last"], s["move"], s["bin"]
        assert abs(s["now"] - d["score"]) < 1e-6, (d["name"], s["now"], d["score"])

    # Tracker (one row per site) -> classification mix, cities, worst sites per grid
    tr_rows = bk.rows("Tracker")
    th = [str(h).strip() if h is not None else "" for h in tr_rows[3]]
    ncol = len(th)
    tr = pd.DataFrame([list(x) + [None] * (ncol - len(x)) for x in tr_rows[4:] if x and x[0] is not None], columns=th)
    chronic_i = th.index("Chronic Below Base")
    now_avl_col = tr.iloc[:, chronic_i - 1]  # current-month site availability sits just before this column
    tr["now_avl"] = pd.to_numeric(now_avl_col, errors="coerce")
    tr["Chronic"] = tr.iloc[:, chronic_i]
    cls_order = ["Platinum +", "Platinum", "Gold", "Silver", "Bronze", "Strategic", "LRS"]
    tg = {}
    for gname, df in tr.groupby("Grid"):
        mix = {c: int((df["Classification"] == c).sum()) for c in cls_order}
        low = df.nsmallest(5, "now_avl")[["Site", "Classification", "City", "now_avl"]]
        tg[gname] = dict(
            mix=mix, cities=df["City"].value_counts().head(3).to_dict(),
            worst=[dict(site=int(a), cls=b, city=c, avl=round(float(v), 2)) for a, b, c, v in low.itertuples(index=False) if pd.notna(v)],
            below98=int((df["now_avl"] < 98).sum()), chronic=int(df["Chronic"].notna().sum()))
    for d in grids:
        d["trk"] = tg.get(d["name"], {})

    # Issue lists behind the "3 basics + MW" KPIs
    items = {}

    def add(grid, kind, site, status_, note):
        if grid is None or (isinstance(grid, float) and pd.isna(grid)):
            return
        s = "" if status_ is None or (isinstance(status_, float) and pd.isna(status_)) else str(status_).strip()
        n = None if note is None or (isinstance(note, float) and pd.isna(note)) else str(note)[:110]
        if isinstance(site, float) and not pd.isna(site) and site == int(site):
            site = int(site)  # .xlsb returns whole numbers as floats
        items.setdefault(grid, []).append(dict(kind=kind, site=None if pd.isna(site) else str(site), status=s or "Pending", note=n))

    def col(df, *names):
        for n in names:
            if n in df.columns:
                return n
        sys.exit(f"None of the columns {names} found; sheet columns: {list(df.columns)[:20]}")

    def feed(sheet, kind, site, stat, note):
        df = bk.frame(sheet)
        site_c, stat_c, note_c = col(df, *site), col(df, *stat), col(df, *note)
        for _, r in df.iterrows():
            add(r["Grid"], kind, r[site_c], r[stat_c], r[note_c])

    feed("Not Operational DGs", "Not operational DG", ["DG CURRENT SITE"], ["Current Status"], ["Remarks Category"])
    feed("2 Phase Missing", "2-phase missing", ["Site Name"], ["Status"], ["Fault Type"])
    feed("Fluctuated Sites", "High fluctuation", ["Site"], ["Current Status", "Status"], ["Detailed RCA"])
    feed("Down Cells", "Down cell", ["Site ID"], ["Status"], ["Fault Type"])
    feed("Zero Traffic", "Zero traffic", ["SID"], ["Status"], ["Detailed RCA"])
    feed("VSWR", "VSWR", ["Site"], ["Status"], ["Alarm title"])
    feed("High TempAlm", "High temperature", ["Site"], ["Status"], ["RCA"])
    feed("T Prime", "T-Prime", ["Site ID"], ["Status", "Current Status"], ["T-Prime Category"])
    feed("RSL Deviation Link", "RSL deviation", ["Site IDs"], ["Status"], ["RCA Detail"])
    feed("TXN Critical Alarms", "Critical alarm", ["Sites"], ["Resolved Status"], ["Name"])
    eb = bk.frame("E-Band Availability")
    for _, r in eb.iterrows():
        v = pd.to_numeric(r["Link Availability"], errors="coerce")
        if pd.notna(v) and v < 0.99:
            add(r["Grid"], "Hi-cap link <99%", r["Sites"], "Pending", r["Link Name"])
    for d in grids:
        d["items"] = items.get(d["name"], [])

    assert [x["region"] for x in summ] == [x["name"] for x in region_rows], "Ex Summ regions do not match Grid Performance regions"
    meta = dict(title=title, last=last_lbl, now=now_lbl, period=f"{now_lbl}-{year % 100:02d}",
                source=Path(str(src)).name, generated=dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                months_n=n_months, rev_months=pos["t_rev"][1] - pos["t_rev"][0] + 1)
    payload = dict(regions=region_rows, grids=grids, summary=summ, districts=districts, months=months, meta=meta)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, default=str, separators=(",", ":"))
    return payload


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    p = build(sys.argv[1], sys.argv[2])
    print(f"OK: {len(p['grids'])} grids, {len(p['districts'])} districts, months {p['months']}, period {p['meta']['now']}")
