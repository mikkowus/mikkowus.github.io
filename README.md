# mikkowus.github.io

Static site (served at [mikkowus.com](https://mikkowus.com) via GitHub Pages)
for finding NY paddle spots, with live USGS gauge heights and NWS weather/wind
overlaid on a Leaflet map. No build step — the HTML files are served as-is.

## Pages

- **index.html** — landing page, links to the two map pages.
- **windy-style-map.html** — the main map: NY USGS gauges + paddle spots on
  one clustered layer, curated canoe launch points on their own toggleable
  layer (with GPS paddling routes on a second toggleable layer), click-anywhere
  wind lookup, optional radar/forecast overlay, and drive-time-to-spot lookups.
- **ny-gauges-map.html** — a simpler gauges-only view of the same USGS data.
- **shared.js** — fetch/parsing helpers (USGS sites, water height, NWS
  weather, OSRM routing, Nominatim geocoding) shared by both map pages, with
  in-memory caching so repeated popup opens don't re-hit the same APIs.

## Data pipeline

**Paddle spots** (`paddlespots_coordinates.csv`, loaded by
`windy-style-map.html`): exported from Google Maps as
`paddle spots from joe.kmz`, converted with
`googlePinsScraperTool/extract_coordinates_final.py` (see
`googlePinsScraperTool/notes.md` for how to run it). `Paddlespots.csv` is an
older, superseded export kept for historical reference — see
`scripts/README.md`.

**USGS gauge fallback** (`usgs-ny-sites.json`, used when the live USGS API is
unreachable): generated from `usgs_ny.rdb` by `scripts/parse_usgs_rdb.py`.
Re-download the `.rdb` and re-run that script to refresh it.

**Canoe launch points** (`launch-points.geojson`, loaded by
`windy-style-map.html`): a hand-curated (not scraped) list of known-good canoe
launches, separate from the paddle-spots dataset above. Each feature can
optionally link to a `nearest_gauge_site_no` (surfaced as a live water-height
reading in its popup) and to one or more GPS routes under `tracks/*.gpx`
(rendered via the `leaflet-gpx` plugin on the "Routes" layer). Run
`python3 scripts/validate_launch_points.py` after editing the file — it
checks required fields, controlled-vocabulary values, coordinate sanity, and
that every referenced `.gpx` file actually exists.
