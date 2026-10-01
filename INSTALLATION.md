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

Whisper (transcription de ta voix) et rembg (détourage) seront installés à la session 2.

## 2. Récupérer le projet

```
git clone https://github.com/maximevignaux-dot/Youtube-.git
cd Youtube-
npm install
```
`npm install` télécharge Remotion (quelques minutes la première fois).

## 3. Voir la démo de style

```
npm run voix:demo
npm run studio
```
- `voix:demo` fabrique la voix test du hook de `videos/castel/script.md` (voix Henri, Microsoft).
- `studio` ouvre le **Remotion Studio** dans ton navigateur. À gauche : `DemoCastel`
  (la démo de 30 s) et le dossier **Galerie** (chaque élément du style maison, seul).

Pour sortir le fichier vidéo : `npm run demo` → `videos/castel/demo-hook.mp4`.

## Si quelque chose coince
Copie le message d'erreur et colle-le à Claude Code : « J'ai cette erreur : … ».
