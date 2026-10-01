import React from 'react';
import {Composition, Folder} from 'remotion';
import {
  CarteFlux,
  CartonPiece,
  ChiffreCle,
  CompteurBillets,
  DocumentCaviarde,
  FichePersonnage,
  GrainVignette,
  GraphiqueAnime,
  Media,
  MotCle,
  OuvertureDossier,
  TableauEnquete,
  TimelineMachine,
} from './components';
import {FPS, HAUTEUR, LARGEUR} from './theme/palette';
import {calculerMetadonnees, Video} from './Video';

const avecGrain = (C: React.FC) => () => (
  <>
    <C />
    <GrainVignette />
  </>
);

// Galerie : chaque composant seul, pour régler le style dans le Studio.
const galerie: Array<[string, number, React.FC]> = [
  ['OuvertureDossier', 110, () => <OuvertureDossier numero={1} titre="Pierre Castel" sousTitre="Le milliardaire qui s'appelait Jésus" />],
  [
    'FichePersonnage',
    180,
    () => (
      <FichePersonnage
        assetId="S000"
        descriptionPhoto="Portrait de la personne"
        nom="Gilbert Chikli"
        champs={[
          {label: 'RÔLE', valeur: 'Escroc (arnaque au faux président)'},
          {label: 'DÉTAIL', valeur: 'Condamné par la justice française'},
        ]}
        tampon="CONDAMNÉ"
      />
    ),
  ],
  ['CompteurBillets', 100, () => <CompteurBillets montant={410_000_000} devise="CHF" sens="perte" />],
  ['ChiffreCle', 120, () => <ChiffreCle items={[{valeur: 22, texte: '22', unite: 'PAYS', aMs: 0}, {valeur: 61, texte: '61', unite: 'MARQUES', aMs: 900}, {valeur: 43000, texte: '43 000', unite: 'SALARIÉS', aMs: 1800}]} />],
  [
    'DocumentCaviarde',
    150,
    () => (
      <DocumentCaviarde
        entete="ORDRE DE VIREMENT"
        tampon="CONFIDENTIEL"
        lignes={[
          {texte: 'Donneur d’ordre : le président.'},
          {texte: 'Montant : 5 000 000 €.', caviarde: true, revelerAMs: 1000, surligner: true},
          {texte: 'Destination : Hong Kong.', caviarde: true, revelerAMs: 2200},
        ]}
      />
    ),
  ],
  ['TimelineMachine', 75, () => <TimelineMachine date="1990" precedentes={['1926', '1947', '1949', '1965']} />],
  [
    'CarteFlux',
    180,
    () => (
      <CarteFlux
        points={[{nom: 'Bordeaux', lon: -0.58, lat: 44.84}, {nom: '', lon: -17.47, lat: 14.72, secondaire: true}, {nom: '', lon: 9.7, lat: 4.05, secondaire: true}]}
        flux={[[0, 1], [0, 2]]}
        pays={[{nom: 'Cameroon', aMs: 1500, clic: true}, {nom: 'Senegal', aMs: 2200, clic: true}, {nom: "Côte d'Ivoire", aMs: 2900, clic: true}]}
        regions={['afrique']}
      />
    ),
  ],
  [
    'TableauEnquete',
    150,
    () => (
      <TableauEnquete
        centres={['CASTEL']}
        elements={[
          {label: 'POPULATION JEUNE'},
          {label: 'CONSO QUOTIDIENNE'},
          {label: 'IMPOSSIBLE À IMPORTER', nouveau: true, filRouge: true},
        ]}
        mode="ajout"
      />
    ),
  ],
  ['GraphiqueAnime', 120, () => <GraphiqueAnime barres={[{label: 'AVANT', valeur: 43, texte: '43 M€'}, {label: 'APRÈS', valeur: 350, texte: '350 M€'}]} />],
  ['MotCle', 60, () => <MotCle texte="Trop clémente." surligne fond="noir" />],
  ['Media-placeholder', 120, () => <Media assetId="V01" genre="video" description="Genève de nuit, vue sur le lac et le jet d'eau" />],
  ['CartonPiece', 80, () => <CartonPiece numero={2} titre="L'empire africain" />],
];

export const Racine: React.FC = () => (
  <>
    <Composition
      id="Video"
      component={Video}
      calculateMetadata={calculerMetadonnees}
      defaultProps={{slug: 'castel', apercu: false, plan: null}}
      durationInFrames={300}
      fps={FPS}
      width={LARGEUR}
      height={HAUTEUR}
    />
    <Folder name="Galerie">
      {galerie.map(([id, duree, C]) => (
        <Composition key={id} id={id} component={avecGrain(C)} durationInFrames={duree} fps={FPS} width={LARGEUR} height={HAUTEUR} />
      ))}
    </Folder>
  </>
);
