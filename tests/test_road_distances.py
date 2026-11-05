"""Checks the multi-source Dijkstra on a synthetic road grid against brute force (no internet needed)."""
import sys
from pathlib import Path
import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from road_distances import multi_source


def grid_graph(k=30, step=200.0, seed=0):
    rng = np.random.default_rng(seed)
    xy = np.array([(i * step, j * step) for i in range(k) for j in range(k)], float)
    r, c, w = [], [], []
    for i in range(k):
        for j in range(k):
            a = i * k + j
            if i + 1 < k: r.append(a); c.append(a + k); w.append(step * rng.uniform(1, 1.6))
            if j + 1 < k: r.append(a); c.append(a + 1); w.append(step * rng.uniform(1, 1.6))
    n = k * k
    return sp.coo_matrix((w, (r, c)), shape=(n, n)).tocsr(), xy, n


def test_multi_source_matches_brute_force():
    A, xy, n = grid_graph()
    rng = np.random.default_rng(1)
    src = rng.uniform(0, 5800, size=(12, 2))
    got = multi_source(A, xy, n, src)
    snap = np.linalg.norm(xy[:, None, :] - src[None, :, :], axis=2)
    node = snap.argmin(axis=0); s = snap.min(axis=0)
    full = dijkstra(A, directed=False, indices=node)            # sources x nodes
    want = (full + s[:, None]).min(axis=0)
    assert np.allclose(got, want, atol=0.2)


if __name__ == "__main__":
    test_multi_source_matches_brute_force(); print("ok")
