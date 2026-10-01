import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Son} from './Son';
import {Tampon} from './Tampon';
import {Tape} from './Tape';

const sortie = (frame: number, duree: number) =>
  interpolate(frame, [duree - 6, duree], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

/** Tampon frappé par-dessus l'image en cours (verdicts, « CLASSÉ SANS SUITE »…). */
export const TamponCalque: React.FC<{texte: string}> = ({texte}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: 'rgba(13,13,13,0.45)', justifyContent: 'center', alignItems: 'center', opacity: sortie(frame, durationInFrames)}}>
      <div style={{background: 'rgba(239,230,210,0.92)', padding: '40px 60px', transform: 'rotate(-3deg)'}}>
        <Tampon texte={texte} taille={texte.length > 16 ? 96 : 130} rotation={-9} debut={2} />
      </div>
    </AbsoluteFill>
  );
};

/** Nombre prononcé sans balise : il s'affiche en grand, au mot exact (bande sombre pour rester lisible). */
export const ChiffreIncruste: React.FC<{texte: string; unite: string}> = ({texte, unite}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const s = spring({frame, fps, config: {damping: 13, stiffness: 380, mass: 0.5}});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity: sortie(frame, durationInFrames)}}>
      <Son nom="frappe" volume={0.8} />
      <div style={{position: 'absolute', left: 0, right: 0, height: 360, background: 'linear-gradient(90deg, transparent, rgba(13,13,13,0.85) 20%, rgba(13,13,13,0.85) 80%, transparent)'}} />
      <div style={{display: 'flex', alignItems: 'baseline', gap: 30, transform: `scale(${interpolate(s, [0, 1], [1.6, 1])}) rotate(-1.5deg)`}}>
        <span style={{fontFamily: anton, fontSize: 230, color: couleurs.jaune, lineHeight: 1}}>{texte}</span>
        <span style={{fontFamily: anton, fontSize: 110, color: couleurs.papier}}>{unite}</span>
      </div>
    </AbsoluteFill>
  );
};

/** Année citée sans frise : petite étiquette tapée à la machine en haut à gauche. */
export const DateIncruste: React.FC<{texte: string}> = ({texte}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const entree = interpolate(frame, [0, 8], [-60, 0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{opacity: sortie(frame, durationInFrames)}}>
      <Son nom="machine-a-ecrire" a={2} duree={14} volume={0.5} />
      <div
        style={{
          position: 'absolute',
          left: 90,
          top: 90 + entree,
          background: couleurs.papier,
          color: couleurs.encre,
          fontFamily: machine,
          fontSize: 70,
          padding: '12px 34px',
          transform: 'rotate(-2deg)',
          boxShadow: '0 14px 40px rgba(0,0,0,0.7)',
        }}
      >
        <Tape texte={texte} debut={2} lettresParSeconde={10} />
      </div>
    </AbsoluteFill>
  );
};
