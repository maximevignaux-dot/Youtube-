import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import {
  CartonPiece,
  CompteurBillets,
  DocumentCaviarde,
  FichePersonnage,
  Flash,
  FiligraneVoixTest,
  GrainVignette,
  MotCle,
  OuvertureDossier,
  PhotoKenBurns,
  Son,
} from '../components';
import {curseurDeMots, Horodatage, msEnFrames, secondes} from '../lib/temps';
import horodatage from '../../videos/castel/voix-test.mots.json';

const SLUG = 'castel';
const h = horodatage as Horodatage;
const AVANCE = 2; // la coupe tombe 2 frames avant le mot : ça paraît plus nerveux

// Toutes les coupes sont calées sur les mots de la voix : si la voix change, le montage suit.
const mot = curseurDeMots(h);
const t = {
  bordeaux: mot('Bordeaux'),
  annee: mot('1949'),
  jeune: mot('jeune'),
  freres: mot('frères'),
  soixante: mot('Soixante'),
  centaines: mot('centaines'),
  vins: mot('vins'),
  bieres: mot('bières'),
  sodas: mot('sodas'),
  paris: mot('Paris'),
  fortune: mot('fortune'),
  plus: mot('Plus'),
  largement: mot('Largement'),
  pourtant: mot('pourtant'),
  pierre: mot('Pierre'),
  tres: mot('Très'),
  ouvre: mot('ouvre'),
  dossier: mot('dossier'),
};
const finVoix = msEnFrames(h.dureeMs);
const finDossier = finVoix + secondes(2.6);
export const DUREE_DEMO_CASTEL = finDossier + secondes(2.8);

/** Plan de montage : [début, fin, contenu]. */
const plans: Array<[number, number, React.ReactNode]> = [
  [0, t.annee, <PhotoKenBurns slug={SLUG} sceneId="S001" description="Quais de Bordeaux, photo d'archive noir et blanc (années 1940-50)" legende="Bordeaux, Gironde" />],
  [t.annee, t.jeune, <MotCle texte="1949" fond="noir" taille={260} />],
  [t.jeune, t.freres, <PhotoKenBurns slug={SLUG} sceneId="S003" description="Jeune homme dans un chai à barriques, ambiance années 1950 (visage non identifiable)" mouvement="droite" />],
  [t.freres, t.soixante, <PhotoKenBurns slug={SLUG} sceneId="S004" description="Photo de famille d'époque devant un domaine viticole bordelais" mouvement="zoom-arriere" />],
  [t.soixante, t.vins, <PhotoKenBurns slug={SLUG} sceneId="S005" description="VIDÉO : chaîne d'embouteillage, des milliers de bouteilles qui défilent" />],
  [t.vins, t.bieres, <PhotoKenBurns slug={SLUG} sceneId="S007" description="Rayon de bouteilles de vin rouge, lumière chaude" mouvement="gauche" />],
  [t.bieres, t.sodas, <PhotoKenBurns slug={SLUG} sceneId="S008" description="Bouteilles de bière sur la chaîne d'une brasserie" mouvement="droite" />],
  [t.sodas, t.paris, <PhotoKenBurns slug={SLUG} sceneId="S009" description="Bouteilles de soda colorées alignées" />],
  [t.paris, t.fortune, <PhotoKenBurns slug={SLUG} sceneId="S010" description="CARTE (auto, session 2) : flux Paris → Afrique de l'Ouest et centrale" mouvement="zoom-arriere" />],
  [t.fortune, t.largement, <CompteurBillets montant={1_000_000_000} prefixe="+ DE" libelle="SA FORTUNE ?" debutComptage={t.plus - t.fortune} dureeComptage={40} />],
  [t.largement, t.pourtant, <MotCle texte="Largement plus." surligne taille={210} fond="noir" />],
  [
    t.pourtant,
    t.tres,
    <DocumentCaviarde
      entete="FICHE D'IDENTIFICATION"
      tampon="CONFIDENTIEL"
      lignes={[
        {texte: 'NOM : PIERRE CASTEL', caviarde: true, revelerA: t.pierre - t.pourtant - AVANCE, surligner: true},
        {texte: 'NÉ EN : 1926', caviarde: true},
        {texte: 'SECTEUR : VINS, BIÈRES, SODAS'},
        {texte: 'RÉSIDENCE : GENÈVE (SUISSE)', caviarde: true},
      ]}
    />,
  ],
  [
    t.tres,
    t.ouvre,
    <FichePersonnage
      slug={SLUG}
      sceneId="S014"
      descriptionPhoto="Portrait de Pierre Castel (Wikimedia Commons ou espace presse)"
      nom="Pierre Castel"
      role="Fondateur du groupe Castel"
      fortune="+ d'1 milliard d'€ (est.)"
      statut="Très discret"
      tampon="MILLIARDAIRE"
      couleurTampon="#1F8A5B"
      lettresParSeconde={45}
    />,
  ],
  [t.ouvre, finDossier, <OuvertureDossier numero={1} titre="Castel" sousTitre="L'empire discret" frappe={t.dossier - t.ouvre} ouverture={t.dossier - t.ouvre + 22} />],
  [finDossier, DUREE_DEMO_CASTEL, <CartonPiece numero={1} titre="Le vigneron" />],
];

export const DemoCastel: React.FC = () => (
  <AbsoluteFill style={{background: '#0D0D0D'}}>
    {plans.map(([debut, fin, contenu], i) => {
      const d = Math.max(0, debut - (i === 0 ? 0 : AVANCE));
      return (
        <Sequence key={i} from={d} durationInFrames={Math.max(1, fin - AVANCE - d)}>
          {contenu}
        </Sequence>
      );
    })}
    {/* mot-clé par-dessus la chaîne d'embouteillage */}
    <Sequence from={t.centaines - AVANCE} durationInFrames={t.vins - t.centaines}>
      <MotCle texte="Des centaines de millions" taille={150} fond="assombri" />
    </Sequence>
    {/* flashs sur les changements de lieu */}
    {[t.vins, t.paris].map((f) => (
      <Sequence key={f} from={f - AVANCE - 3} durationInFrames={12}>
        <Flash />
      </Sequence>
    ))}
    <Audio src={staticFile(`videos/${SLUG}/voix-test.mp3`)} />
    <Son nom="nappe" volume={0.22} boucle />
    <GrainVignette />
    <FiligraneVoixTest />
  </AbsoluteFill>
);
