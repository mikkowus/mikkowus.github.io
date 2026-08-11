# scripts/

## Current

- **parse_usgs_rdb.py** — regenerates `usgs-ny-sites.json` (the offline fallback
  used by the map pages when the live USGS API is unreachable) from
  `usgs_ny.rdb`. Run this after re-downloading `usgs_ny.rdb` to refresh the
  fallback data.

## Legacy (one-time migration, already applied — kept for reference)

`Paddlespots.csv` was an earlier, manually-exported list of paddle spots. These
scripts were one-off tools used to add and normalize a coordinates column on
that file:

- **add_coords.py** — added a `Coords` column to `Paddlespots.csv`.
- **convert_to_separate_coords.py** — split `Coords` into `CoordsLat`/`CoordsLon`.
- **check_coords.py** / **list_coords.py** — inspected how many rows had
  coordinates.
- **count_paddlespots.py** — ad hoc coordinate-counting script, hardcoded to a
  local `c:\paddleMap\Paddlespots.csv` path.

This pipeline has been superseded by `googlePinsScraperTool/extract_coordinates_final.py`,
which reads a Google Maps KML export directly and writes
`paddlespots_coordinates.csv` — the file the map pages actually load. These
scripts are no longer part of the data pipeline; they're kept only because
`Paddlespots.csv` (their output) is still in the repo as historical raw data.
