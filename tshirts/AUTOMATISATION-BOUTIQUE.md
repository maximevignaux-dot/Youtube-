# Mission Claude Code n°2 — Publication automatique Shopify + Printful

> **Pour Maxime** : fais d'abord la partie « Ce que tu fais toi » (environ 30 minutes, une seule fois). Ensuite, mets ce fichier dans le même dossier que `LANCEMENT-TSHIRTS.md`, ouvre Claude Code et écris :
> **« Lis AUTOMATISATION-BOUTIQUE.md et construis tout. »**

---

## Ce que tu fais toi (une seule fois)

1. **Shopify** : crée la boutique (avec ta SARL : mentions légales, CGV, droit de rétractation de 14 jours, TVA).
2. **Printful** : crée le compte, puis *Stores → Add store → Shopify* pour relier les deux. Dans les réglages de la boutique Printful, active **« Import not synced products »**.
3. **Clé Shopify** : dans Shopify, *Paramètres → Applications → Développer des applications → Créer une application*. Donne-lui les accès `write_products`, `read_products`, `write_files`, `read_files`, puis installe-la et copie le **jeton d'accès Admin API** (il commence par `shpat_`).
4. **Clé Printful** : sur https://developers.printful.com/tokens, crée un jeton privé avec accès à ta boutique et copie-le.
5. Quand Claude Code te le demandera, colle ces deux jetons **dans le fichier `.env` qu'il aura créé**, jamais dans un message ou un autre fichier.

---

## Ton rôle (Claude Code)

Construis `publish.py`, qui met en vente automatiquement les t-shirts prêts. Maxime ne code pas : explique en français simple, pose une question seulement quand une décision lui revient.

### 1. Préparer
- Crée `.env` (avec `SHOPIFY_STORE=nom-boutique.myshopify.com`, `SHOPIFY_TOKEN=`, `PRINTFUL_TOKEN=`) et un `.gitignore` qui l'exclut. Demande à Maxime de remplir les jetons lui-même dans `.env`.
- `pip install requests python-dotenv`.
- Dans `banque-slogans.xlsx` : ajoute la colonne **« Style choisi »** (liste : `empile, mix, badge, retro, fiche, illustre`) et le statut **« À publier »** dans la liste des statuts.

### 2. Choisir le t-shirt de base, avec Maxime
- Interroge le catalogue Printful (`GET https://api.printful.com/products`) et propose à Maxime 2 ou 3 t-shirts unisexes en coton, imprimés en Europe, avec leur prix de revient en France (produit + livraison).
- Une fois qu'il a choisi, enregistre l'identifiant produit Printful et la correspondance couleur → identifiants de variantes (pour les couleurs `noir`, `blanc`, `kaki`, `marine`, `sable`, `gris`, ou la plus proche) dans `config_printful.json`.
- **Prix** : prix de revient livré + 10 € de marge minimum, arrondi au ,90 supérieur. Montre le calcul à Maxime une fois et fais-le valider.

### 3. Ce que fait `publish.py` pour chaque ligne au statut « À publier »
1. Prend `sortie/<id>/impression_<style choisi>.png` et les textes de `sortie/<id>/fiche-produit.md`.
2. Envoie le fichier d'impression dans **Shopify Files** (`stagedUploadsCreate` puis `fileCreate`, API GraphQL Admin) pour obtenir une adresse publique.
3. Crée le produit dans Shopify **en brouillon** : titre, description, tags, une variante par taille (S à 3XL) dans la couleur du design, au prix validé.
4. Attend que Printful importe le produit (vérifie toutes les 30 s pendant 10 min max avec `GET /sync/products`).
5. Relie chaque variante avec `PUT /sync/variant/{id}` : `variant_id` du catalogue Printful (bonne taille et couleur) et `files: [{"type": "back", "url": "<adresse Shopify Files>"}]` (impression **dans le dos**, comme sur les vidéos ; ajoute en option un petit logo devant plus tard). Limite Printful : 10 requêtes par minute, donc attends entre deux appels.
6. Génère les vraies photos du t-shirt avec le générateur de mockups Printful (`POST /mockup-generator/create-task/{product_id}`, puis récupère le résultat) et ajoute-les comme images du produit Shopify, avec `apercu_<style>.jpg` en secours.
7. Passe la ligne au statut « En ligne (brouillon) » et note le lien d'administration du produit.

### 4. Sécurités
- **Toujours en brouillon.** Le produit ne passe en vente que quand Maxime dit « publie » : alors seulement, mets-le en `ACTIVE`.
- Mode test : `python3 publish.py --test <id>` fait tout sauf l'écriture chez Shopify et Printful, et affiche ce qui serait envoyé.
- Si une étape échoue, arrête-toi sur ce t-shirt, explique l'erreur simplement, et passe au suivant.
- Ne jamais afficher, copier ou envoyer les jetons ailleurs que dans les appels aux API.

### 5. La commande `/publier`
Crée `.claude/skills/publier/SKILL.md` : « Lance `publish.py` sur les lignes "À publier", montre le résumé (titres, prix, liens brouillons), et, si Maxime répond "publie", passe ces produits en vente. »

### 6. Etsy (plus tard)
Ne pas automatiser Etsy pour l'instant : l'API Etsy demande une validation d'application, et rien ne garantit que la synchronisation Printful fonctionne pareil. Quand Shopify tourne, Maxime pourra relier Etsy dans Printful et y pousser ses meilleurs produits depuis le tableau de bord Printful.

---

## Le circuit complet, une fois tout en place
1. Maxime passe des slogans en « Validé » → `/tshirts` → les designs sont prêts.
2. Il choisit un style dans la colonne « Style choisi » et passe la ligne en « À publier » → `/publier` → les produits sont en brouillon sur Shopify, reliés à Printful, avec photos.
3. Il vérifie, dit « publie » → en vente.
4. Il fait les vidéos (photos IA + `make_video.py`) et les publie.
