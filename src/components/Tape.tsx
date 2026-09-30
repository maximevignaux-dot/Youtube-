import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

/** Texte qui se tape lettre par lettre. */
export const Tape: React.FC<{texte: string; debut?: number; lettresParSeconde?: number; curseur?: boolean}> = ({
  texte,
  debut = 0,
  lettresParSeconde = 22,
  curseur = true,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const n = Math.max(0, Math.floor(((frame - debut) / fps) * lettresParSeconde));
  const fini = n >= texte.length;
  return (
    <span>
      {texte.slice(0, n)}
      {curseur && !fini && frame >= debut ? <span style={{opacity: 0.7}}>▌</span> : null}
    </span>
  );
};
