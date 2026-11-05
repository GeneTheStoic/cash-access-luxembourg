"""Shared loaders: population cells, communes, and ATM site scenarios (all in EPSG:3035 metres)."""
import csv
from pathlib import Path
import numpy as np
from laea import fwd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

BANCOMAT_FILE = "bancomat_sites_20261105.csv"
OSM_LABELS = ["2019-07-01", "2024-01-01", "2026-06-01", "now"]


def load_cells():
    """Populated 1 km cells (census 2021) with centroid coordinates, population, commune and 65+ share."""
    rows = list(csv.DictReader(open(RAW / "population_grid_1km_2021.csv", encoding="utf-8")))
    com = {r["lau2"]: r for r in csv.DictReader(open(RAW / "communes_population_2018.csv", encoding="utf-8"))}
    E = np.array([float(r["east_m"]) + 500 for r in rows])
    N = np.array([float(r["north_m"]) + 500 for r in rows])
    pop = np.array([float(r["population_2021"]) for r in rows])
    lau = np.array([r["lau2"] for r in rows])
    s65 = np.array([int(com[l]["pop_65plus_2018"]) / int(com[l]["pop_total_2018"]) for l in lau])
    names = {l: com[l]["commune"] for l in com}
    canton = {l: com[l]["canton"] for l in com}
    return {"grid_id": np.array([r["grid_id"] for r in rows]), "xy": np.c_[E, N], "pop": pop,
            "pop65": pop * s65, "share65": s65, "lau2": lau, "commune_name": names, "canton": canton}


def _read_sites(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    ll = sorted(set((float(r["lon"]), float(r["lat"])) for r in rows))   # unique sites
    lon = np.array([p[0] for p in ll]); lat = np.array([p[1] for p in ll])
    E, N = fwd(lon, lat)
    return {"xy": np.c_[E, N], "lon": lon, "lat": lat, "n_rows": len(rows)}


def scenarios():
    """Available ATM network scenarios: key -> label."""
    s = {"bancomat_plan": "Bancomat network as planned (locator, 5 Nov 2026)"}
    for lab in OSM_LABELS:
        if (RAW / f"osm_atms_{lab}.csv").exists():
            s["osm_" + lab.replace("-", "_")] = f"OpenStreetMap ATMs, {lab}"
    return s


def load_sites(name):
    if name == "bancomat_plan":
        return _read_sites(RAW / BANCOMAT_FILE)
    lab = name[4:].replace("_", "-")
    return _read_sites(RAW / f"osm_atms_{lab}.csv")
