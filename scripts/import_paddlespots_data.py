"""One-time import: merge real Google Takeout paddlespot data into paddlespots.geojson.

Source: a Google Takeout "Saved" export of the "Paddlespots" Maps list, processed by
the (separate, not part of this repo) extraction tool at
~/projects/2026_google_saved_data_extraction into a flat paddlespots.json with resolved
lat/lng, formatted_address (for named places), and any saved notes.

This script:
  - Filters that source down to real New York entries only.
  - Skips anything that duplicates an already-curated entry in paddlespots.geojson
    (matched by name).
  - Generates a unique slug id per imported entry.
  - Appends them to paddlespots.geojson's existing FeatureCollection, leaving the
    already-curated entries untouched.

Run once:
    python3 scripts/import_paddlespots_data.py ~/projects/2026_google_saved_data_extraction/paddlespots.json

NY membership:
  - "place"-type source rows (resolved via Google Places API) are trusted by their
    formatted_address ending in ", NY" (+ optional zip).
  - "coords"-type rows (parsed directly from a dropped-pin URL, never geocoded) have no
    formatted_address, so a loose lat/lon bounding box is used, MINUS two rows manually
    verified (via Nominatim reverse geocoding, 2026-08) to actually be in Massachusetts
    despite falling inside that box.
"""
import json
import math
import re
import sys
from pathlib import Path

# Two points within this distance are treated as "the same place" -- catches
# saves that resolved to the same physical spot under a different title (e.g.
# "Town of Cortlandville River Access and Parking" turned out to be the exact
# same place_id as "Yaman Park", just pinned ~168m off). Chosen to sit between
# that confirmed-duplicate distance and the closest confirmed-DISTINCT pair
# found in this dataset (Syracuse Chargers Boathouse / Onondaga Lake Park
# Public Canoe and Kayak Launch, ~189m apart -- different amenities on the
# same shoreline, kept as separate points).
DUPLICATE_RADIUS_METERS = 180


def meters_between(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# Titles like "Dropped pin" or a bare DMS coordinate string are Google's
# fallback label when a save has no real name -- they carry no identifying
# information, so two rows sharing one of these "names" are NOT evidence of
# being the same place. Name-based dedup only applies to genuinely specific
# titles; generic ones rely on proximity alone.
GENERIC_TITLE_RE = re.compile(r'^\d+°')


def is_generic_title(title):
    return title.strip().lower() == 'dropped pin' or bool(GENERIC_TITLE_RE.match(title.strip()))

REPO_ROOT = Path(__file__).resolve().parents[1]
GEOJSON_PATH = REPO_ROOT / 'paddlespots.geojson'

# (lat, lng) pairs confirmed via reverse geocoding to be outside NY despite being
# inside the loose bounding box below (both are near Boston, MA).
KNOWN_NON_NY_COORDS = {
    (42.3032984, -71.2107383),
    (42.3028109, -71.2107912),
}


def in_ny_bbox(lat, lon):
    return 40.0 <= lat <= 45.6 and -80.0 <= lon <= -71.0


def is_ny(record):
    lat, lng = record.get('lat'), record.get('lng')
    if lat is None or lng is None:
        return False
    addr = record.get('formatted_address')
    if addr:
        # formatted_address sometimes ends with a trailing country clause
        # (", United States") and sometimes doesn't -- allow either.
        return bool(re.search(r',\s*NY\s*\d{0,5}(,.*)?$', addr))
    if (lat, lng) in KNOWN_NON_NY_COORDS:
        return False
    return in_ny_bbox(lat, lng)


def slugify(text, existing_ids):
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'spot'
    candidate = slug
    n = 2
    while candidate in existing_ids:
        candidate = f'{slug}-{n}'
        n += 1
    existing_ids.add(candidate)
    return candidate


def main():
    if len(sys.argv) != 2:
        print('Usage: python3 scripts/import_paddlespots_data.py <path to paddlespots.json>')
        raise SystemExit(1)

    source_path = Path(sys.argv[1]).expanduser()
    source = json.loads(source_path.read_text(encoding='utf-8'))

    existing = json.loads(GEOJSON_PATH.read_text(encoding='utf-8'))
    existing_features = existing['features']
    existing_ids = {f['properties']['id'] for f in existing_features}

    ny_records = [r for r in source if is_ny(r)]
    print(f'{len(ny_records)} NY records in source')

    # Some places were saved to the list more than once (same exact coordinates,
    # sometimes under a slightly different title). Keep one per coordinate pair --
    # whichever has a note, else whichever has the longer (more descriptive) title.
    by_coords = {}
    for r in ny_records:
        title = (r.get('title') or '').strip()
        if not title:
            continue
        key = (round(r['lat'], 6), round(r['lng'], 6))
        current = by_coords.get(key)
        if current is None:
            by_coords[key] = r
            continue
        current_note = (current.get('note') or '').strip()
        new_note = (r.get('note') or '').strip()
        if new_note and not current_note:
            by_coords[key] = r
        elif not new_note and current_note:
            pass  # keep current
        elif len(title) > len((current.get('title') or '').strip()):
            by_coords[key] = r

    skipped_dupe_coords = len(ny_records) - len(by_coords)

    existing_points = [
        (f['properties']['name'], f['geometry']['coordinates'][1], f['geometry']['coordinates'][0])
        for f in existing_features
    ]

    # A name match alone isn't safe -- generic titles like "Dropped pin" or a
    # bare DMS string repeat across many genuinely different real locations,
    # so name-based dedup is skipped for those (proximity alone still applies).
    # For genuinely specific titles, a generous radius also catches a re-pin
    # of the same real place under a slightly different location.
    SAME_NAME_RADIUS_METERS = 5000

    imported = []
    skipped_dupes = []
    imported_points = []  # also dedupe imported entries against each other by proximity
    for r in by_coords.values():
        title = (r.get('title') or '').strip()
        title_lower = title.lower()
        generic = is_generic_title(title)

        near = None
        for name, lat, lng in existing_points + imported_points:
            dist = meters_between(lat, lng, r['lat'], r['lng'])
            same_name = not generic and name.strip().lower() == title_lower
            if dist <= DUPLICATE_RADIUS_METERS or (same_name and dist <= SAME_NAME_RADIUS_METERS):
                near = name
                break
        if near:
            skipped_dupes.append(f'{title} (duplicate of "{near}")')
            continue

        feature_id = slugify(title, existing_ids)
        imported_points.append((title, r['lat'], r['lng']))
        imported.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [r['lng'], r['lat']]},
            'properties': {
                'id': feature_id,
                'name': title,
                'description': (r.get('note') or '').strip(),
                'region': 'NY',
                'water_body_name': '',
                'water_body_type': '',
                'access_type': '',
                'parking_notes': '',
                'tags': [],
                'nearest_gauge_site_no': '',
                'source_url': r.get('url', ''),
                'photos': [],
                'tracks': [],
            },
        })

    print(f'imported: {len(imported)}')
    print(f'skipped as exact-coordinate duplicate saves within the source: {skipped_dupe_coords}')
    print(f'skipped as duplicates of already-curated entries: {skipped_dupes}')

    existing_features.extend(imported)
    existing['features'] = existing_features
    GEOJSON_PATH.write_text(json.dumps(existing, indent=2) + '\n', encoding='utf-8')
    print(f'wrote {len(existing_features)} total features to {GEOJSON_PATH}')


if __name__ == '__main__':
    main()
