# Lancer « Zigoto & Cie » — ce que tu dois faire

Coche au fur et à mesure. Compte environ 2 heures en tout, réparties sur quelques jours
(Stripe peut mettre 1 à 2 jours à valider le compte).

## 1. M'envoyer par message (rien de secret)
Recopie-les depuis ton extrait Kbis (sur infogreffe.fr ou dans ton espace entreprise) :
- [ ] Forme juridique (SARL, SAS, EURL…) et capital social
- [ ] Adresse complète du siège
- [ ] SIREN (9 chiffres) et ville du RCS (sûrement Angers)
- [ ] Nom du gérant (il sera « directeur de la publication »)
- [ ] TVA : ta société facture-t-elle la TVA (20 %) ou est-elle en franchise de TVA ? + numéro de TVA intracommunautaire
- [ ] Livraison : **offerte** (comprise dans le prix) ou **forfait 4,90 €** ?
- [ ] OK ou pas pour le nom « Zigoto & Cie »

Discrétion : le site n'affiche rien sur les drones. Seule la raison sociale « LM DRONE » apparaît, en petit,
dans les mentions légales et les CGV (c'est obligatoire). Le client voit « Zigoto & Cie » partout,
y compris sur son relevé bancaire (réglage Stripe, étape 3).

## 2. Vérifier avec ton comptable (10 minutes)
- [ ] Que l'objet social de LM DRONE couvre bien la vente en ligne de vêtements. Sinon, c'est une modification
  simple de l'objet social. Mieux vaut l'avoir avant la première vente.
- [ ] Ton régime de TVA (il change le prix : la TVA est comprise dans le calcul).

## 3. Créer les comptes
### Cloudflare (hébergement gratuit + nom de domaine)
- [ ] Compte gratuit sur cloudflare.com
- [ ] Acheter le nom de domaine (idées : `zigoto-et-cie.fr`, `zigotoetcie.com`). Si Cloudflare ne propose pas
      l'extension voulue, prends-le chez OVH et je t'explique comment le brancher.
- [ ] Email gratuit `contact@ton-domaine` : *Email → Email Routing* → redirige vers ta boîte habituelle
      (comme ça, le site n'affiche pas l'email de LM Drone)
- [ ] Clé pour que je puisse publier le site : *Mon profil → API Tokens → Create Token → Custom token*,
      permission **Account · Cloudflare Pages · Edit**. Copie la clé et ton **Account ID**
      (colonne de droite de la page d'accueil du compte).

### Stripe (paiement par carte, Apple Pay, Google Pay)
- [ ] Compte au nom de LM DRONE : SIREN, IBAN pro, pièce d'identité du gérant
- [ ] *Paramètres → Informations publiques* : nom affiché **Zigoto & Cie**, libellé du relevé bancaire **ZIGOTO ET CIE**
- [ ] *Développeurs → Clés API* : copie la **clé secrète de test** (`sk_test_…`). La clé réelle (`sk_live_…`)
      viendra après le test. Option plus sûre : une **clé restreinte** avec seulement « Checkout Sessions : écriture ».
- [ ] Le webhook (`whsec_…`) : on le crée ensemble quand le site a son adresse.

### Printful (fabrication et livraison)
- [ ] Compte au nom de LM DRONE, avec une carte bancaire enregistrée (Printful débite le prix du t-shirt à chaque commande)
- [ ] *Stores → Add store → Manual order platform / API*, nom « Zigoto & Cie »
- [ ] Jeton privé sur https://developers.printful.com/tokens pour cette boutique (copie-le)
- [ ] Dans les réglages de la boutique Printful : nom « Zigoto & Cie » sur le bordereau d'expédition

### Médiateur de la consommation (obligatoire pour vendre aux particuliers)
- [ ] Adhérer à un médiateur agréé (par exemple CM2C ou Medicys, quelques dizaines d'euros par an) et me donner son nom et son site

### Facultatif
- [ ] Compte gratuit sur resend.com : clé API pour recevoir un email à chaque commande

## 4. Me donner les clés SANS les écrire dans un message
Dans l'app Claude : menu de l'environnement cloud (en haut de la session) → **Modifier** →
**Variables d'environnement** (ou « Network secrets »). Ajoute une ligne par clé, avec exactement ces noms :

| Nom | Valeur |
|---|---|
| `STRIPE_SECRET_KEY` | ta clé `sk_test_…` (puis la `sk_live_…` après le test) |
| `PRINTFUL_TOKEN` | le jeton Printful |
| `CLOUDFLARE_API_TOKEN` | la clé Cloudflare |
| `CLOUDFLARE_ACCOUNT_ID` | ton Account ID |
| `SITE_URL` | `https://ton-domaine` |
| `RESEND_API_KEY`, `EMAIL_MAXIME` | facultatif |

Dans la même page, **Accès réseau → Domaines autorisés**, ajoute :
`api.printful.com`, `api.stripe.com`, `*.cloudflare.com`, `*.canva.com`, `upload.wikimedia.org`.
Puis ouvre une nouvelle session et dis-moi « les clés sont prêtes ».

## 5. Ce que je fais ensuite (toi, tu valides seulement)
1. Je te montre 2-3 t-shirts Printful avec leur vrai prix de revient et le prix de vente calculé → tu choisis.
2. Je mets le site en ligne en mode test, je crée le webhook Stripe avec toi.
3. Paiement test avec la carte 4242 4242 4242 4242 → la commande doit apparaître en brouillon chez Printful.
4. Tu remplaces la clé de test par la clé réelle → le site est ouvert.
5. Tu choisis les t-shirts à vendre dans l'Excel (« À publier ») → `/publier` → aperçu → « publie ».
