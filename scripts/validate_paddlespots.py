"""Sanity-check paddlespots.geojson before committing new entries.

Not a build step -- run manually after editing the file:
    python3 scripts/validate_paddlespots.py

Most entries are real but sparse (imported from a Google Takeout export with
little beyond a name and coordinates), so only id/name/region are required --
water_body_name/type, access_type, description etc. are enrichable over time
and an empty value there is honest, not an error.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GEOJSON_PATH = REPO_ROOT / 'paddlespots.geojson'

REQUIRED_PROPERTIES = ['id', 'name', 'region']
WATER_BODY_TYPES = {'river', 'lake', 'pond', 'reservoir', 'canal', 'bay'}
ACCESS_TYPES = {'public-boat-launch', 'carry-in', 'beach', 'private-permission-required'}

# Roughly the northeastern US -- loose enough to allow neighboring states, tight
# enough to catch a typo'd sign or swapped lat/lon.
LAT_RANGE = (38.0, 47.5)
LON_RANGE = (-80.5, -68.0)


def main():
    data = json.loads(GEOJSON_PATH.read_text(encoding='utf-8'))
    errors = []
    seen_ids = set()

    for i, feature in enumerate(data.get('features', [])):
        props = feature.get('properties', {})
        label = props.get('id') or props.get('name') or f'feature[{i}]'

        for field in REQUIRED_PROPERTIES:
            if not props.get(field):
                errors.append(f'{label}: missing required field "{field}"')

        fid = props.get('id')
        if fid:
            if fid in seen_ids:
                errors.append(f'{label}: duplicate id "{fid}"')
            seen_ids.add(fid)

        water_body_type = props.get('water_body_type')
        if water_body_type and water_body_type not in WATER_BODY_TYPES:
            errors.append(f'{label}: unknown water_body_type "{water_body_type}" (expected one of {sorted(WATER_BODY_TYPES)})')

        access_type = props.get('access_type')
        if access_type and access_type not in ACCESS_TYPES:
            errors.append(f'{label}: unknown access_type "{access_type}" (expected one of {sorted(ACCESS_TYPES)})')

        geometry = feature.get('geometry', {})
        coords = geometry.get('coordinates', [])
        if len(coords) != 2:
            errors.append(f'{label}: geometry.coordinates must be [lon, lat]')
        else:
            lon, lat = coords
            if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1]):
                errors.append(f'{label}: latitude {lat} outside expected range {LAT_RANGE}')
            if not (LON_RANGE[0] <= lon <= LON_RANGE[1]):
                errors.append(f'{label}: longitude {lon} outside expected range {LON_RANGE}')

        for track in props.get('tracks', []):
            gpx_path = REPO_ROOT / track.get('gpx', '')
            if not track.get('gpx') or not gpx_path.is_file():
                errors.append(f'{label}: track "{track.get("id", "?")}" references missing file "{track.get("gpx")}"')

    if errors:
        print(f'{len(errors)} problem(s) found:')
        for e in errors:
            print(f'  - {e}')
        raise SystemExit(1)

    print(f'OK: {len(data.get("features", []))} paddlespots validated.')


if __name__ == '__main__':
    main()
