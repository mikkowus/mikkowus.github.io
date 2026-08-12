# mikkowus.github.io

Static site (served at [mikkowus.com](https://mikkowus.com) via GitHub Pages)
for finding NY paddle spots, with live USGS gauge heights and NWS weather/wind
overlaid on a Leaflet map. No build step — the HTML files are served as-is.

## Pages

- **index.html** — landing page, links to the main map.
- **windy-style-map.html** — the main map: NY USGS gauges + paddle spots on
  one clustered layer, curated canoe launch points on their own toggleable
  layer (with GPS paddling routes on a second toggleable layer), click-anywhere
  wind lookup, a "My Position" locate button, optional radar/forecast overlay,
  and drive-time-to-spot lookups.
- **add-location.html** — mobile-friendly page for trusted contributors to log
  in and submit new canoe launch points (GPS capture or tap-to-place-pin),
  with offline queueing via `offline-queue.js` + `sw.js`. Backed by the
  Cloudflare Worker in `worker/`.
- **review.html** — owner-only page to approve/reject pending submissions from
  `add-location.html` and export approved ones as GeoJSON to paste into
  `launch-points.geojson`.
- **shared.js** — fetch/parsing helpers (USGS sites, water height, NWS
  weather, OSRM routing, Nominatim geocoding) shared by `windy-style-map.html`,
  `add-location.html`, and `review.html`, with in-memory caching so repeated
  popup opens don't re-hit the same APIs.

## Data pipeline

**Paddle spots** (`paddlespots_coordinates.csv`, loaded by
`windy-style-map.html`): exported from Google Maps as
`googlePinsScraperTool/paddle spots from joe.kmz`, converted with
`googlePinsScraperTool/extract_coordinates_final.py` (see
`googlePinsScraperTool/notes.md` for how to run it). `googlePinsScraperTool/Paddlespots.csv`
is an older, superseded export kept for historical reference — see
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
