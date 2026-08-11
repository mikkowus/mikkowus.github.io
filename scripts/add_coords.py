import re
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'Paddlespots.csv'
backup = p.with_suffix('.csv.bak')
text = p.read_text(encoding='utf-8')
# backup
backup.write_text(text, encoding='utf-8')
lines = text.splitlines()
if not lines:
    print('Empty file')
    raise SystemExit(1)
header = lines[0]
cols = header.split(',')
if cols[-1].strip().lower() == 'coords':
    print('Coords column already present')
    raise SystemExit(0)
new_header = header + ',Coords'
out_lines = [new_header]

coord_re = re.compile(r'maps/search/(?:@)?(-?\d+\.\d+),(-?\d+\.\d+)', re.I)
dec_pair_re = re.compile(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)')
dms_re = re.compile(r"(\d+)[°:\s]+(\d+)'[\s]*(\d+(?:\.\d+)?)\"?\s*([NS]).*?(\d+)[°:\s]+(\d+)'[\s]*(\d+(?:\.\d+)?)\"?\s*([EW])", re.I)

def dms_to_dec(deg, minute, sec, dirc):
    try:
        deg = float(deg)
        minute = float(minute)
        sec = float(sec)
    except:
        return None
    dec = deg + minute/60.0 + sec/3600.0
    if dirc.upper() in ('S','W'):
        dec = -dec
    return dec

for line in lines[1:]:
    if line.strip() == '':
        out_lines.append('')
        continue
    coords = ''
    m = coord_re.search(line)
    if m:
        coords = f"{m.group(1)},{m.group(2)}"
    else:
        m2 = dec_pair_re.search(line)
        if m2:
            coords = f"{m2.group(1)},{m2.group(2)}"
        else:
            m3 = dms_re.search(line)
            if m3:
                lat = dms_to_dec(m3.group(1), m3.group(2), m3.group(3), m3.group(4))
                lon = dms_to_dec(m3.group(5), m3.group(6), m3.group(7), m3.group(8))
                if lat is not None and lon is not None:
                    coords = f"{lat:.6f},{lon:.6f}"
    # ensure any existing trailing commas preserved: append coords as last column
    out_lines.append(line + (',' + coords if coords else ','))

new_text = '\n'.join(out_lines) + '\n'
p.write_text(new_text, encoding='utf-8')
print('Wrote updated Paddlespots.csv and backup saved to', backup.name)
