from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from grid_report.tools.build_report_data import build

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "data" / "report.json"


class Command(BaseCommand):
    help = "Load the monthly 'Network KPI Report - Grid Excellence' workbook (.xlsb or .xlsx) into the dashboard."

    def add_arguments(self, parser):
        parser.add_argument("workbook", help="Path to the .xlsb / .xlsx file")
        parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON (default: grid_report/data/report.json)")

    def handle(self, *args, **opts):
        src = Path(opts["workbook"])
        if not src.exists():
            raise CommandError(f"File not found: {src}")
        try:
            p = build(src, opts["out"])
        except SystemExit as e:  # layout problems are reported by the builder
            raise CommandError(str(e))
        m = p["meta"]
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {src.name}: {len(p['grids'])} grids, {len(p['districts'])} districts, {m['title']} -> {opts['out']}"))
