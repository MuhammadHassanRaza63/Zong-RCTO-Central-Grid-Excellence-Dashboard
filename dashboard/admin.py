from django.contrib import admin
from .models import Complaint, OfcBreak, SiteAvailability, Snapshot

for m in (Complaint, OfcBreak, SiteAvailability, Snapshot):
    admin.site.register(m)
