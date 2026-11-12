"""Build the metric inputs from the database and store the result as a Snapshot."""
import pandas as pd
from django.conf import settings
from . import metrics
from .models import Complaint, OfcBreak, SiteAvailability, Snapshot

ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6}
CATS = {'Coverage Related': 'Coverage', 'Internet / Data Speed Related': 'Data speed',
        'Call Connectivity/Quality Related': 'Call quality'}
KEY = 'dashboard'


def _complaints():
    c = pd.DataFrame.from_records(Complaint.objects.values(
        'month', 'accept_time', 'city', 'sub_region', 'site_id', 'site_classification', 'main_tagging', 'routing_team'))
    out = pd.DataFrame({
        'm': c['month'].astype(int),
        'geo': c['sub_region'].str.replace('Central ', '', regex=False).map(ROMAN),
        'fops': c['routing_team'].str.extract(r'FOPs C(\d)')[0].astype(int),
        'cat': c['main_tagging'].map(CATS),
        'site': c['site_id'],
        'ts': pd.to_datetime(c['accept_time']),
        'city': c['city'], 'site_class': c['site_classification'],
    })
    return out


def _sites():
    rows = list(SiteAvailability.objects.values('site_id', 'sub_region', 'grid', 'group', 'bb_type', 'dg_operational',
                                                'chronic', 'avail', 'ls'))
    df = pd.DataFrame({'site': [r['site_id'] for r in rows], 'grid': [r['grid'] for r in rows],
                       'team': [int(r['sub_region'][-1]) for r in rows], 'group': [r['group'] for r in rows],
                       'bb': [r['bb_type'] for r in rows], 'dg': [r['dg_operational'] for r in rows],
                       'chronic': [r['chronic'] for r in rows]})
    num = lambda col, i: pd.to_numeric(pd.Series([r[col][i] for r in rows]), errors='coerce')
    for i in range(12):                       # 2025: Jan..Dec
        df[f'av25_{i}'] = num('avail', i); df[f'ls25_{i}'] = num('ls', i)
    for i in range(10):                       # 2026: Jan..Oct
        df[f'av{i}'] = num('avail', 12 + i); df[f'ls{i}'] = num('ls', 12 + i)
    return df


def _ofc(year):
    o = pd.DataFrame.from_records(OfcBreak.objects.filter(year=year).values('date', 'sub_region', 'network_type', 'sections', 'ofc_flag', 'vendor', 'duration_min'))
    d = pd.to_datetime(o['date'])
    return pd.DataFrame({
        'm': d.dt.month,
        'ofc': o['ofc_flag'].astype(str).str.strip().str.upper().eq('OFC'),
        'team': o['sub_region'].str.extract(r'Central-(\d)')[0].astype(float),
        'net': o['network_type'], 'sections': o['sections'], 'vendor': o['vendor'], 'dur': o['duration_min'],
    })


def compute_payload():
    return metrics.compute(_complaints(), _sites(), _ofc(2026), _ofc(2025),
                           settings.CUTS_TARGET, settings.CUTS_TARGET_SOURCE)


def refresh():
    payload = compute_payload()
    Snapshot.objects.update_or_create(key=KEY, defaults={'payload': payload})
    return payload
