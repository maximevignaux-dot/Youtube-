"""Vue de dessus du toit (toit.png) et tableau texte pour le terminal."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from scipy import ndimage  # noqa: E402

PALETTE = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#B07AA1", "#76B7B2", "#EDC948",
           "#FF9DA7", "#9C755F", "#86BCB6", "#D37295", "#A0CBE8", "#8CD17D", "#F1CE63"]


def _contours(ax, geom, **kw):
    polys = getattr(geom, "geoms", [geom])
    for i, p in enumerate(polys):
        x, y = p.exterior.xy
        ax.plot(x, y, **(kw if i == 0 else {k: v for k, v in kw.items() if k != "label"}))
        for r in p.interiors:
            ax.plot(*r.xy, **{k: v for k, v in kw.items() if k != "label"})


def dessiner(res: dict, titre: str, fichier):
    g = res.get("grille_emprise")
    fig, ax = plt.subplots(figsize=(9, 9), dpi=130)
    if g is not None:
        n = len(res["pans"])
        couleurs = [PALETTE[k % len(PALETTE)] for k in range(n)]
        lab = g.etiquettes.astype(float)
        img = np.full(lab.shape, np.nan)
        img[lab >= 0] = lab[lab >= 0]
        ax.imshow(np.ma.masked_invalid(img), origin="lower", extent=g.etendue,
                  cmap=ListedColormap(couleurs), vmin=-0.5, vmax=n - 0.5, interpolation="nearest", alpha=0.85)
        nm = np.where(lab == -1, 1.0, np.nan)
        if np.isfinite(nm).any():
            ax.imshow(np.ma.masked_invalid(nm), origin="lower", extent=g.etendue,
                      cmap=ListedColormap(["#BBBBBB"]), interpolation="nearest")
        gn = res["grille_nuage"]
        ax.contour(*gn.centres(), (gn.etiquettes >= 0).astype(float), levels=[0.5],
                   colors="#333333", linestyles="--", linewidths=1)
        pts = res["points_locaux"]
        if len(pts) > 15000:      # grand toit : on n'affiche qu'un échantillon des points
            pts = pts[np.random.default_rng(0).choice(len(pts), 15000, replace=False)]
        ax.scatter(pts[:, 0], pts[:, 1], s=0.3, c="k", alpha=0.25)
        X, Y = g.centres()
        # toit très complexe : on ne numérote que les 30 plus grands pans (tous restent colorés)
        a_numeroter = set(range(len(res["pans"])))
        if len(res["pans"]) > 25:
            a_numeroter = set(sorted(range(len(res["pans"])), key=lambda k: -res["pans"][k]["surface_projetee_m2"])[:30])
        for k, (p, q) in enumerate(zip(res["pans"], res["objets_pans"])):
            m = g.etiquettes == k
            if not m.any() or k not in a_numeroter:
                continue
            # point d'étiquette : la cellule du pan la plus éloignée de son bord
            dist = ndimage.distance_transform_edt(m)
            i = np.unravel_index(np.argmax(dist), m.shape)
            cx, cy = X[i], Y[i]
            if p["azimut_deg"] is not None:
                a = np.radians(p["azimut_deg"])
                etendue = max(g.nx, g.ny) * g.cellule
                L = min(max(2.0, 0.03 * etendue), 0.8 * dist[i] * g.cellule + 0.6)
                ax.annotate("", xy=(cx + L * np.sin(a), cy + L * np.cos(a)),
                            xytext=(cx - 0.3 * L * np.sin(a), cy - 0.3 * L * np.cos(a)),
                            arrowprops=dict(arrowstyle="-|>", color="k", lw=1.6))
            ax.text(cx, cy, str(p["numero"]), ha="center", va="center", fontsize=12, weight="bold",
                    bbox=dict(boxstyle="circle,pad=0.25", fc="white", ec="k", lw=0.8))
    _contours(ax, res["emprise_locale"], color="k", lw=2, label="emprise BD TOPO")
    ax.plot([], [], "--", color="#333333", label="étendue du nuage de points")
    ax.set_aspect("equal")
    ax.set_xlabel("Est (m)")
    ax.set_ylabel("Nord (m)")
    ax.set_title(titre, fontsize=10)
    ax.legend(loc="upper right", fontsize=8)
    ax.annotate("N", xy=(0.04, 0.96), xytext=(0.04, 0.88), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color="k"), ha="center", fontsize=11, weight="bold")
    fig.tight_layout()
    fig.savefig(fichier)
    plt.close(fig)


def tableau(res: dict) -> str:
    l = []
    tete = f"{'Pan':>3} | {'Type':<11} | {'Pente':>6} | {'Pente':>6} | {'Orient.':>7} | {'Azim.':>5} | " \
           f"{'S. projetée':>11} | {'S. réelle':>9} | {'Points':>6} | {'Écart':>6}"
    l.append(tete)
    l.append(f"{'':>3} | {'':<11} | {'(°)':>6} | {'(%)':>6} | {'':>7} | {'(°)':>5} | {'(m²)':>11} | {'(m²)':>9} | {'':>6} | {'(cm)':>6}")
    l.append("-" * len(tete))
    for p in res["pans"]:
        az = "—" if p["azimut_deg"] is None else str(p["azimut_deg"])
        l.append(f"{p['numero']:>3} | {p['type']:<11} | {p['pente_deg']:>6.1f} | {p['pente_pct']:>6.1f} | "
                 f"{p['orientation']:>7} | {az:>5} | {p['surface_projetee_m2']:>11.2f} | "
                 f"{p['surface_reelle_m2']:>9.2f} | {p['nb_points']:>6} | {p['ecart_moyen_cm']:>6.1f}")
    l.append("-" * len(tete))
    return "\n".join(l)
