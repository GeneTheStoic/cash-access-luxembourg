# Data sources (downloaded 5 November 2026)

| File | Source | Notes |
|---|---|---|
| `population_grid_1km_2021.csv` | STATEC, population census 2021 on the 1 km² INSPIRE grid (EPSG:3035), via Geoportail Luxembourg OGC API, collection 2514; cell-to-commune assignment from collection 2717/2 (`maxm2LAU2`) | 1,636 populated cells, 643,420 residents. `east_m`, `north_m` are the lower-left corner of the cell. |
| `communes_population_2018.csv` | STATEC, population by age group and commune on 1 January 2018, Geoportail collection 1566 | Used only for the commune share of residents aged 65 and over (602,005 residents in total). |
| `bancomat_sites_20261105.csv` | Bancomat locator (bancomat.lu), public GeoJSON behind the map | 214 machines at 207 distinct sites; `available_now` = 1 for the 22 machines in service on 5 November 2026. The operator notes that the map is indicative and that some sites are still to be confirmed. |
| `osm_atms_<date>.csv` | OpenStreetMap via the Overpass API (attic queries), created by `src/fetch_osm_atms.py` | ATMs and banks tagged `atm=yes` inside the national boundary, merged within 30 m. © OpenStreetMap contributors, ODbL. |
| `luxembourg_boundary.geojson` | OpenStreetMap relation 2171347 via OSMnx | National boundary. |
