from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "grid_report"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="grid_report:report", permanent=False), name="home"),  # no separate landing: the site landing page lists modules
    path("report/", views.report, name="report"),       # Grid Excellence dashboard
    path("analysis/", views.analysis, name="analysis"), # cross-metric analysis lab
    path("data.json", views.report_json, name="data"),
]
