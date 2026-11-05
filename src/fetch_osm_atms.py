"""Download ATM locations in Luxembourg from OpenStreetMap at several dates.

Uses the Overpass API "attic" mode ([date:...]) to recover the map as it was before the
Bancomat rollout started (summer 2026). Points are kept only if they fall inside the
national boundary (OSM relation 2171347). Nearby duplicates (an ATM node and a bank
tagged atm=yes within 30 m) are merged into one site.

Output: data/raw/osm_atms_<label>.csv with columns site_id, lon, lat, n_objects, operators
Run from the repository root:  python src/fetch_osm_atms.py
"""
import csv, json, time, sys
from pathlib import Path
import numpy as np
import requests
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).parent))
from laea import fwd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OVERPASS = "https://overpass-api.de/api/interpreter"
HEADERS = {"User-Agent": "cash-access-luxembourg research script (github.com/GeneTheStoic)"}
BBOX = "49.40,5.70,50.20,6.55"  # south, west, north, east
DATES = {"2019-07-01": "2019-07-01T00:00:00Z",   # year of the 595-ATM figure
         "2024-01-01": "2024-01-01T00:00:00Z",   # before the rollout
         "2026-06-01": "2026-06-01T00:00:00Z",   # just before the first Bancomat machines
         "now": None}


def overpass(query, tries=4):
    for i in range(tries):
        r = requests.post(OVERPASS, data={"data": query}, headers=HEADERS, timeout=300)
        if r.status_code == 200:
            return r.json()
        print(f"  Overpass status {r.status_code}, retrying in {20 * (i + 1)} s")
        time.sleep(20 * (i + 1))
    raise RuntimeError("Overpass request failed")


def boundary():
    """Luxembourg national boundary as a shapely polygon (cached as GeoJSON)."""
    import osmnx as ox
    from shapely.geometry import shape, mapping
    f = RAW / "luxembourg_boundary.geojson"
    if f.exists():
        return shape(json.loads(f.read_text())["features"][0]["geometry"])
    gdf = ox.geocode_to_gdf("R2171347", by_osmid=True)
    geom = gdf.geometry.iloc[0]
    f.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"osm_relation": 2171347}, "geometry": mapping(geom)}]}))
    return geom


def fetch(label, date):
    head = f'[out:json][timeout:240]{"[date:%s]" % json.dumps(date) if date else ""};'
    q = (head + f'(node["amenity"="atm"]({BBOX});'
         f'node["amenity"="bank"]["atm"="yes"]({BBOX});'
         f'way["amenity"="bank"]["atm"="yes"]({BBOX}););out center tags;')
    els = overpass(q)["elements"]
    pts = []
    for e in els:
        lon = e.get("lon", e.get("center", {}).get("lon"))
        lat = e.get("lat", e.get("center", {}).get("lat"))
        if lon is None:
            continue
        t = e.get("tags", {})
        pts.append((lon, lat, t.get("operator") or t.get("brand") or t.get("name") or ""))
    return pts


def merge(pts, poly, radius_m=30.0):
    from shapely.geometry import Point
    pts = [p for p in pts if poly.contains(Point(p[0], p[1]))]
    if not pts:
        return []
    E, N = fwd(np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
    tree = cKDTree(np.c_[E, N])
    parent = list(range(len(pts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in tree.query_pairs(radius_m):
        parent[find(i)] = find(j)
    groups = {}
    for i in range(len(pts)):
        groups.setdefault(find(i), []).append(i)
    sites = []
    for k, idx in enumerate(groups.values()):
        lon = float(np.mean([pts[i][0] for i in idx])); lat = float(np.mean([pts[i][1] for i in idx]))
        ops = sorted(set(pts[i][2] for i in idx if pts[i][2]))
        sites.append((k, round(lon, 6), round(lat, 6), len(idx), "|".join(ops)))
    return sites


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    poly = boundary()
    for label, date in DATES.items():
        print(f"Fetching OSM ATMs at {label} ...")
        sites = merge(fetch(label, date), poly)
        out = RAW / f"osm_atms_{label}.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["site_id", "lon", "lat", "n_objects", "operators"])
            w.writerows(sites)
        print(f"  {len(sites)} sites -> {out.relative_to(ROOT)}")
        time.sleep(5)
