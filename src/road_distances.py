"""Road distances from every populated 1 km cell to the nearest ATM, for each network scenario.

1. Downloads the drivable OpenStreetMap road network of Luxembourg (plus a 2 km margin) with OSMnx.
2. Snaps cell centroids and ATM sites to the nearest road node (straight-line snap distance is added).
3. Runs one multi-source Dijkstra per scenario from a virtual source linked to all ATM nodes.
4. Also computes the cell-to-cell road distance matrix used to optimize machine placement.

Outputs (data/derived/):
  road_distance_by_cell.csv   grid_id, snap_m, d_<scenario>_km for every scenario
  road_cell_to_cell_km.npz    float32 matrix (cells x cells) of road distances in km
Run from the repository root after fetch_osm_atms.py:  python src/road_distances.py
"""
import csv, sys, time
from pathlib import Path
import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).parent))
from laea import fwd
from common import load_cells, load_sites, scenarios

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "data" / "derived"


def road_graph():
    import osmnx as ox
    import json
    from shapely.geometry import shape
    bfile = ROOT / "data" / "raw" / "luxembourg_boundary.geojson"
    poly = shape(json.loads(bfile.read_text())["features"][0]["geometry"])
    G = ox.graph_from_polygon(poly.buffer(0.03), network_type="drive", simplify=True, retain_all=False)
    ids = list(G.nodes)
    pos = {n: i for i, n in enumerate(ids)}
    lon = np.array([G.nodes[n]["x"] for n in ids]); lat = np.array([G.nodes[n]["y"] for n in ids])
    E, N = fwd(lon, lat)
    best = {}
    for u, v, d in G.edges(data=True):
        i, j = sorted((pos[u], pos[v]))
        if i == j:
            continue
        L = max(float(d.get("length", 0.0)), 0.1)
        if L < best.get((i, j), np.inf):
            best[(i, j)] = L                     # parallel links: keep the shortest
    ij = np.array(list(best.keys())); w = np.array(list(best.values()))
    n = len(ids)
    A = sp.coo_matrix((w, (ij[:, 0], ij[:, 1])), shape=(n, n)).tocsr()  # upper triangle, used as undirected
    return A, np.c_[E, N], n


def multi_source(A, xy, n, src_xy):
    """Distance (m) from every graph node to the nearest of several points, including snap distances."""
    tree = cKDTree(xy)
    snap, node = tree.query(src_xy)
    # add a virtual node n connected to every source node with weight = snap distance
    k = len(node)
    extra = sp.coo_matrix((np.maximum(snap, 0.1), (np.full(k, n), node)), shape=(n + 1, n + 1))
    B = sp.bmat([[A, None], [None, sp.csr_matrix((1, 1))]]).tocsr() + extra.tocsr()
    return dijkstra(B, directed=False, indices=n)[:n]


if __name__ == "__main__":
    t0 = time.time()
    cells = load_cells()
    A, xy, n = road_graph()
    print(f"Road graph: {n} nodes, {A.nnz} road links ({time.time() - t0:.0f} s)")
    tree = cKDTree(xy)
    csnap, cnode = tree.query(cells["xy"])
    out = {"grid_id": cells["grid_id"], "snap_m": np.round(csnap, 1)}
    for name, label in scenarios().items():
        s = load_sites(name)
        dn = multi_source(A, xy, n, s["xy"])
        out[f"d_{name}_km"] = np.round((dn[cnode] + csnap) / 1000.0, 4)
        print(f"  {label}: {len(s['xy'])} sites done ({time.time() - t0:.0f} s)")
    DER.mkdir(parents=True, exist_ok=True)
    keys = list(out)
    with open(DER / "road_distance_by_cell.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(keys)
        for i in range(len(cells["grid_id"])):
            w.writerow([out[k][i] for k in keys])
    # cell-to-cell matrix for placement optimization
    uniq, inv = np.unique(cnode, return_inverse=True)
    D = np.empty((len(uniq), len(cnode)))
    for c in range(0, len(uniq), 100):                                # chunks keep memory low
        D[c:c + 100] = dijkstra(A, directed=False, indices=uniq[c:c + 100])[:, cnode]
        print(f"  cell-to-cell matrix: {min(c + 100, len(uniq))}/{len(uniq)}", end="\r")
    # M[i, j]: distance from the population of cell i to a machine placed at the road node nearest to cell j
    print()
    M = (D[inv] + csnap[:, None]) / 1000.0
    np.savez_compressed(DER / "road_cell_to_cell_km.npz", M=M.astype(np.float32), grid_id=cells["grid_id"])
    print(f"Done in {time.time() - t0:.0f} s")
