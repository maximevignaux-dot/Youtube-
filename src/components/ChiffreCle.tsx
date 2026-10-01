import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {ms} from '../lib/contexte';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Son} from './Son';

export type ItemChiffre = {valeur: number | null; texte: string; unite: string; aMs: number};

const formater = (n: number, modele: string) => {
  const dec = modele.includes(',') ? 1 : 0;
  const s = n.toFixed(dec).replace('.', ',');
  const [e, d] = s.split(',');
  return e.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (d ? ',' + d : '');
};

/** Chiffres-clés (non monétaires) : chacun apparaît au mot exact où il est prononcé et défile jusqu'à sa valeur. */
export const ChiffreCle: React.FC<{items: ItemChiffre[]; debutSceneMs?: number}> = ({items, debutSceneMs = 0}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.05]);
  const plusieurs = items.length > 1;
  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${couleurs.papier}0d 2px, transparent 2px), linear-gradient(90deg, ${couleurs.papier}0d 2px, transparent 2px)`,
          backgroundSize: '80px 80px',
          transform: `translateY(${-frame * 0.6}px)`,
        }}
      />
      <div style={{display: 'flex', gap: plusieurs ? 90 : 0, alignItems: 'flex-end', transform: `scale(${zoom})`}}>
        {items.map((it, i) => {
          const a = Math.max(i === 0 ? 0 : 4, ms(it.aMs - debutSceneMs));
          const f = frame - a;
          if (f < 0) return <div key={i} style={{width: 0}} />;
          const entree = spring({frame: f, fps, config: {damping: 14, stiffness: 260}});
          const p = interpolate(f, [2, 26], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
          const affiche = it.valeur != null ? formater(it.valeur * p, it.texte) : it.texte;
          const taille = plusieurs ? 190 : it.texte.length > 8 ? 230 : 300;
          return (
            <div key={i} style={{textAlign: 'center', transform: `translateY(${(1 - entree) * 120}px)`, opacity: entree}}>
              <Son nom="frappe" a={a} volume={0.8} />
              <div style={{fontFamily: anton, fontSize: taille, lineHeight: 1, color: couleurs.papier, textShadow: '0 12px 40px rgba(0,0,0,0.8)'}}>
                {affiche}
              </div>
              <div style={{fontFamily: machine, fontSize: plusieurs ? 46 : 64, color: couleurs.jaune, letterSpacing: 6, marginTop: 10}}>{it.unite}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
