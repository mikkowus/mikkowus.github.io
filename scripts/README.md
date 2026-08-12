# scripts/

## Current

- **parse_usgs_rdb.py** — regenerates `usgs-ny-sites.json` (the offline fallback
  used by the map pages when the live USGS API is unreachable) from
  `usgs_ny.rdb`. Run this after re-downloading `usgs_ny.rdb` to refresh the
  fallback data.
- **import_paddlespots_data.py** — one-time import that merged real paddlespot
  data (from a Google Takeout "Saved" export, processed by a separate tool at
  `~/projects/2026_google_saved_data_extraction`) into `paddlespots.geojson`.
  Not meant to be re-run against the same source; kept for reference on how
  the NY filtering and duplicate-detection (by name and by proximity) works,
  in case another Takeout export needs merging in later.
- **validate_paddlespots.py** — sanity-checks `paddlespots.geojson` after
  editing it by hand: required fields present, `water_body_type`/`access_type`
  match the controlled vocab if set, coordinates in a sane range, and every
  referenced `tracks[].gpx` file exists. Run it after any manual edit.

## Legacy (one-time migrations, already applied — kept for reference)

`Paddlespots.csv` was an earlier, manually-exported list of paddle spots. These
scripts were one-off tools used to add and normalize a coordinates column on
that file:

- **add_coords.py** — added a `Coords` column to `Paddlespots.csv`.
- **convert_to_separate_coords.py** — split `Coords` into `CoordsLat`/`CoordsLon`.
- **check_coords.py** / **list_coords.py** — inspected how many rows had
  coordinates.
- **count_paddlespots.py** — ad hoc coordinate-counting script, hardcoded to a
  local `c:\paddleMap\Paddlespots.csv` path.

That pipeline was later superseded by `googlePinsScraperTool/extract_coordinates_final.py`
(reads a Google Maps KML export directly, writes `paddlespots_coordinates.csv`),
which has in turn been superseded by `import_paddlespots_data.py` above — the
map no longer loads `paddlespots_coordinates.csv` at all as of the
`paddlespots.geojson` consolidation. Both `Paddlespots.csv` and
`paddlespots_coordinates.csv` are kept in the repo as historical raw data, not
as part of the live data pipeline. Note: the legacy scripts above hardcode a
`Paddlespots.csv` path at the repo root or an old local `c:\paddleMap\` path —
the file itself has since moved to `googlePinsScraperTool/Paddlespots.csv`, so
re-running these as-is would need that path updated first. They're
historical/already-applied, not meant to be re-run.
