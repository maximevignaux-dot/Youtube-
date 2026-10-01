import React from 'react';
import {AbsoluteFill, Audio, CalculateMetadataFunction, getStaticFiles, Sequence, staticFile} from 'remotion';
import {
  CarteFlux,
  CartonPiece,
  ChiffreCle,
  ChiffreIncruste,
  Citation,
  CompteurBillets,
  DateIncruste,
  DocumentCaviarde,
  FichePersonnage,
  FiligraneVoixTest,
  Flash,
  GrainVignette,
  GraphiqueAnime,
  Media,
  MotCle,
  OuvertureDossier,
  Schema,
  TableauEnquete,
  TamponCalque,
  Teaser,
  TimelineMachine,
} from './components';
import {ContexteVideo, ms} from './lib/contexte';
import {FPS, HAUTEUR, LARGEUR} from './theme/palette';

type Scene = {composant: string; debutMs: number; finMs: number; props: Record<string, unknown>};
export type Plan = {
  slug: string;
  voix: {fichier: string; test: boolean; motsFichier?: string};
  dureeMs: number;
  fond: Scene[];
  calques: Scene[];
  parole: [number, number][];
  silences: [number, number][];
  sections: {nom: string; debutMs: number; piece: number | null}[];
};
export type PropsVideo = {slug: string; apercu: boolean; plan?: Plan | null};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const COMPOSANTS: Record<string, React.FC<any>> = {
  Media, FichePersonnage, DocumentCaviarde, CompteurBillets, ChiffreCle, TimelineMachine, CarteFlux, TableauEnquete,
  GraphiqueAnime, Citation, Schema, CartonPiece, OuvertureDossier, Teaser,
  MotCle: (p: {texte: string; surligne?: boolean}) => <MotCle {...p} fond="assombri" taille={p.texte.length > 14 ? 150 : 200} />,
  TamponCalque, ChiffreIncruste, DateIncruste,
};

/** Lit videos/<slug>/scenes.json (copié dans public/) pour connaître la durée. */
export const calculerMetadonnees: CalculateMetadataFunction<PropsVideo> = async ({props}) => {
  const rep = await fetch(staticFile(`videos/${props.slug}/scenes.json`));
  if (!rep.ok) throw new Error(`scenes.json introuvable pour « ${props.slug} » : lance d'abord npm run video ${props.slug}`);
  const plan = (await rep.json()) as Plan;
  const echelle = props.apercu ? 2 / 3 : 1;
  return {
    durationInFrames: Math.max(30, ms(plan.dureeMs)),
    fps: FPS,
    width: Math.round(LARGEUR * echelle),
    height: Math.round(HAUTEUR * echelle),
    props: {...props, plan},
  };
};

/** Musique : baisse sous la voix (ducking), quasi silence sur les grandes pauses avant les révélations. */
const volumeMusique = (plan: Plan) => {
  const parole = plan.parole;
  const silences = plan.silences;
  return (f: number) => {
    const t = (f / FPS) * 1000;
    if (silences.some(([a, b]) => t > a + 150 && t < b - 100)) return 0.04;
    // distance à la parole la plus proche
    let lo = 0;
    let hi = parole.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (parole[mid][1] < t) lo = mid + 1;
      else hi = mid;
    }
    const [a, b] = parole[lo] ?? [0, 0];
    if (t >= a && t <= b) return 0.1;
    const d = Math.min(Math.abs(t - a), Math.abs(t - b), lo > 0 ? Math.abs(t - parole[lo - 1][1]) : Infinity);
    return 0.1 + Math.min(1, d / 400) * 0.18;
  };
};

const Musiques: React.FC<{plan: Plan}> = ({plan}) => {
  const fichiers = getStaticFiles()
    .map((f) => f.name)
    .filter((n) => n.startsWith('musique/') && /\.(mp3|wav|m4a|ogg)$/i.test(n))
    .sort();
  const volume = volumeMusique(plan);
  const sections = plan.sections.length ? plan.sections : [{nom: '', debutMs: 0, piece: null}];
  return (
    <>
      {sections.map((s, i) => {
        const debut = i === 0 ? 0 : ms(s.debutMs);
        const fin = i + 1 < sections.length ? ms(sections[i + 1].debutMs) : ms(plan.dureeMs);
        // une musique par pièce si /musique en contient, sinon la nappe grave
        const src = fichiers.length ? staticFile(fichiers[i % fichiers.length]) : staticFile('sfx/nappe.wav');
        return (
          <Sequence key={i} from={debut} durationInFrames={Math.max(1, fin - debut)} layout="none">
            <Audio src={src} loop volume={(f) => volume(f + debut) * (fichiers.length ? 1 : 1.6)} />
          </Sequence>
        );
      })}
    </>
  );
};

export const Pistes: React.FC<{plan: Plan; slug: string; sansFiligrane?: boolean}> = ({plan, slug, sansFiligrane}) => (
  <AbsoluteFill style={{background: '#0D0D0D'}}>
    {plan.fond.map((s, i) => {
      const C = COMPOSANTS[s.composant];
      if (!C) return null;
      const de = ms(s.debutMs);
      const duree = Math.max(1, ms(s.finMs) - de);
      const precedent = plan.fond[i - 1];
      // flash sur les changements de lieu (cartes) et à la reprise après un carton de pièce
      const flash = s.composant === 'CarteFlux' || precedent?.composant === 'CartonPiece';
      return (
        <React.Fragment key={i}>
          <Sequence from={de} durationInFrames={duree} name={`${s.composant} ${(s as {scene?: string}).scene ?? ''}`} layout="none">
            <AbsoluteFill>
              <C {...s.props} debutSceneMs={s.debutMs} />
            </AbsoluteFill>
          </Sequence>
          {flash ? (
            <Sequence from={Math.max(0, de - 3)} durationInFrames={12} name="flash" layout="none">
              <AbsoluteFill>
                <Flash />
              </AbsoluteFill>
            </Sequence>
          ) : null}
        </React.Fragment>
      );
    })}
    {plan.calques.map((s, i) => {
      const C = COMPOSANTS[s.composant];
      if (!C) return null;
      const de = ms(s.debutMs);
      return (
        <Sequence key={'c' + i} from={de} durationInFrames={Math.max(1, ms(s.finMs) - de)} name={s.composant} layout="none">
          <AbsoluteFill>
            <C {...s.props} />
          </AbsoluteFill>
        </Sequence>
      );
    })}
    <Audio src={staticFile(`videos/${slug}/${plan.voix.fichier}`)} />
    <Musiques plan={plan} />
    <GrainVignette />
    {plan.voix.test && !sansFiligrane ? <FiligraneVoixTest /> : null}
  </AbsoluteFill>
);

/** La vidéo complète d'un dossier, pilotée par scenes.json. */
export const Video: React.FC<PropsVideo> = ({slug, apercu, plan}) => {
  if (!plan) return null;
  const echelle = apercu ? 2 / 3 : 1;
  return (
    <ContexteVideo.Provider value={{slug}}>
      <AbsoluteFill style={{background: '#0D0D0D'}}>
        <div style={{width: LARGEUR, height: HAUTEUR, flexShrink: 0, transform: `scale(${echelle})`, transformOrigin: '0 0', position: 'relative'}}>
          <Pistes plan={plan} slug={slug} />
        </div>
      </AbsoluteFill>
    </ContexteVideo.Provider>
  );
};
