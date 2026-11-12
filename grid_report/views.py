import json
from pathlib import Path

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin

DATA_FILE = Path(__file__).resolve().parent / "data" / "report.json"
_cache = {"mtime": None, "data": None}


def _load():
    """Read report.json, reloading only when the file changes."""
    mtime = DATA_FILE.stat().st_mtime
    if _cache["mtime"] != mtime:
        with DATA_FILE.open(encoding="utf-8") as fh:
            _cache["data"] = json.load(fh)
        _cache["mtime"] = mtime
    return _cache["data"]


def dashboard(request):
    """One-page dashboard: report + analysis combined."""
    return render(request, "grid_report/dashboard.html", {"report_data": _load()})


@xframe_options_sameorigin  # lets Dashboard and Analysis open inside each other while fullscreen is on
def report(request):
    return render(request, "grid_report/report.html", {"report_data": _load()})


def report_json(request):
    return JsonResponse(_load())


@xframe_options_sameorigin
def analysis(request):
    """Cross-metric analysis dashboard (correlations, pair analysis, site classes, 3D)."""
    return render(request, "grid_report/analysis.html", {"report_data": _load()})
