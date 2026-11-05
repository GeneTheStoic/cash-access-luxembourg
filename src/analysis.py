"""Access to cash in Luxembourg before and after the Bancomat consolidation.

Uses road distances when data/derived/road_distance_by_cell.csv exists (run road_distances.py),
otherwise straight-line distances, and reports which metric was used.

Outputs: results/results.json, results/summary.md, results/communes.csv, figures/*.png
Run from the repository root:  python src/analysis.py
"""
import csv, json, sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).parent))
from common import load_cells, load_sites, scenarios

ROOT = Path(__file__).resolve().parents[1]
DER, RES, FIG = ROOT / "data" / "derived", ROOT / "results", ROOT / "figures"
THRESH = [1, 2, 3, 5, 7]
BASELINE = "osm_2024_01_01"
PLAN = "bancomat_plan"


# ---------- distances ----------
def distances(cells, scen):
    road_file = DER / "road_distance_by_cell.csv"
    if road_file.exists():
        rows = list(csv.DictReader(open(road_file)))
        assert [r["grid_id"] for r in rows] == list(cells["grid_id"]), "cell order mismatch"
        out = {}
        for k in scen:
            col = f"d_{k}_km"
            if col in rows[0]:
                out[k] = np.array([float(r[col]) for r in rows])
        if PLAN in out:
            return out, "road"
    out = {}
    for k in scen:
        d, _ = cKDTree(load_sites(k)["xy"]).query(cells["xy"])
        out[k] = d / 1000.0
    return out, "straight-line"


def cell_matrix(cells, metric):
    f = DER / "road_cell_to_cell_km.npz"
    if metric == "road" and f.exists():
        return np.load(f)["M"].astype(float)
    xy = cells["xy"]
    return np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1)) / 1000.0


# ---------- statistics ----------
def wquant(x, w, q):
    o = np.argsort(x); c = np.cumsum(w[o]) / w.sum()
    return float(x[o][np.searchsorted(c, q)])


def coverage(d, cells):
    P, P65 = cells["pop"], cells["pop65"]
    r = {"mean_km": float((d * P).sum() / P.sum()), "mean_km_65plus": float((d * P65).sum() / P65.sum()),
         "median_km": wquant(d, P, .5), "p90_km": wquant(d, P, .9), "p99_km": wquant(d, P, .99)}
    for t in THRESH:
        r[f"share_within_{t}km"] = float(P[d <= t].sum() / P.sum())
        r[f"share65_within_{t}km"] = float(P65[d <= t].sum() / P65.sum())
        r[f"pop_beyond_{t}km"] = int(round(P[d > t].sum()))
    return r


def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return float(2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum()) - (n + 1) / n)


def catchments(cells, sites_xy):
    _, k = cKDTree(sites_xy).query(cells["xy"])
    load = np.bincount(k, weights=cells["pop"], minlength=len(sites_xy))
    return {"sites": int(len(sites_xy)), "median_pop": float(np.median(load)), "p90_pop": float(np.percentile(load, 90)),
            "max_pop": float(load.max()), "sites_with_no_nearest_residents": int((load == 0).sum()), "gini": gini(load)}


def redundancy(cells, sites_xy, t=5.0):
    """Share of residents with at least two distinct sites within t km (straight line)."""
    d, _ = cKDTree(sites_xy).query(cells["xy"], k=2)
    return float(cells["pop"][d[:, 1] / 1000 <= t].sum() / cells["pop"].sum())


def greedy_add(M, pop, d0, steps, t):
    """Add sites one by one (candidates: populated cells) maximizing residents newly within t km."""
    cur = d0.copy(); chosen, cov = [], [float(pop[cur <= t].sum() / pop.sum())]
    for _ in range(steps):
        newly = ((M <= t) & (cur[:, None] > t)) * pop[:, None]
        j = int(newly.sum(0).argmax())
        chosen.append(j); cur = np.minimum(cur, M[:, j]); cov.append(float(pop[cur <= t].sum() / pop.sum()))
    return chosen, cov, cur


def greedy_pmedian(M, pop, p):
    """Greedy p-median: same number of sites placed to minimize mean distance (candidates: populated cells)."""
    cur = np.full(len(pop), np.inf); chosen = []
    for _ in range(p):
        cost = (np.minimum(cur[:, None], M) * pop[:, None]).sum(0)
        j = int(cost.argmin()); chosen.append(j); cur = np.minimum(cur, M[:, j])
    return chosen, cur


# ---------- figures ----------
def figures(cells, D, metric, res, sites):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm
    FIG.mkdir(exist_ok=True)
    xy = cells["xy"] / 1000
    bounds = [0, 1, 2, 3, 5, 7, 12]
    cmap = plt.get_cmap("YlOrRd", len(bounds) - 1); norm = BoundaryNorm(bounds, cmap.N)

    def basemap(ax, d, title):
        ax.scatter(xy[:, 0], xy[:, 1], c=d, cmap=cmap, norm=norm, marker="s", s=9, linewidths=0)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title, fontsize=10)
        for s in ax.spines.values(): s.set_visible(False)

    fig, axs = plt.subplots(1, 2 if BASELINE in D else 1, figsize=(9 if BASELINE in D else 4.8, 5.4))
    axs = np.atleast_1d(axs)
    if BASELINE in D:
        basemap(axs[0], D[BASELINE], f"Before: OSM ATMs, 1 Jan 2024 ({len(sites[BASELINE])} sites)")
        b = sites[BASELINE] / 1000; axs[0].scatter(b[:, 0], b[:, 1], s=3, c="k")
    basemap(axs[-1], D[PLAN], f"After: Bancomat plan ({len(sites[PLAN])} sites)")
    p = sites[PLAN] / 1000; axs[-1].scatter(p[:, 0], p[:, 1], s=4, c="k")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    fig.colorbar(sm, ax=axs, shrink=0.6, label=f"{metric} distance to nearest ATM (km)")
    fig.savefig(FIG / "map_distance.png", dpi=200, bbox_inches="tight"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    grid = np.linspace(0, 10, 201)
    for k, lab, ls in [(BASELINE, "Before (OSM, Jan 2024)", "--"), (PLAN, "After (Bancomat plan)", "-")]:
        if k in D:
            ax.plot(grid, [cells["pop"][D[k] <= g].sum() / cells["pop"].sum() for g in grid], ls, color="k", label=lab)
    ax.axvline(5, color="gray", lw=.6); ax.set_xlabel(f"{metric} distance (km)")
    ax.set_ylabel("share of residents within distance"); ax.legend(frameon=False); ax.set_ylim(0, 1.01)
    fig.savefig(FIG / "coverage_curves.png", dpi=200, bbox_inches="tight"); plt.close(fig)

    if BASELINE in D:
        delta = D[PLAN] - D[BASELINE]
        fig, ax = plt.subplots(figsize=(4.8, 5.4))
        from matplotlib.colors import ListedColormap
        bnd = [-8, -0.5, 0.5, 1, 2, 3, 12]
        cm = ListedColormap(["#4393c3", "#e8e8e8", "#fddbc7", "#f4a582", "#d6604d", "#8b0a1e"])
        ax.scatter(xy[:, 0], xy[:, 1], c=delta, cmap=cm, norm=BoundaryNorm(bnd, cm.N), marker="s", s=9, linewidths=0)
        ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
        for s in ax.spines.values(): s.set_visible(False)
        fig.colorbar(plt.cm.ScalarMappable(cmap=cm, norm=BoundaryNorm(bnd, cm.N)), ax=ax, shrink=.6,
                     label="change in distance to nearest ATM (km)")
        ax.set_title("Change in access after consolidation", fontsize=10)
        fig.savefig(FIG / "map_change.png", dpi=200, bbox_inches="tight"); plt.close(fig)

    g = res["placement"]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.plot(range(len(g["greedy_coverage_path"])), np.array(g["greedy_coverage_path"]) * 100, "k-o", ms=3)
    ax.plot([13], [94], marker="s", color="#b2182b", ms=6, ls="none", label="operator: 13 further sites, 94%")
    ax.legend(frameon=False, loc="lower right")
    ax.set_xlabel("additional machines (greedy choice)"); ax.set_ylabel(f"% residents within {g['threshold_km']} km")
    fig.savefig(FIG / "greedy_additions.png", dpi=200, bbox_inches="tight"); plt.close(fig)


# ---------- main ----------
def main():
    cells = load_cells(); scen = scenarios()
    D, metric = distances(cells, scen)
    sites = {k: load_sites(k)["xy"] for k in scen}
    res = {"metric": metric, "population": int(cells["pop"].sum()), "cells": int(len(cells["pop"])),
           "scenarios": {k: {"label": scen[k], "sites": int(len(sites[k])), **coverage(D[k], cells),
                             "catchments": catchments(cells, sites[k]),
                             "redundancy_two_sites_within_5km_straight": redundancy(cells, sites[k])}
                         for k in D}}
    res["bancomat_machine_rows"] = load_sites(PLAN)["n_rows"]

    # before/after
    if BASELINE in D:
        delta = D[PLAN] - D[BASELINE]; P = cells["pop"]; P65 = cells["pop65"]
        dens = P  # residents per km2 (1 km cells)
        ba = {"pop_farther_0_5km": int(P[delta > .5].sum()), "pop_farther_1km": int(P[delta > 1].sum()),
              "pop_farther_2km": int(P[delta > 2].sum()), "pop_closer_0_5km": int(P[delta < -.5].sum()),
              "pop_newly_beyond_5km": int(P[(D[PLAN] > 5) & (D[BASELINE] <= 5)].sum()),
              "mean_change_km": float((delta * P).sum() / P.sum()),
              "mean_change_km_65plus": float((delta * P65).sum() / P65.sum())}
        w = P / P.sum()
        def wcorr(a, b):
            ma, mb = (a * w).sum(), (b * w).sum()
            return float(((a - ma) * (b - mb) * w).sum() / np.sqrt(((a - ma) ** 2 * w).sum() * ((b - mb) ** 2 * w).sum()))
        ba["corr_change_share65"] = wcorr(delta, cells["share65"])
        ba["corr_change_log_density"] = wcorr(delta, np.log(dens))
        ba["note"] = ("OpenStreetMap records fewer ATMs than existed (the banks reported 595 machines in 2019). "
                      "Missing legacy machines can only shorten the true 'before' distances, so increases in distance "
                      "are lower bounds and decreases are upper bounds, provided the mapped ATMs existed.")
        com = []
        for l in sorted(set(cells["lau2"])):
            m = cells["lau2"] == l; Pm = P[m]
            com.append({"commune": cells["commune_name"][l], "population_2021": int(Pm.sum()),
                        "mean_change_km": round(float((delta[m] * Pm).sum() / Pm.sum()), 3),
                        "residents_farther_1km": int(Pm[delta[m] > 1].sum())})
        ba["communes_largest_increase"] = sorted(com, key=lambda r: -r["mean_change_km"])[:8]
        res["before_after"] = ba

    # commune table
    rows = []
    for l in sorted(set(cells["lau2"])):
        m = cells["lau2"] == l; P = cells["pop"][m]
        r = {"lau2": l, "commune": cells["commune_name"][l], "canton": cells["canton"][l], "population_2021": int(P.sum()),
             "share_65plus_2018": round(float(cells["share65"][m][0]), 4)}
        for k in D:
            r[f"mean_km_{k}"] = round(float((D[k][m] * P).sum() / P.sum()), 3)
            r[f"share_beyond_5km_{k}"] = round(float(P[D[k][m] > 5].sum() / P.sum()), 4)
        rows.append(r)
    RES.mkdir(exist_ok=True)
    with open(RES / "communes.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
    res["communes_worst_access_plan"] = [
        {k: r[k] for k in ("commune", "population_2021", f"mean_km_{PLAN}", f"share_beyond_5km_{PLAN}")}
        for r in sorted(rows, key=lambda r: -r[f"mean_km_{PLAN}"])[:10]]

    # placement
    M = cell_matrix(cells, metric); P = cells["pop"]
    t = 5.0
    chosen, path, _ = greedy_add(M, P, D[PLAN], 25, t)
    pm_sites, pm_d = greedy_pmedian(M, P, len(sites[PLAN]))
    res["placement"] = {
        "threshold_km": t, "greedy_coverage_path": path,
        "greedy_sites_grid_id": [str(cells["grid_id"][j]) for j in chosen],
        "greedy_sites_commune": [cells["commune_name"][cells["lau2"][j]] for j in chosen],
        "same_size_pmedian_mean_km": float((pm_d * P).sum() / P.sum()),
        "same_size_pmedian_share_within_5km": float(P[pm_d <= t].sum() / P.sum()),
        "note": "candidate sites restricted to populated 1 km cells; objective covers residents only "
                "(commuters, shops and tourists are outside the model)"}
    for n_add in (5, 10, 13, 20):
        res["placement"][f"coverage_after_{n_add}_additions"] = path[n_add]

    (RES / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    figures(cells, D, metric, res, sites)
    summary(res)
    print(json.dumps({k: res[k] for k in ("metric", "population")}, indent=1))
    print((RES / "summary.md").read_text(encoding="utf-8"))


def summary(res):
    L = [f"# Results (distance metric: {res['metric']})", "",
         "| Scenario | Sites | Mean km | Median km | P90 km | Within 1 km | Within 3 km | Within 5 km | 65+ within 5 km | Residents beyond 5 km |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for k, s in res["scenarios"].items():
        L.append(f"| {s['label']} | {s['sites']} | {s['mean_km']:.2f} | {s['median_km']:.2f} | {s['p90_km']:.2f} | "
                 f"{100*s['share_within_1km']:.1f}% | {100*s['share_within_3km']:.1f}% | {100*s['share_within_5km']:.1f}% | "
                 f"{100*s['share65_within_5km']:.1f}% | {s['pop_beyond_5km']:,} |")
    if "before_after" in res:
        b = res["before_after"]; L += ["", "## Before (OSM, 1 Jan 2024) vs. after (Bancomat plan)", ""]
        L += [f"- {k}: {v:,.3f}" if isinstance(v, float) else f"- {k}: {v:,}" for k, v in b.items()
              if isinstance(v, (int, float))]
        L += ["", f"Note: {b['note']}"]
    p = res["placement"]
    L += ["", "## Placement", "", f"- Coverage within {p['threshold_km']} km now: {100*p['greedy_coverage_path'][0]:.1f}%",
          f"- After 13 greedy additions: {100*p['coverage_after_13_additions']:.1f}%",
          f"- Same number of sites placed by greedy p-median: mean {p['same_size_pmedian_mean_km']:.2f} km, "
          f"{100*p['same_size_pmedian_share_within_5km']:.1f}% within 5 km"]
    (RES / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
