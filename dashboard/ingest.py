"""Read the four raw files into the database. Nothing is filtered, changed or guessed."""
import datetime as dt
import openpyxl
from django.db import transaction
from .models import Complaint, OfcBreak, SiteAvailability

COMPLAINT_TAB = 'CPM - NOMC-E2E-REGIONS'
COMPLAINT_COLS = ['SN', 'Month#', 'ACCEPTTIME', 'ServiceTitle', 'City', 'Sub Region', 'Site ID',
                  'Site Classification', 'Main Tagging', 'Routing Team']


def _s(v):
    return '' if v is None else str(v).strip()


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None          # '-' or blank = no value


def _header_map(header):
    """first occurrence of every header (the OFC files carry two 'Region' columns)"""
    m = {}
    for i, h in enumerate(header):
        m.setdefault(_s(h), i)
    return m


@transaction.atomic
def load_complaints(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[COMPLAINT_TAB]
    it = ws.iter_rows(values_only=True)
    h = _header_map(next(it))
    missing = [c for c in COMPLAINT_COLS if c not in h]
    if missing:
        raise ValueError(f'tab {COMPLAINT_TAB!r} is missing columns: {missing}')
    ix = [h[c] for c in COMPLAINT_COLS]
    Complaint.objects.all().delete()
    batch, n = [], 0
    for row in it:
        sn = row[ix[0]]
        if sn is None or _s(sn) == '':        # the tab carries ~980k empty trailing rows
            continue
        site = _num(row[ix[6]])
        batch.append(Complaint(
            sn=_s(sn), month=int(row[ix[1]]), accept_time=dt.datetime.strptime(_s(row[ix[2]]), '%Y/%m/%d %H:%M:%S'),
            service_title=_s(row[ix[3]]), city=_s(row[ix[4]]), sub_region=_s(row[ix[5]]),
            site_id=int(site) if site is not None else None, site_classification=_s(row[ix[7]]),
            main_tagging=_s(row[ix[8]]), routing_team=_s(row[ix[9]])))
        if len(batch) >= 2000:
            Complaint.objects.bulk_create(batch); n += len(batch); batch = []
    Complaint.objects.bulk_create(batch); n += len(batch)
    return n


@transaction.atomic
def load_ofc(path, year):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb['Data']
    it = ws.iter_rows(values_only=True)
    h = _header_map(next(it))
    sec = 'OFC Sections' if 'OFC Sections' in h else 'Fiber Sections'
    flag = 'OFC / Non OFC Corrected' if 'OFC / Non OFC Corrected' in h else 'OFC /NON-OFC'
    ev = 'CMPak Event# / S#'
    OfcBreak.objects.filter(year=year).delete()
    batch, n = [], 0
    for row in it:
        d = row[h['Date']]
        if d is None:
            continue
        if isinstance(d, dt.datetime):
            d = d.date()
        batch.append(OfcBreak(year=year, event_id=_s(row[h[ev]]), vendor=_s(row[h['OFC Vendor']]), date=d,
                              sub_region=_s(row[h['Sub-Region']]), network_type=_s(row[h['Network Type (LH/Metro/FTTS)']]),
                              sections=_s(row[h[sec]]), ofc_flag=_s(row[h[flag]]),
                              duration_min=_num(row[h['Duration']])))
        if len(batch) >= 2000:
            OfcBreak.objects.bulk_create(batch); n += len(batch); batch = []
    OfcBreak.objects.bulk_create(batch); n += len(batch)
    return n


@transaction.atomic
def load_availability(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    header = next(it)
    h = _header_map(header)
    # fixed layout: 'Cell Avail%' (col T) then 22 monthly availability columns (Jan 2025 .. Oct 2026),
    # 'Load Shedding Trend' then 22 monthly load-shedding columns
    if (_s(header[0]) != 'SITE_ID' or _s(header[19]) != 'Cell Avail%' or _s(header[42]) != 'Load Shedding Trend'
            or len(header) < 65):
        raise ValueError('unexpected column layout in the availability file')
    SiteAvailability.objects.all().delete()
    batch = []
    for row in it:
        if row[0] is None:
            continue
        batch.append(SiteAvailability(
            site_id=int(row[0]), sub_region=_s(row[h['Sub-Region']]), grid=_s(row[h['Grid']]),
            group=_s(row[h['Group']]), bb_type=_s(row[h['BB Type']]), dg_operational=_s(row[h['DG Operational']]),
            chronic=_s(row[h['Chronic Below Target']]) != '',
            avail=[_num(v) for v in row[20:42]], ls=[_num(v) for v in row[43:65]]))
    SiteAvailability.objects.bulk_create(batch)
    return len(batch)
