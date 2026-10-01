import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {filtreDossier} from './Habillage';

/**
 * Effet 2,5D : la photo d'origine en fond (floutée, bouge lentement) et le sujet détouré
 * par-dessus, qui avance plus vite → impression de profondeur.
 */
export const Parallaxe25D: React.FC<{fond: string; sujet: string; sens?: 1 | -1}> = ({fond, sujet, sens = 1}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const p = interpolate(frame, [0, durationInFrames], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      <AbsoluteFill style={{transform: `scale(${1.12 + 0.04 * p}) translateX(${sens * (-20 + 40 * p)}px)`}}>
        <Img src={fond} style={{width: '100%', height: '100%', objectFit: 'cover', filter: `${filtreDossier} blur(5px) brightness(0.7)`}} />
      </AbsoluteFill>
      <AbsoluteFill style={{transform: `scale(${1.04 + 0.14 * p}) translateX(${sens * (40 - 80 * p)}px)`}}>
        <Img src={sujet} style={{width: '100%', height: '100%', objectFit: 'cover', filter: `${filtreDossier} drop-shadow(0 30px 40px rgba(0,0,0,0.8))`}} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
