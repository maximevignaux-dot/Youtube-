# DOSSIERS — pipeline vidéo

Chaîne YouTube « DOSSIERS » : les coulisses de l'argent. Montage automatique avec Remotion.

- Le cahier des charges complet : [CLAUDE.md](CLAUDE.md)
- Installer sur ton ordinateur : [INSTALLATION.md](INSTALLATION.md)
- Utilisation au quotidien : [DEMARRAGE.md](DEMARRAGE.md)

## Où en est-on
- [x] Session 1 — fondations : palette, polices, grain + vignettage, sons provisoires,
      composants OuvertureDossier, FichePersonnage, CompteurBillets, DocumentCaviarde,
      MotCle, PhotoKenBurns (+ placeholders), CartonPiece, Flash ; démo de 30 s (`DemoCastel`).
- [x] Session 2 — chaîne complète (`npm run video <slug>`) : lecture du script et de a-chercher.md,
      voix test au mot près, découpage automatique, cartes, tableau d'enquête, graphiques, frises,
      chiffres, musique avec ducking, recherche auto des visuels, shotlist.html, chapitres, crédits.
- [x] Session 3 — `npm run revoice` (ta voix, ratés retirés, montage recalé), `npm run final`
      (1080p, contrôles licences, miniatures), `npm run shorts` (9:16, sous-titres mot à mot), effet 2,5D.
- 👉 Au quotidien : [MODE-EMPLOI.md](MODE-EMPLOI.md)

## Organisation
```
src/theme/         palette + polices
src/components/    composants du style maison
src/demos/         démo du hook Castel
scripts/           voix test (edge-tts), sons provisoires, préparation de public/
polices/ sfx/ musique/ mes-rushs/
videos/<slug>/     script.md, voix, assets/…
```
