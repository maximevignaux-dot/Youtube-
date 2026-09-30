import React from 'react';
import {Composition, Folder} from 'remotion';
import {
  CartonPiece,
  CompteurBillets,
  DocumentCaviarde,
  FichePersonnage,
  GrainVignette,
  MotCle,
  OuvertureDossier,
  PhotoKenBurns,
} from './components';
import {DemoCastel, DUREE_DEMO_CASTEL} from './demos/DemoCastel';
import {FPS, HAUTEUR, LARGEUR} from './theme/palette';

const avecGrain = (C: React.FC) => () => (
  <>
    <C />
    <GrainVignette />
  </>
);

// Galerie : chaque composant seul, pour valider le style dans le Studio.
const galerie: Array<[string, number, React.FC]> = [
  ['OuvertureDossier', 110, () => <OuvertureDossier numero={1} titre="Castel" sousTitre="L'empire discret" />],
  [
    'FichePersonnage',
    150,
    () => (
      <FichePersonnage
        slug="demo"
        sceneId="S000"
        descriptionPhoto="Portrait de la personne"
        nom="Gilbert Chikli"
        role="Escroc (arnaque au faux président)"
        fortune="Plusieurs dizaines de M€ détournés"
        statut="Condamné par la justice française"
        tampon="CONDAMNÉ"
      />
    ),
  ],
  ['CompteurBillets-gain', 90, () => <CompteurBillets montant={80_000_000} libelle="BUTIN ESTIMÉ" />],
  ['CompteurBillets-perte', 90, () => <CompteurBillets montant={5_000_000} sens="perte" libelle="PERTE DE L'ENTREPRISE" />],
  [
    'DocumentCaviarde',
    120,
    () => (
      <DocumentCaviarde
        entete="ORDRE DE VIREMENT"
        tampon="URGENT"
        lignes={[
          {texte: 'DONNEUR D\u2019ORDRE : LE PRÉSIDENT'},
          {texte: 'MONTANT : 5 000 000 €', caviarde: true, revelerA: 30, surligner: true},
          {texte: 'DESTINATION : HONG KONG', caviarde: true, revelerA: 60},
          {texte: 'MOTIF : OPÉRATION CONFIDENTIELLE'},
        ]}
      />
    ),
  ],
  ['MotCle', 60, () => <MotCle texte="Évidemment que non." fond="noir" />],
  ['MotCle-surligne', 60, () => <MotCle texte="Personne n'a rien vu." surligne fond="noir" />],
  ['PhotoKenBurns-placeholder', 120, () => <PhotoKenBurns slug="demo" sceneId="S027" description="Façade du tribunal de Paris, plan large de jour" legende="Paris, 2015" />],
  ['CartonPiece', 75, () => <CartonPiece numero={2} titre="L'arnaque" />],
];

export const Racine: React.FC = () => (
  <>
    <Composition id="DemoCastel" component={DemoCastel} durationInFrames={DUREE_DEMO_CASTEL} fps={FPS} width={LARGEUR} height={HAUTEUR} />
    <Folder name="Galerie">
      {galerie.map(([id, duree, C]) => (
        <Composition key={id} id={id} component={avecGrain(C)} durationInFrames={duree} fps={FPS} width={LARGEUR} height={HAUTEUR} />
      ))}
    </Folder>
  </>
);
