import React from 'react';
import {AbsoluteFill, CalculateMetadataFunction, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {FiligraneVoixTest, GrainVignette, Tampon} from './components';
import {ContexteVideo, ms} from './lib/contexte';
import {couleurs, FPS} from './theme/palette';
import {anton, machine} from './theme/polices';
import {Pistes, Plan} from './Video';

type Mot = {i: number; mot: string; debut: number; fin: number};
export type PropsShort = {slug: string; debutMs: number; finMs: number; motCle: string; plan?: Plan | null; mots?: Mot[] | null};

export const calculerShort: CalculateMetadataFunction<PropsShort> = async ({props}) => {
  const plan = (await (await fetch(staticFile(`videos/${props.slug}/scenes.json`))).json()) as Plan;
  const fichier = plan.voix.motsFichier ?? (plan.voix.test ? 'voix-test.mots.json' : 'voix.mots.json');
  const mots = ((await (await fetch(staticFile(`videos/${props.slug}/${fichier}`))).json()).mots as Mot[]).filter(
    (m) => m.fin > props.debutMs && m.debut < props.finMs,
  );
  return {durationInFrames: Math.max(30, ms(props.finMs - props.debutMs)), fps: FPS, width: 1080, height: 1920, props: {...props, plan, mots}};
};

/** Sous-titres dynamiques : 3 à 4 mots à la fois, le mot prononcé passe en jaune. */
const SousTitres: React.FC<{mots: Mot[]; debutMs: number}> = ({mots, debutMs}) => {
  const frame = useCurrentFrame();
  const t = (frame / FPS) * 1000 + debutMs;
  const courant = mots.findIndex((m) => t >= m.debut - 40 && t < (mots[mots.indexOf(m) + 1]?.debut ?? m.fin + 400));
  if (courant < 0) return null;
  // groupes de mots qui ne coupent pas une phrase
  const groupe: Mot[] = [];
  let a = courant;
  while (a > 0 && courant - a < 3 && !/[.?!:…]$/.test(mots[a - 1].mot)) a--;
  a = courant - ((courant - a) % 4);
  for (let k = a; k < mots.length && groupe.length < 4; k++) {
    groupe.push(mots[k]);
    if (/[.?!:…]$/.test(mots[k].mot)) break;
  }
  return (
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '0 22px', padding: '0 60px'}}>
      {groupe.map((m) => {
        const actif = m === mots[courant];
        return (
          <span
            key={m.i}
            style={{
              fontFamily: anton,
              fontSize: 96,
              lineHeight: 1.15,
              textTransform: 'uppercase',
              color: actif ? couleurs.jaune : couleurs.papier,
              transform: actif ? 'scale(1.08)' : 'none',
              textShadow: '0 6px 0 #000, 0 0 30px rgba(0,0,0,0.9)',
            }}
          >
            {m.mot.replace(/[«»"]/g, '')}
          </span>
        );
      })}
    </div>
  );
};

/** Short vertical : mot-clé en grand la 1re seconde, puis bandeau-titre + scène au centre + sous-titres. */
export const Short: React.FC<PropsShort> = ({slug, debutMs, motCle, plan, mots}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (!plan || !mots) return null;
  const intro = interpolate(frame, [fps * 0.9, fps * 1.2], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const impact = spring({frame, fps, config: {damping: 13, stiffness: 300}});
  const scene = 1.32; // la scène 16:9 est agrandie (on rogne un peu les côtés) pour remplir la largeur verticale
  return (
    <ContexteVideo.Provider value={{slug}}>
      <AbsoluteFill style={{background: couleurs.noir}}>
        <AbsoluteFill style={{backgroundImage: `radial-gradient(${couleurs.papier}10 2px, transparent 2px)`, backgroundSize: '40px 40px'}} />
        {/* la scène du film, calée sur le bon moment */}
        <div style={{position: 'absolute', top: 640, left: (1080 - 1920 * 0.5625 * scene) / 2, width: 1920, height: 1080, transform: `scale(${0.5625 * scene})`, transformOrigin: '0 0', overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,0.9)'}}>
          <Sequence from={-ms(debutMs)} layout="none">
            <Pistes plan={plan} slug={slug} sansFiligrane />
          </Sequence>
        </div>
        {/* bandeau-titre */}
        <div style={{position: 'absolute', top: 170, left: 0, right: 0, textAlign: 'center', opacity: 1 - intro}}>
          <div style={{fontFamily: machine, fontSize: 38, color: couleurs.papier, letterSpacing: 8, opacity: 0.8}}>DOSSIERS</div>
          <div style={{fontFamily: anton, fontSize: motCle.length > 14 ? 92 : 120, color: couleurs.papier, lineHeight: 1.05, padding: '10px 60px', textTransform: 'uppercase'}}>{motCle}</div>
        </div>
        <div style={{position: 'absolute', top: 1450, left: 0, right: 0}}>
          <SousTitres mots={mots} debutMs={debutMs} />
        </div>
        {/* 1re seconde : le mot-clé en très grand */}
        {intro > 0 ? (
          <AbsoluteFill style={{background: couleurs.noir, opacity: intro, justifyContent: 'center', alignItems: 'center'}}>
            <div style={{transform: `scale(${interpolate(impact, [0, 1], [1.6, 1])}) rotate(-3deg)`, textAlign: 'center', padding: 60}}>
              <div style={{fontFamily: anton, fontSize: motCle.length > 12 ? 150 : 210, lineHeight: 1, color: couleurs.jaune, textTransform: 'uppercase'}}>{motCle}</div>
              <div style={{marginTop: 50}}>
                <Tampon texte="DOSSIER" taille={90} rotation={-8} debut={-30} son={false} />
              </div>
            </div>
          </AbsoluteFill>
        ) : null}
        <GrainVignette intensite={0.6} />
        {plan.voix.test ? <FiligraneVoixTest /> : null}
      </AbsoluteFill>
    </ContexteVideo.Provider>
  );
};
