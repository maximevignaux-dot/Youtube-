import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {couleurs} from '../theme/palette';
import {machine} from '../theme/polices';
import {Tampon} from './Tampon';
import {Tape} from './Tape';

/** Début d'acte : tampon rouge « PIÈCE N°2 » + titre de l'acte tapé à la machine. */
export const CartonPiece: React.FC<{numero: number; titre: string}> = ({numero, titre}) => {
  const frame = useCurrentFrame();
  const derive = interpolate(frame, [0, 90], [1, 1.06]);
  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{transform: `scale(${derive})`, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 60}}>
        <Tampon texte={`PIÈCE N°${numero}`} taille={200} rotation={-6} debut={3} />
        <div style={{fontFamily: machine, fontSize: 64, color: couleurs.papier, letterSpacing: 3, minHeight: 80}}>
          <Tape texte={titre} debut={14} lettresParSeconde={20} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
