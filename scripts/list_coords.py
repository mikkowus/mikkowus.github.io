import csv
from pathlib import Path
p = Path('Paddlespots.csv')
with p.open(encoding='utf-8') as f:
    r = list(csv.reader(f))
headers = r[0] if r else []
coords_idx = None
for i,h in enumerate(headers):
    if h.strip().lower()=='coords':
        coords_idx = i
        break
if coords_idx is None:
    print('No Coords column')
    raise SystemExit(0)

found = 0
for i,row in enumerate(r[1:], start=2):
    if len(row) <= coords_idx: continue
    field = row[coords_idx].strip()
    if not field: continue
    print(i, field, '=>', row[0] if row else '')
    found += 1
    if found >= 20:
        break
print('total coords entries:', found)
