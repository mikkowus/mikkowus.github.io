import json
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
infile = repo_root / 'usgs_ny.rdb'
outfile = repo_root / 'usgs-ny-sites.json'
with open(infile, encoding='utf-8') as fh:
    lines = [l.rstrip('\n') for l in fh]
# find header line by searching for agency_cd
header_idx = None
for i,l in enumerate(lines):
    if 'agency_cd' in l and 'site_no' in l:
        header_idx = i
        header = l.split('\t')
        break
if header_idx is None:
    raise SystemExit('Header not found')
start = header_idx + 2
sites = []
for l in lines[start:]:
    if not l.strip(): continue
    if l.startswith('#'): continue
    parts = l.split('\t')
    if len(parts) < 6: continue
    obj = dict(zip(header, parts))
    lat = obj.get('dec_lat_va','').strip()
    lon = obj.get('dec_long_va','').strip()
    try:
        latf = float(lat)
        lonf = float(lon)
    except:
        continue
    sites.append({
        'site_no': obj.get('site_no',''),
        'station_nm': obj.get('station_nm',''),
        'dec_lat_va': latf,
        'dec_long_va': lonf
    })
with open(outfile, 'w', encoding='utf-8') as of:
    json.dump(sites, of, indent=2)
print('Wrote', len(sites), 'sites to', outfile)
