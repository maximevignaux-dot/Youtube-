# Mission Claude Code n°2 — Le site boutique (sans Shopify)

> **Pour Maxime** : fais d'abord « Ce que tu fais toi » (environ 45 minutes, une seule fois). Ensuite, mets ce fichier dans le même dossier que `LANCEMENT-TSHIRTS.md`, ouvre Claude Code et écris :
> **« Lis SITE-BOUTIQUE.md et construis tout. »**

Le principe : Claude Code fabrique un site de vente simple et rapide. Le client paie par carte via Stripe, et la commande part toute seule chez Printful, qui imprime et livre. Pas d'abonnement Shopify.

**Coûts** : nom de domaine (environ 10 à 15 €/an), Stripe (commission par vente, pas d'abonnement), Printful (gratuit, tu paies le t-shirt à chaque commande), hébergement Cloudflare (gratuit, usage commercial autorisé).

---

## Ce que tu fais toi (une seule fois)

1. **Nom de domaine** : achète-le (chez Cloudflare directement, c'est le plus simple).
2. **Cloudflare** : crée un compte gratuit.
3. **Stripe** : crée le compte au nom de ta SARL (SIREN, IBAN pro). Récupère la **clé secrète** (`sk_live_…`, et `sk_test_…` pour les essais).
4. **Printful** : crée le compte, puis *Stores → Add store → **Manual order platform / API***. Ensuite, sur https://developers.printful.com/tokens, crée un jeton privé pour cette boutique.
5. Quand Claude Code te le demandera, colle les clés **dans le fichier `.env`**, jamais dans un message.
6. Prépare les infos des pages légales : raison sociale, adresse, SIREN, numéro de TVA, email de contact, nom du directeur de publication.

---

## Ton rôle (Claude Code)

Construis le site, son paiement et la publication automatique. Maxime ne code pas : explique simplement et ne pose une question que si la décision lui revient (nom de la boutique, couleurs, prix).

### 1. Préparer
- `.env` (exclu par `.gitignore`) avec : `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `PRINTFUL_TOKEN`, `SITE_URL`. Maxime remplit lui-même les valeurs.
- Installe Node.js (LTS) si besoin, puis `wrangler` (outil Cloudflare) ; `pip install requests python-dotenv`.
- Demande à Maxime le nom de la boutique et propose 3 idées si il n'en a pas (court, drôle, français, nom de domaine disponible).

### 2. Le t-shirt de base et le prix (avec Maxime)
- Avec l'API Printful (`GET /products`), propose 2 ou 3 t-shirts unisexes en coton imprimés en Europe, avec le prix de revient livré en France.
- Enregistre son choix et la correspondance couleur → variantes (noir, blanc, kaki, marine, sable, gris, ou la plus proche) dans `config_printful.json`.
- **Prix** : prix de revient livré + frais Stripe + 10 € de marge minimum, arrondi au ,90 supérieur. Montre le calcul et fais-le valider. Livraison : soit offerte (incluse dans le prix), soit un forfait fixe, au choix de Maxime.

### 3. Le site (dossier `site/`)
Site statique, très rapide, pensé **mobile d'abord** (90 % des clients arriveront depuis Facebook sur téléphone) :
- **Accueil** : accroche drôle, les t-shirts en grille, filtres par niche (Apéro, Pétanque, Métiers, Daron, Femmes…).
- **Fiche produit** (une page par t-shirt, adresse lisible : `/t-shirt/<id>`) : photos (mockups Printful), titre, description de `fiche-produit.md`, choix de la taille, guide des tailles, prix, gros bouton « Je le veux », mention « Idée cadeau ». C'est la page vers laquelle pointeront les vidéos : elle doit charger en moins de 2 secondes.
- **Panier** simple (stocké dans le navigateur) pour acheter plusieurs t-shirts.
- **Pages légales** : mentions légales, CGV (droit de rétractation de 14 jours, retours, délais), politique de confidentialité, contact. Rédige-les à partir des infos de la SARL.
- Style : sobre et chaleureux, qui met les t-shirts en avant. Pas de rose.
- Le site est généré par `build_site.py` à partir de `catalogue.json` : un t-shirt ajouté au catalogue = une page créée automatiquement.

### 4. Le paiement (fonctions Cloudflare dans `site/functions/`)
- `/api/checkout` : reçoit le panier, vérifie les prix **côté serveur** (jamais ceux envoyés par le navigateur), crée une session **Stripe Checkout** (carte, Apple Pay, Google Pay ; adresse de livraison France + UE ; email du client) et redirige vers Stripe.
- `/api/stripe-webhook` : sur `checkout.session.completed` (signature Stripe vérifiée), crée la commande Printful (`POST /orders`) avec l'adresse et les articles.
  - **Phase 1 (les 10 premières commandes)** : commande Printful créée **en brouillon** + email à Maxime. Il vérifie et confirme dans Printful.
  - **Phase 2** (quand Maxime le dit) : confirmation automatique (`confirm: true`).
- Pages « Merci pour ta commande » et « Paiement annulé ».
- Teste tout en mode test Stripe (carte 4242 4242 4242 4242) avant de passer en clés réelles.

### 5. Publier un t-shirt : `publish.py` et la commande `/publier`
Pour chaque ligne au statut **« À publier »** (ajoute ce statut et une colonne **« Style choisi »** dans `banque-slogans.xlsx`) :
1. Copie `sortie/<id>/impression_<style>.png` vers `site/f/<code aléatoire de 16 caractères>/<id>.png` (adresse publique mais introuvable sans le lien, nécessaire à Printful).
2. Crée le produit dans Printful (`POST /store/products`) : une variante par taille (S à 3XL) dans la bonne couleur, impression **dans le dos** avec ce fichier. Respecte la limite de requêtes Printful (attends entre deux appels).
3. Génère les photos du t-shirt avec le générateur de mockups Printful et enregistre-les dans `site/img/<id>/`.
4. Ajoute le t-shirt à `catalogue.json` (id, titre, description, prix, tailles avec leur `sync_variant_id`, photos, niche) avec `"visible": false`.
5. Reconstruit le site, le déploie (`wrangler pages deploy`) et donne à Maxime le lien de prévisualisation.
6. Quand Maxime dit **« publie »** : passe le t-shirt en `"visible": true`, redéploie, met la ligne en « En ligne », et donne le lien de la fiche produit à mettre sous les vidéos.

Crée `.claude/skills/publier/SKILL.md` qui décrit ce circuit.

### 6. Plus tard (ne pas faire maintenant, juste prévoir la place)
- **Pixel Meta + bandeau cookies** : à ajouter avant de lancer des pubs payantes (consentement obligatoire).
- **Etsy** : relier Etsy dans Printful et y pousser les meilleurs t-shirts depuis le tableau de bord Printful.
- **Suivi des ventes** : `/ventes` qui résume les commandes Stripe de la semaine et les t-shirts qui vendent.

### Sécurités
- Clés uniquement dans `.env`, jamais affichées ni copiées ailleurs.
- Les prix sont toujours recalculés côté serveur.
- Toute modification du site passe par une prévisualisation avant la mise en ligne.

---

## Le circuit complet, une fois tout en place
1. Slogans en « Validé » → `/tshirts` → designs prêts.
2. Style choisi + statut « À publier » → `/publier` → t-shirt en prévisualisation sur ton site, relié à Printful.
3. « publie » → en vente, avec le lien à mettre sous la vidéo.
4. Un client paie → Printful imprime et livre → l'argent arrive sur ton compte Stripe.
