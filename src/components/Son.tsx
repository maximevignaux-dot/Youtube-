import React from 'react';
import {Audio, Sequence, staticFile} from 'remotion';

export type NomSfx = 'tampon' | 'frappe' | 'machine-a-ecrire' | 'flash' | 'liasse' | 'feuille' | 'nappe';

/** Joue un son de /sfx à la frame `a` (relative à la scène en cours). */
export const Son: React.FC<{nom: NomSfx; a?: number; volume?: number; duree?: number; boucle?: boolean}> = ({
  nom,
  a = 0,
  volume = 0.8,
  duree,
  boucle,
}) => (
  <Sequence from={a} durationInFrames={duree} layout="none">
    <Audio src={staticFile(`sfx/${nom}.wav`)} volume={volume} loop={boucle} />
  </Sequence>
);
