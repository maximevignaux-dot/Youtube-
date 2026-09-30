import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton} from '../theme/polices';
import {Son} from './Son';

type Props = {
  texte: string;
  couleur?: keyof typeof couleurs;
  surligne?: boolean; // bande de surligneur jaune derrière le mot (révélation)
  taille?: number;
  fond?: 'transparent' | 'assombri' | 'noir';
  son?: boolean;
};

/** Mot fort frappé à l'écran, synchro au mot exact de la voix (placer la Sequence sur ce mot). */
export const MotCle: React.FC<Props> = ({texte, couleur = 'papier', surligne = false, taille = 190, fond = 'assombri', son = true}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const impact = spring({frame, fps, config: {damping: 13, stiffness: 400, mass: 0.5}});
  const echelle = interpolate(impact, [0, 1], [1.7, 1]);
  const flou = interpolate(frame, [0, 4], [12, 0], {extrapolateRight: 'clamp'});
  const derive = interpolate(frame, [0, 90], [1, 1.05]); // mouvement permanent
  const surligneur = interpolate(frame, [5, 13], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fondCss = fond === 'noir' ? couleurs.noir : fond === 'assombri' ? 'rgba(13,13,13,0.72)' : 'transparent';

  return (
    <AbsoluteFill style={{background: fondCss, justifyContent: 'center', alignItems: 'center'}}>
      {son ? <Son nom="frappe" volume={0.9} /> : null}
      <div
        style={{
          position: 'relative',
          transform: `scale(${echelle * derive}) rotate(-1.5deg)`,
          filter: `blur(${flou}px)`,
          padding: '0 40px',
          maxWidth: '88%',
          textAlign: 'center',
        }}
      >
        {surligne ? (
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: '4%',
              height: '94%',
              width: `${surligneur}%`,
              background: couleurs.jaune,
              transform: 'skewX(-8deg)',
            }}
          />
        ) : null}
        <span
          style={{
            position: 'relative',
            fontFamily: anton,
            fontSize: taille,
            lineHeight: 1.05,
            textTransform: 'uppercase',
            color: surligne ? couleurs.noir : couleurs[couleur],
            textShadow: surligne ? 'none' : '0 10px 40px rgba(0,0,0,0.8)',
          }}
        >
          {texte}
        </span>
      </div>
    </AbsoluteFill>
  );
};
