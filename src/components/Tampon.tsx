import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton} from '../theme/polices';
import {Son} from './Son';

export const masqueEncre = `url("data:image/svg+xml;utf8,${encodeURIComponent(
  "<svg xmlns='http://www.w3.org/2000/svg' width='320' height='320'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='3' seed='7'/><feColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -2.6 2.15'/></filter><rect width='100%' height='100%' filter='url(#n)'/></svg>",
)}")`;

type Props = {
  texte: string;
  sousTexte?: string;
  couleur?: string;
  taille?: number;
  rotation?: number;
  debut?: number; // frame où le tampon frappe
  son?: boolean;
  style?: React.CSSProperties;
};

/** Tampon encreur qui « frappe » : grossit, s'écrase, légère secousse. */
export const Tampon: React.FC<Props> = ({
  texte,
  sousTexte,
  couleur = couleurs.rouge,
  taille = 110,
  rotation = -12,
  debut = 0,
  son = true,
  style,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const f = frame - debut;
  if (f < 0) return son ? <Son nom="tampon" a={debut} volume={0.9} /> : null;
  const frappe = spring({frame: f, fps, config: {damping: 14, stiffness: 320, mass: 0.6}});
  const echelle = interpolate(frappe, [0, 1], [2.4, 1]);
  const opacite = interpolate(f, [0, 3], [0, 0.92], {extrapolateRight: 'clamp'});
  const secousse = f < 8 ? Math.sin(f * 3.1) * (8 - f) * 0.6 : 0;
  return (
    <>
      {son ? <Son nom="tampon" a={debut} volume={0.9} /> : null}
      <div
      style={{
        display: 'inline-block',
        whiteSpace: 'nowrap',
        transform: `translate(${secousse}px, ${-secousse}px) rotate(${rotation}deg) scale(${echelle})`,
        opacity: opacite,
        color: couleur,
        border: `${taille * 0.07}px solid ${couleur}`,
        outline: `${taille * 0.025}px solid ${couleur}`,
        outlineOffset: taille * 0.05,
        borderRadius: 8,
        padding: `${taille * 0.08}px ${taille * 0.3}px`,
        fontFamily: anton,
        fontSize: taille,
        lineHeight: 1,
        letterSpacing: taille * 0.04,
        textAlign: 'center',
        textTransform: 'uppercase',
        // encre irrégulière (petits manques comme un vrai tampon)
        WebkitMaskImage: masqueEncre,
        maskImage: masqueEncre,
        WebkitMaskSize: '320px 320px',
        maskSize: '320px 320px',
        ...style,
      }}
    >
      {texte}
      {sousTexte ? <div style={{fontSize: taille * 0.28, letterSpacing: 2, marginTop: 6}}>{sousTexte}</div> : null}
    </div>
    </>
  );
};
