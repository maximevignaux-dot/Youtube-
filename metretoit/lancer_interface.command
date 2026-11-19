#!/bin/bash
# MétréToit — double-cliquez sur ce fichier (Mac / Linux) pour ouvrir l'interface de test.
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo "Première utilisation : installation (1 à 3 minutes)…"
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt || { echo "Échec de l'installation : Python 3 est-il installé ?"; read -r; exit 1; }
fi
( sleep 2; (open http://localhost:5000 || xdg-open http://localhost:5000) >/dev/null 2>&1 ) &
.venv/bin/python interface.py
