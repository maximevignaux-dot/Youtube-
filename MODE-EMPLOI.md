# MODE D'EMPLOI — chaîne DOSSIERS

Tu ouvres Claude Code dans le dossier du projet, puis tu tapes **une de ces phrases**.
Claude s'occupe de tout le reste.

---

### 📝 Tester un nouveau script (sans enregistrer ta voix)
> **Nouvelle vidéo : [colle ton script ici]**

Tu reçois : `apercu.mp4` (voix test + filigrane) et `shotlist.html` (les images à trouver).

### 🖼️ Tu as trouvé des images ou des vidéos
Dépose-les dans `videos/<nom>/assets/` avec le nom de la shotlist (ex. `V01.mp4`, `S012.jpg`), puis :
> **J'ai ajouté des images pour <nom>, relance l'aperçu.**

Et note d'où vient chaque fichier dans `videos/<nom>/assets/sources.txt` :
`V01 | Pexels | Jean Dupont | Licence Pexels` (sinon le rendu final est bloqué).

### ✏️ Tu as modifié ton script
> **J'ai modifié le script de <nom>, refais l'aperçu.**

### 🎙️ Tu as enregistré ta voix
Dépose ton fichier sous le nom `voix.mp3` dans `videos/<nom>/`, puis :
> **Ma voix est prête pour <nom>.**

Tu te trompes en lisant ? Marque une pause et relis la phrase depuis le début : la mauvaise prise est retirée toute seule.
Claude te dit ensuite quelles phrases tu as sautées ou changées.

### 🎬 Sortir la vidéo à publier
> **Fais le rendu final de <nom>.**

Tu reçois : `sortie.mp4` (1080p), `chapitres.txt` et `credits.txt` (à coller dans la description YouTube),
`miniature-1.jpg`, `-2`, `-3` (3 miniatures à tester).

### 📱 Faire les Shorts
Entoure les passages dans ton script avec `[SHORT début]` et `[SHORT fin]` (45 à 60 s chacun), puis :
> **Fais les Shorts de <nom>.**

### 💡 Écrire un script à partir de la liste d'idées
> **Écris le script de l'idée 007 de idees-videos.md, avec les balises et les sources vérifiées.**

### 🛠️ Changer le style
> **Sur l'aperçu de <nom>, à 3:25 le tampon est trop petit / la carte va trop vite / …**

### 🆘 Ça ne marche pas
> **J'ai cette erreur : [colle le message]**

---

**Balises utiles dans un script** (jamais lues à voix haute) :
`[CHIFFRE 80 M€]` · `[COMPTEUR 410 000 000 CHF, rouge]` · `[FICHE Nom | Rôle | STATUT]` · `[CARTE Paris→Genève]` ·
`[DOCUMENT "titre" caviardé]` · `[TABLEAU ajouter "X", fil rouge]` · `[GRAPH barres 43 M€ → 350 M€]` ·
`[TIMELINE 1990]` · `[MOT "JÉSUS"]` · `[TAMPON "CLASSÉ SANS SUITE"]` · `[PHOTO …]` · `[VIDEO …]` ·
`[PIECE 2 "Le titre"]` · `[PAUSE 1s]` · `[SHORT début]` / `[SHORT fin]`
