import re
f = r"c:\paddleMap\Paddlespots.csv"
coord_re = re.compile(r'maps/search/(?:@)?(-?\d+\.\d+),(-?\d+\.\d+)')
dec_pair_re = re.compile(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)')
dms_re = re.compile(r'(\d+°\d+\'\d+(?:\.\d+)?"?\s*[NS]).*?(\d+°\d+\'\d+(?:\.\d+)?"?\s*[EW])', re.I)

def dms2(d):
    m = re.match(r"(\d+)[°\s]+(\d+)'[\s]?(\d+(?:\.\d+)?)\"?\s*([NSEW])", d, re.I)
    if not m:
        return None
    deg = int(m.group(1)); minute = int(m.group(2)); sec = float(m.group(3)); dir = m.group(4).upper()
    dec = deg + minute/60 + sec/3600
    if dir in ('S','W'):
        dec = -dec
    return dec

count = 0
spots = []
with open(f, encoding='utf-8', errors='ignore') as fh:
    for line in fh:
        if not line.strip():
            continue
        lat = None; lon = None
        m = coord_re.search(line)
        if m:
            lat = float(m.group(1)); lon = float(m.group(2))
        else:
            m2 = dec_pair_re.search(line)
            if m2:
                lat = float(m2.group(1)); lon = float(m2.group(2))
            else:
                m3 = dms_re.search(line)
                if m3:
                    la = dms2(m3.group(1)); lo = dms2(m3.group(2))
                    if la is not None and lo is not None:
                        lat = la; lon = lo
        if lat is None or lon is None:
            continue
        if 40.0 <= lat <= 45.6 and -80.0 <= lon <= -71.0:
            count += 1
            spots.append((lat, lon, line.strip()))
print(count)
for s in spots:
    print(f"{s[0]:.6f},{s[1]:.6f} - {s[2]}")
