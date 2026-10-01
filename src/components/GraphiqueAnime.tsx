import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Son} from './Son';

export type Barre = {label: string; valeur: number; texte?: string};

/** Barres qui se dessinent sur du papier millimétré. La plus grande est en vert billet. */
export const GraphiqueAnime: React.FC<{barres: Barre[]; titre?: string}> = ({barres, titre}) => {
  const frame = useCurrentFrame();
  const max = Math.max(...barres.map((b) => b.valeur), 1);
  const H = 560;
  const largeur = Math.min(320, 1100 / Math.max(barres.length, 1));
  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <div
        style={{
          width: 1500,
          height: 900,
          background: couleurs.papier,
          backgroundImage:
            'linear-gradient(rgba(31,138,91,0.28) 2px, transparent 2px), linear-gradient(90deg, rgba(31,138,91,0.28) 2px, transparent 2px), linear-gradient(rgba(31,138,91,0.12) 1px, transparent 1px), linear-gradient(90deg, rgba(31,138,91,0.12) 1px, transparent 1px)',
          backgroundSize: '100px 100px, 100px 100px, 20px 20px, 20px 20px',
          boxShadow: '0 40px 100px rgba(0,0,0,0.8)',
          transform: `rotate(-0.8deg) scale(${interpolate(frame, [0, 200], [1, 1.05])})`,
          position: 'relative',
          padding: '60px 100px',
          boxSizing: 'border-box',
        }}
      >
        {titre ? <div style={{fontFamily: anton, fontSize: 60, color: couleurs.encre}}>{titre}</div> : null}
        <div style={{position: 'absolute', left: 100, right: 100, bottom: 130, height: H, display: 'flex', alignItems: 'flex-end', justifyContent: 'space-around', borderBottom: `5px solid ${couleurs.encre}`}}>
          {barres.map((b, i) => {
            const a = 10 + i * 22;
            const p = interpolate(frame, [a, a + 26], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
            const h = Math.max(6, (b.valeur / max) * H * p);
            const plusGrande = b.valeur === max;
            return (
              <div key={i} style={{position: 'relative', width: largeur, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%'}}>
                <Son nom="frappe" a={a} volume={0.5} />
                <div style={{fontFamily: anton, fontSize: 70, color: plusGrande ? couleurs.vert : couleurs.encre, opacity: p, marginBottom: 10}}>{b.texte}</div>
                <div style={{width: '100%', height: h, background: plusGrande ? couleurs.vert : couleurs.encre, opacity: 0.9, boxShadow: '6px 6px 0 rgba(0,0,0,0.15)'}} />
                <div style={{position: 'absolute', bottom: -80, fontFamily: machine, fontSize: 44, color: couleurs.encre}}>{b.label}</div>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
