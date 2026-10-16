---
name: publier
description: Met en vente les t-shirts au statut « À publier » de banque-slogans.xlsx sur le site boutique (Printful + Stripe + Cloudflare) : aperçu d'abord, vente seulement quand Maxime dit « publie ».
argument-hint: "[optionnel : publie <id> | publie tout]"
---

# /publier — du design au t-shirt en vente

Maxime ne code pas : lance les commandes toi-même, résume en français simple.

## Avant la toute première fois (vérifier, ne refaire que ce qui manque)
1. `.env` rempli par Maxime (STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, PRINTFUL_TOKEN, SITE_URL). Ne jamais afficher ni copier ces valeurs.
2. `config_printful.json` existe : sinon `python3 choisir_tshirt.py` → `--comparer <ids>` → montrer le calcul du prix à Maxime → `--choisir <id>` quand il a validé.
3. `boutique.json` complet (nom, SARL, médiateur…) : `python3 build_site.py --prod` refuse sinon, et dit ce qui manque.
4. Cloudflare : `cd site && npx wrangler login` (Maxime clique « Autoriser »), projet créé une fois avec
   `npx wrangler pages project create boutique --production-branch main`, puis `python3 publish.py secrets`.
5. Stripe : webhook vers `https://<domaine>/api/stripe-webhook`, événement `checkout.session.completed` ; sa clé `whsec_…` dans `.env`, puis `python3 publish.py secrets`.
6. Test complet en clés `sk_test_` : carte 4242 4242 4242 4242, n'importe quelle date future, n'importe quel code → la commande doit apparaître en brouillon dans Printful.

## Publier
1. Dans `banque-slogans.xlsx` : lignes au statut « À publier » avec « Style choisi » et « ID design » remplis.
   S'il n'y en a aucune, dis-le en une phrase et arrête-toi.
2. `python3 publish.py --test` d'abord si c'est la première fois ou si quelque chose a changé, puis `python3 publish.py`.
   Un t-shirt en erreur est sauté (explique l'erreur simplement), les autres continuent.
   Un design avec `ATTENTION-BASSE-DEF.txt` est refusé : il faut l'illustration HD de Canva.
3. Montre le résumé : titre, prix, lien d'aperçu de chaque fiche (`https://apercu.<projet>.pages.dev/t-shirt/<id>/`).
   Les lignes passent en « En aperçu ».

## Quand Maxime dit « publie »
`python3 publish.py publie tout` (ou `publie <id>`) → t-shirts visibles, site mis en ligne, lignes en « En ligne ».
Donne-lui les liens des fiches produit à mettre sous les vidéos.

## Commandes clients
- Phase 1 (par défaut, les 10 premières commandes) : `PRINTFUL_AUTO_CONFIRM=0` → chaque commande payée arrive
  en BROUILLON dans Printful ; Maxime vérifie et clique « Confirmer ».
- Phase 2, quand Maxime le demande : `PRINTFUL_AUTO_CONFIRM=1` dans `.env`, puis `python3 publish.py secrets`
  et `python3 publish.py publie tout` (redéploiement pour prendre le réglage).

## Règles
- Prix toujours recalculés côté serveur (site/functions) à partir de catalogue.json : ne jamais faire confiance au navigateur.
- Toute modification du site passe par l'aperçu avant la mise en ligne.
- Tests des fonctions de paiement : `cd site && npm test`.
