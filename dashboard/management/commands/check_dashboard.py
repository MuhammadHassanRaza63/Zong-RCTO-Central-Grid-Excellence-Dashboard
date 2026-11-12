import json
import re
from django.core.management.base import BaseCommand, CommandError
from dashboard import snapshot


# blocks that exist only in this project (not in the reference HTML); verified separately
EXTRA_OK = {'scorecard'}


class Command(BaseCommand):
    help = 'Compare the computed numbers with the DATA block of a reference dashboard HTML file.'

    def add_arguments(self, p):
        p.add_argument('html')

    def handle(self, *a, **o):
        s = open(o['html'], encoding='utf-8').read()
        m = re.search(r'const DATA = (\{.*?\});\n', s, re.S)
        if not m:
            raise CommandError('no DATA block found in the HTML file')
        ref = json.loads(m.group(1))
        got = json.loads(json.dumps(snapshot.compute_payload()))
        bad = []

        def cmp(x, y, p=''):
            if isinstance(y, dict):
                for k in y:
                    cmp(x[k], y[k], f'{p}/{k}') if k in x else bad.append((p + '/' + k, 'missing'))
                bad.extend((p + '/' + k, 'extra') for k in x if k not in y and not (p == '' and k in EXTRA_OK))
            elif isinstance(y, list):
                if len(x) != len(y):
                    bad.append((p, f'length {len(x)} vs {len(y)}')); return
                for i, (u, v) in enumerate(zip(x, y)):
                    cmp(u, v, f'{p}[{i}]')
            elif isinstance(y, float) or isinstance(x, float):
                if x is None or y is None or abs(x - y) > 1e-9:
                    bad.append((p, x, y))
            elif x != y:
                bad.append((p, x, y))
        cmp(got, ref)
        n = len(json.dumps(ref))
        if bad:
            for b in bad[:50]:
                self.stdout.write(str(b))
            raise CommandError(f'{len(bad)} mismatches')
        self.stdout.write(self.style.SUCCESS(f'OK - every value matches the reference ({n:,} characters of data compared)'))
