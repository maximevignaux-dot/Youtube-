import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Tape} from './Tape';

/** Citation : grands guillemets rouges, texte tapé, source en dessous. */
export const Citation: React.FC<{texte: string; auteur?: string}> = ({texte, auteur}) => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 200], [1, 1.06]);
  const fin = 8 + Math.ceil((texte.length / 16) * 30);
  const opAuteur = interpolate(frame, [fin, fin + 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{width: 1400, transform: `scale(${zoom})`, position: 'relative'}}>
        <div style={{position: 'absolute', left: -120, top: -170, fontFamily: anton, fontSize: 400, color: couleurs.rouge, opacity: 0.85}}>«</div>
        <div style={{fontFamily: machine, fontSize: texte.length > 60 ? 72 : 96, color: couleurs.papier, lineHeight: 1.25}}>
          <Tape texte={texte} debut={8} lettresParSeconde={16} />
        </div>
        {auteur ? (
          <div style={{fontFamily: anton, fontSize: 48, color: couleurs.jaune, marginTop: 50, letterSpacing: 3, opacity: opAuteur}}>— {auteur.toUpperCase()}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
