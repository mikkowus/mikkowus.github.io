import re
from pathlib import Path
import csv

p = Path('Paddlespots.csv')
if not p.exists():
    print('Paddlespots.csv not found')
    raise SystemExit(1)
backup = p.with_suffix('.csv.bak2')
backup.write_text(p.read_text(encoding='utf-8'), encoding='utf-8')

rows = []
with p.open(newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        rows.append(row)
if not rows:
    print('Empty CSV')
    raise SystemExit(1)

header = rows[0]
# Ensure header has at least 5 columns
while len(header) < 5:
    header.append('')
# New header: keep first 5 columns (Title,Note,URL,Tags,Comment), then CoordsLat, CoordsLon
new_header = header[:5] + ['CoordsLat', 'CoordsLon']

# regex to find decimal latitude,longitude pair
dec_pair_re = re.compile(r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)')

out_rows = [new_header]
for row in rows[1:]:
    # normalize row length to at least 5
    while len(row) < 5:
        row.append('')
    title, note, url, tags, comment = row[:5]
    rest = row[5:]
    lat = ''
    lon = ''
    # first try: search URL column for maps/search/@lat,lon
    if url and 'maps/search' in url:
        m = dec_pair_re.search(url)
        if m:
            lat = m.group(1); lon = m.group(2)
    # second: if rest contains two numeric values as last two entries
    if not lat and rest:
        # join rest with commas and search for a decimal pair
        joined = ','.join(rest)
        m = dec_pair_re.search(joined)
        if m:
            lat = m.group(1); lon = m.group(2)
    # third: look for any decimal pair in the entire original line
    if not lat:
        line = ','.join([title, note, url, tags, comment] + rest)
        m = dec_pair_re.search(line)
        if m:
            lat = m.group(1); lon = m.group(2)
    out_rows.append([title, note, url, tags, comment, lat, lon])

# write back to file
with p.open('w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerows(out_rows)

print('Converted CSV; backup at', backup.name)
