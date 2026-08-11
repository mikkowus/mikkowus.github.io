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

count_total = 0
count_ny = 0
samples = []
for row in r[1:]:
    if len(row) <= coords_idx: continue
    field = row[coords_idx].strip()
    if not field: continue
    count_total += 1
    parts = [p.strip() for p in field.split(',')]
    try:
        lat = float(parts[0]); lon = float(parts[1])
    except Exception:
        continue
    if 40.0 <= lat <= 45.6 and -80.0 <= lon <= -71.0:
        count_ny += 1
        samples.append((lat,lon,row[0] if row else ''))

print('coords_total=',count_total)
print('coords_in_NY=',count_ny)
print('\nfirst 20 NY samples:')
for s in samples[:20]:
    print(s)
