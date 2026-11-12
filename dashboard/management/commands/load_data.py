from django.core.management.base import BaseCommand
from dashboard import ingest, snapshot


class Command(BaseCommand):
    help = 'Load the raw files into the database and recompute the dashboards.'

    def add_arguments(self, p):
        p.add_argument('--complaints', required=True, help="Consolidated_file_of_RCTO-FOPS-FC_Data.xlsx (tab 'CPM - NOMC-E2E-REGIONS')")
        p.add_argument('--ofc2026', required=True, help='2026_OFC_Breaks_Detail.xlsx')
        p.add_argument('--ofc2025', required=True, help='2025_OFC_Breaks_Detail.xlsx')
        p.add_argument('--availability', required=True, help='Availability_with_LS_Jan_-_Nov2026.xlsx')

    def handle(self, *a, **o):
        self.stdout.write(f"complaints   : {ingest.load_complaints(o['complaints'])} rows")
        self.stdout.write(f"OFC 2026     : {ingest.load_ofc(o['ofc2026'], 2026)} rows")
        self.stdout.write(f"OFC 2025     : {ingest.load_ofc(o['ofc2025'], 2025)} rows")
        self.stdout.write(f"availability : {ingest.load_availability(o['availability'])} sites")
        snapshot.refresh()
        self.stdout.write(self.style.SUCCESS('dashboards recomputed'))
