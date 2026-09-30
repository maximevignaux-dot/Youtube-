import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {couleurs} from '../theme/palette';
import {machine} from '../theme/polices';

/** Grain papier + vignettage, posé au-dessus de TOUTE la vidéo. */
export const GrainVignette: React.FC<{intensite?: number}> = ({intensite = 1}) => {
  const frame = useCurrentFrame();
  const graine = Math.floor(frame / 2) % 50; // le grain « vit » sans clignoter
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <svg width="100%" height="100%" style={{position: 'absolute', opacity: 0.13 * intensite, mixBlendMode: 'overlay'}}>
        <filter id={`grain-${graine}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" seed={graine} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain-${graine})`} />
      </svg>
      <AbsoluteFill
        style={{
          background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.55) 85%, rgba(0,0,0,0.85) 100%)',
          opacity: intensite,
        }}
      />
    </AbsoluteFill>
  );
};

/** Petit filigrane affiché tant que la vidéo est calée sur la voix de synthèse. */
export const FiligraneVoixTest: React.FC = () => (
  <div
    style={{
      position: 'absolute',
      top: 36,
      right: 44,
      padding: '6px 14px',
      border: `3px solid ${couleurs.rouge}`,
      color: couleurs.rouge,
      fontFamily: machine,
      fontSize: 26,
      letterSpacing: 4,
      transform: 'rotate(3deg)',
      opacity: 0.8,
      background: 'rgba(13,13,13,0.4)',
    }}
  >
    VOIX TEST
  </div>
);

/** Étalonnage « dossier » appliqué à toutes les photos / vidéos : noirs profonds, teinte chaude. */
export const filtreDossier = 'contrast(1.12) saturate(0.8) sepia(0.14) brightness(0.9)';
