import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Son} from './Son';
import {Tape} from './Tape';

/** Frise : les dates précédentes défilent vers la gauche, la nouvelle date se tape à la machine. */
const L = 1920;

export const TimelineMachine: React.FC<{date: string; precedentes?: string[]}> = ({date, precedentes = []}) => {
  const frame = useCurrentFrame();
  const glisse = interpolate(frame, [0, 18], [380, 0], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const trait = interpolate(frame, [0, 20], [0, 100], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center'}}>
      <Son nom="machine-a-ecrire" a={6} duree={Math.ceil((date.length / 9) * 30) + 4} volume={0.6} />
      {/* ruban de la frise */}
      <div style={{position: 'absolute', top: 600, left: 0, width: `${trait}%`, height: 4, background: couleurs.papier, opacity: 0.5}} />
      {/* anciennes dates, à gauche de la nouvelle */}
      {precedentes.map((d, i) => {
        const rang = precedentes.length - i; // 1 = la plus récente
        return (
          <div key={i} style={{position: 'absolute', top: 591, left: L / 2 - 330 - rang * 240 + glisse * 0.4, width: 200, textAlign: 'center', opacity: Math.max(0.15, 0.65 - rang * 0.12)}}>
            <div style={{width: 18, height: 18, borderRadius: 9, background: couleurs.papier, margin: '0 auto 18px'}} />
            <div style={{fontFamily: machine, fontSize: 44, color: couleurs.papier}}>{d}</div>
          </div>
        );
      })}
      {/* la nouvelle date */}
      <div style={{position: 'absolute', left: 0, right: 0, top: 300, textAlign: 'center'}}>
        <div style={{fontFamily: anton, fontSize: date.length > 6 ? 190 : 260, color: couleurs.papier, lineHeight: 1}}>
          <Tape texte={date} debut={6} lettresParSeconde={9} />
        </div>
      </div>
      <div style={{position: 'absolute', left: L / 2 - 17, top: 585, width: 34, height: 34, borderRadius: 17, background: couleurs.rouge, boxShadow: `0 0 30px ${couleurs.rouge}`}} />
    </AbsoluteFill>
  );
};
