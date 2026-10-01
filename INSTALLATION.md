# Démarrage — installer le pipeline sur ton ordinateur

Tu n'as à faire ça **qu'une seule fois**. Copie-colle chaque ligne dans un terminal
(sur Mac : app « Terminal » ; sur Windows : « PowerShell »), puis appuie sur Entrée.

## 1. Installer les outils (une fois pour toutes)

| Outil | À quoi il sert | Comment l'installer |
|---|---|---|
| **Node.js** (v20 ou +) | fait tourner Remotion, le logiciel de montage | télécharger « LTS » sur https://nodejs.org |
| **Python** (3.10 ou +) | petits utilitaires (voix, transcription) | https://www.python.org/downloads (Windows : cocher « Add to PATH ») |
| **ffmpeg** | découpe et convertit l'audio / la vidéo | Mac : `brew install ffmpeg` · Windows : `winget install ffmpeg` |
| **edge-tts** | la voix test gratuite | `pip install edge-tts` |

Vérifier que tout est là (chaque commande doit afficher un numéro de version) :
```
node -v
python --version
ffmpeg -version
edge-tts --version
```

Pour ta vraie voix et le détourage des photos (une fois, ça télécharge environ 1 Go la première fois qu'ils servent) :
```
pip install faster-whisper "rembg[cpu]"
```

## 2. Récupérer le projet

```
git clone https://github.com/maximevignaux-dot/Youtube-.git
cd Youtube-
npm install
```
`npm install` télécharge Remotion (quelques minutes la première fois).

## 3. Les clés gratuites pour les images (5 min, une seule fois)

1. Crée un compte sur https://www.pexels.com/api/ → copie ta clé.
2. Crée un compte sur https://pixabay.com/api/docs/ → ta clé s'affiche dans la page une fois connecté.
3. Dans le dossier du projet, copie le fichier `.env.exemple` et renomme la copie en `.env`.
4. Ouvre `.env` avec le Bloc-notes et colle tes clés après les signes `=`.

Sans ces clés, tout marche quand même : les images manquantes restent des cartons « à fournir ».

## 4. Fabriquer l'aperçu du dossier Castel

```
npm run video castel
```
Ça fait tout, dans l'ordre : voix test → découpage en scènes → recherche des images →
shotlist → vidéo d'aperçu. Compte 15 à 30 minutes la première fois.

Résultat dans `videos/castel/` :
- `apercu.mp4` : la vidéo complète en 720p (avec le filigrane VOIX TEST)
- `shotlist.html` : ouvre-le dans ton navigateur (ou sur ton téléphone) : la liste des visuels à trouver
- `chapitres.txt` et `credits.txt` : à coller dans la description YouTube

Pour regarder et naviguer scène par scène : `npm run studio` puis clique sur `Video` à gauche.

## Si quelque chose coince
Copie le message d'erreur et colle-le à Claude Code : « J'ai cette erreur : … ».
