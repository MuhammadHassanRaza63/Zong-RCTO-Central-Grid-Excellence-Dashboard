from django.db import models


class Complaint(models.Model):
    """One row of tab 'CPM - NOMC-E2E-REGIONS' (Central region, owner RCTO Central)."""
    sn = models.CharField(max_length=32, unique=True)
    month = models.PositiveSmallIntegerField(db_index=True)          # 'Month#' column
    accept_time = models.DateTimeField()                              # 'ACCEPTTIME'
    service_title = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=80, blank=True)
    sub_region = models.CharField(max_length=20, blank=True)         # 'Central I' ... 'Central VI'
    site_id = models.IntegerField(null=True, blank=True, db_index=True)
    site_classification = models.CharField(max_length=40, blank=True)
    main_tagging = models.CharField(max_length=80, blank=True)       # Coverage / Data speed / Call quality
    routing_team = models.CharField(max_length=20, blank=True)       # 'FOPs C1' ... 'FOPs C6'


class OfcBreak(models.Model):
    """One row of the yearly OFC Breaks Detail files (2025 and 2026)."""
    year = models.PositiveSmallIntegerField(db_index=True)
    event_id = models.CharField(max_length=40, blank=True)
    vendor = models.CharField(max_length=60, blank=True)
    date = models.DateField(db_index=True)
    sub_region = models.CharField(max_length=20, blank=True)         # 'Central-1' ...
    network_type = models.CharField(max_length=20, blank=True)       # LH / Metro / FTTS
    sections = models.CharField(max_length=200, blank=True)          # 'OFC Sections' / 'Fiber Sections'
    duration_min = models.FloatField(null=True, blank=True)          # 'Duration': fiber break time to restoration, minutes
    ofc_flag = models.CharField(max_length=40, blank=True)           # OFC / Non OFC ... (as in the file)


class SiteAvailability(models.Model):
    """One row per site of 'Network Availability with LS' (Jan 2025 - Oct 2026)."""
    site_id = models.IntegerField(unique=True)
    sub_region = models.CharField(max_length=20)                     # 'Central-1' ...
    grid = models.CharField(max_length=20, blank=True)
    group = models.CharField(max_length=30, blank=True)              # 'Group': Platinum+ / PGS / SB
    bb_type = models.CharField(max_length=40, blank=True)            # 'BB Type': power backup
    dg_operational = models.CharField(max_length=40, blank=True)     # 'DG Operational' (blank = not filled)
    chronic = models.BooleanField(default=False)                     # 'Chronic Below Target' filled
    avail = models.JSONField()                                       # 22 monthly cell availability values, Jan 2025 .. Oct 2026 (null = none)
    ls = models.JSONField()                                          # 22 monthly load-shedding hours, same months


class Snapshot(models.Model):
    """Computed dashboard numbers, refreshed every time data is loaded."""
    key = models.CharField(max_length=40, unique=True)
    payload = models.JSONField()
    computed_at = models.DateTimeField(auto_now=True)
