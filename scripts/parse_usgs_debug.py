with open(r"c:\paddleMap\usgs_ny.rdb", encoding='utf-8') as fh:
    lines = [l.rstrip('\n') for l in fh]
for idx,l in enumerate(lines[:60]):
    print(idx+1, l[:200])
# find header
for i,l in enumerate(lines):
    if l.startswith('#') or l.strip()=='':
        continue
    print('header line idx', i+1, l)
    header = l.split('\t')
    print('header cols', header)
    print('next line (types):', lines[i+1])
    print('sample data line:', lines[i+2][:200])
    break
