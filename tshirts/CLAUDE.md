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

## Site boutique (Stripe + Printful + Cloudflare, sans Shopify)
- `build_site.py` fabrique `site/public/` depuis `catalogue.json` + `boutique.json` (`--demo` : tous les designs, `--prod` : en ligne).
- `site/functions/api/` : paiement Stripe (`checkout.js`) et commande Printful après paiement (`stripe-webhook.js`). Tests : `cd site && npm test`.
- `choisir_tshirt.py` : t-shirt de base + prix (TVA, Stripe et 10 € de marge minimum inclus). `publish.py` : mise en vente.
- Commande `/publier` : `.claude/skills/publier/SKILL.md`. Mission d'origine : `SITE-BOUTIQUE.md`.
