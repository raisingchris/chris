"""Synthetic portfolio example. Run with Python 3; no third-party packages."""
import csv
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

root = Path(__file__).parent
fields = ['record_id', 'customer', 'category', 'amount', 'date']
rows = list(csv.DictReader((root / 'input.csv').open(newline='')))
cleaned, rejected, seen = [], [], set()
duplicates = 0
for line, row in enumerate(rows, start=2):
    try:
        out = {k: row[k].strip() for k in fields}
        if not out['record_id'] or not out['customer']:
            raise ValueError('Missing required record ID or customer')
        out['category'] = out['category'].lower()
        amount = Decimal(out['amount'].replace(',', ''))
        if not amount.is_finite():
            raise ValueError('Amount is not finite')
        out['amount'] = format(amount.quantize(Decimal('0.01')), 'f')
        out['date'] = datetime.strptime(out['date'].replace('/', '-'), '%Y-%m-%d').date().isoformat()
        signature = tuple(out[k] for k in fields)
        if signature in seen:
            duplicates += 1
            continue
        seen.add(signature)
        cleaned.append(out)
    except (ValueError, InvalidOperation) as e:
        rejected.append({'source_line': line, 'reason': 'Invalid numeric amount' if isinstance(e, InvalidOperation) else str(e)})
with (root / 'cleaned.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(cleaned)
report = {'sample_data': 'synthetic; no client data', 'input_rows': len(rows),
          'output_rows': len(cleaned), 'duplicate_rows_removed': duplicates, 'rejected_rows': rejected}
(root / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
assert len(rows) == len(cleaned) + duplicates + len(rejected)
print(json.dumps(report))
