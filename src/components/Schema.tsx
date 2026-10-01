import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton} from '../theme/polices';
import {Son} from './Son';

/** Schéma animé : étapes reliées par des flèches qui se dessinent (« vous → fondation »). */
export const Schema: React.FC<{etapes: string[]; pas?: number}> = ({etapes, pas = 900}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ecart = Math.round((pas / 1000) * fps);
  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <AbsoluteFill style={{backgroundImage: `radial-gradient(${couleurs.papier}14 2px, transparent 2px)`, backgroundSize: '44px 44px'}} />
      <div style={{display: 'flex', alignItems: 'center', gap: 0}}>
        {etapes.map((e, i) => {
          const a = 6 + i * ecart;
          const s = spring({frame: frame - a, fps, config: {damping: 15}});
          const fleche = interpolate(frame, [a - ecart + 10, a], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          return (
            <React.Fragment key={i}>
              {i > 0 ? (
                <svg width={260} height={60} style={{overflow: 'visible'}}>
                  <line x1={20} y1={30} x2={20 + 200 * fleche} y2={30} stroke={couleurs.vert} strokeWidth={8} strokeDasharray="18 12" />
                  {fleche > 0.95 ? <polygon points="215,8 250,30 215,52" fill={couleurs.vert} /> : null}
                </svg>
              ) : null}
              <div
                style={{
                  transform: `scale(${s})`,
                  background: i === etapes.length - 1 ? couleurs.papier : 'transparent',
                  border: `5px solid ${couleurs.papier}`,
                  color: i === etapes.length - 1 ? couleurs.noir : couleurs.papier,
                  padding: '40px 60px',
                  minWidth: 300,
                  textAlign: 'center',
                  fontFamily: anton,
                  fontSize: 80,
                }}
              >
                <Son nom="frappe" a={a} volume={0.6} />
                {e}
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
