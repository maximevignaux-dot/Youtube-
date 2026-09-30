# DOSSIERS — pipeline vidéo

Chaîne YouTube « DOSSIERS » : les coulisses de l'argent. Montage automatique avec Remotion.

- Le cahier des charges complet : [CLAUDE.md](CLAUDE.md)
- Installer sur ton ordinateur : [DEMARRAGE.md](DEMARRAGE.md)

## Où en est-on
- [x] Session 1 — fondations : palette, polices, grain + vignettage, sons provisoires,
      composants OuvertureDossier, FichePersonnage, CompteurBillets, DocumentCaviarde,
      MotCle, PhotoKenBurns (+ placeholders), CartonPiece, Flash ; démo de 30 s (`DemoCastel`).
- [ ] Session 2 — chaîne complète (`npm run video <slug>`)
- [ ] Session 3 — `revoice`, `final`, `shorts`, miniatures

## Organisation
```
src/theme/         palette + polices
src/components/    composants du style maison
src/demos/         démo du hook Castel
scripts/           voix test (edge-tts), sons provisoires, préparation de public/
polices/ sfx/ musique/ mes-rushs/
videos/<slug>/     script.md, voix, assets/…
```
