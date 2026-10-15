# Atelier t-shirts humour (Printful)

Maxime ne code pas : tu fais tout, tu expliques en français simple, tu montres les résultats.

- `banque-slogans.xlsx` : toutes les idées de slogans et leur statut (Idée, Validé, Design fait…).
- `designs.json` : la fiche technique de chaque design (lignes, icône, couleur de t-shirt…).
- `generate.py` : fabrique les fichiers d'impression (4500 x 5400 px, transparent, 300 dpi) et les aperçus
  dans `sortie/<id>/`, plus `planche-du-jour.jpg`. `--only <id>` pour refaire un design, `--force` pour tout refaire.
- `fonts/` (Google Fonts), `icons/` (Tabler, MIT), `illustrations/<id>.png` (dessins faits avec Canva).
- `LANCEMENT-TSHIRTS.md` : la mission d'origine et les règles qui ne bougent jamais.

Pour fabriquer de nouveaux designs : suivre le skill `/tshirts` (`.claude/skills/tshirts/SKILL.md`).
Règles : aucune marque ni logo, pas de provoc sur l'origine / la religion / le handicap / l'orientation / le physique,
orthographe et accents parfaits.
