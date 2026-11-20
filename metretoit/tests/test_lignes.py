"""Mètres linéaires (égouts, faîtages, rives, arêtiers, noues) sur les toits simulés."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_synthetique as T  # noqa: E402
from toiture.analyse import analyser  # noqa: E402
from toiture.lignes import calculer_lignes, totaux  # noqa: E402

c35, t35, t30 = np.cos(np.radians(35)), np.tan(np.radians(35)), np.tan(np.radians(30))
_t1, _t2 = np.tan(np.radians(40)), np.tan(np.radians(25))
_y0 = _t2 * 10 / (_t1 + _t2)
ATTENDU = {
    "2 pans 35°": {"égout": 24, "faîtage": 12, "rive": 4 * 4.5 / c35},
    "4 pans 30°": {"égout": 44, "faîtage": 4, "arêtier": 4 * np.sqrt(2 * 4.5 ** 2 + (4.5 * t30) ** 2)},
    "en L 2 ailes": {"égout": 64, "faîtage": 32, "rive": 4 * 4 / c35,
                     "arêtier": np.sqrt(32 + (4 * t35) ** 2), "noue": np.sqrt(32 + (4 * t35) ** 2)},
    "toit plat": {"bord de toit plat": 50},
    "2 pans 40°/25°": {"égout": 24, "faîtage": 12,
                       "rive": 2 * _y0 / np.cos(np.radians(40)) + 2 * (10 - _y0) / np.cos(np.radians(25))},
}


@pytest.mark.parametrize("nom", list(ATTENDU))
@pytest.mark.parametrize("graine", [1, 2, 3, 4])
def test_lineaires(nom, graine):
    emp, z, _, _, _, para = T.CAS[nom]()
    res = analyser(*T.fabriquer(emp, z, np.random.default_rng(graine), para))
    t = totaux(calculer_lignes(res))
    for typ in set(t) | set(ATTENDU[nom]):
        attendu = ATTENDU[nom].get(typ, 0.0)
        # au plus 0,6 m ou 3 % d'écart par type de ligne
        assert abs(t.get(typ, 0.0) - attendu) <= max(0.6, 0.03 * attendu), (typ, t, ATTENDU[nom])


def test_selection_de_pans():
    emp, z, _, _, _, para = T.toit_2_pans()
    res = analyser(*T.fabriquer(emp, z, np.random.default_rng(1), para))
    lignes = calculer_lignes(res)
    un = totaux(lignes, pans={1})
    # un seul versant : son égout (12 m), ses 2 rives, et le faîtage partagé
    assert abs(un["égout"] - 12) < 0.3 and abs(un["faîtage"] - 12) < 0.3
    assert abs(un["rive"] - 2 * 4.5 / c35) < 0.3
