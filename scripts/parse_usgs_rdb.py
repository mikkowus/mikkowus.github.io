import json
import re
infile = r"c:\paddleMap\usgs_ny.rdb"
outfile = r"c:\paddleMap\usgs-ny-sites.json"
with open(infile, encoding='utf-8') as fh:
    lines = [l.rstrip('\n') for l in fh]
# find header line (first non-comment beginning without #)
header = None
for i,l in enumerate(lines):
    if l.startswith('#') or l.strip()=='' :
        continue
    # first non-comment line is probably header
    header = l.split('\t')
    start = i+2
    break
if header is None:
    raise SystemExit('No header found')
sites = []
for l in lines[start:]:
    if not l.strip(): continue
    parts = l.split('\t')
    if len(parts) < 6: continue
    obj = {}
    for k,v in zip(header, parts):
        obj[k] = v
    # ensure lat/lon present
    lat = obj.get('dec_lat_va','').strip()
    lon = obj.get('dec_long_va','').strip()
    if lat and lon:
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
