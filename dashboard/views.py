import json
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from . import landing
from .models import Snapshot
from .snapshot import KEY


@xframe_options_sameorigin   # fullscreen mode opens pages inside the fullscreen page (see _fs.html)
def home(request):
    """The one landing page: RCTO Central and Grid Excellence shown as modules."""
    return render(request, 'site/portal.html', landing.portal())


@xframe_options_sameorigin
def dashboards(request):
    snap = Snapshot.objects.filter(key=KEY).first()
    if snap is None:
        return render(request, 'site/empty.html', status=503)
    # '</' is escaped so the JSON can never close the <script> tag it is placed in
    data = json.dumps(snap.payload, ensure_ascii=False).replace('</', '<\\/')
    return render(request, 'site/dashboards.html', {'data_json': data})
