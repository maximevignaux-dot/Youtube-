import React from 'react';
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Son} from './Son';

export type ElementTableau = {label: string; nouveau?: boolean; filRouge?: boolean};

type Props = {
  centres: string[]; // 1 centre, ou 2 camps (« FAMILLE » vs « CLERC »)
  elements: ElementTableau[];
  mode?: 'nouveau' | 'ajout' | 'vue' | 'ensemble' | 'coupe';
};

const L = 1920;
const H = 1080;
const PLATEAU = {l: 3000, h: 1800}; // le liège est plus grand que l'écran : la caméra s'y promène

/** Position déterministe autour du centre (ellipse, angle d'or) pour que le tableau soit stable d'une scène à l'autre. */
const position = (i: number, n: number) => {
  const angle = i * 2.39996 - Math.PI / 2;
  const r = 400 + (i % 3) * 95;
  return {x: PLATEAU.l / 2 + Math.cos(angle) * r * 1.55, y: PLATEAU.h / 2 + Math.sin(angle) * r * 0.78 + (n > 8 ? (i % 2) * 30 : 0)};
};

const Carte: React.FC<{label: string; x: number; y: number; apparition: number; centre?: boolean; rot: number}> = ({label, x, y, apparition, centre, rot}) => (
  <div
    style={{
      position: 'absolute',
      left: x,
      top: y,
      transform: `translate(-50%, -50%) rotate(${rot}deg) scale(${apparition})`,
      background: centre ? couleurs.papier : '#F4EEDF',
      padding: centre ? '34px 50px' : '22px 30px',
      minWidth: centre ? 360 : 240,
      maxWidth: 460,
      textAlign: 'center',
      boxShadow: '0 18px 40px rgba(0,0,0,0.6)',
      fontFamily: centre ? anton : machine,
      fontSize: centre ? 72 : label.length > 22 ? 34 : 42,
      lineHeight: 1.15,
      color: couleurs.encre,
      border: centre ? `6px solid ${couleurs.rouge}` : 'none',
    }}
  >
    <div style={{position: 'absolute', top: -14, left: '50%', width: 30, height: 30, borderRadius: 15, background: couleurs.rouge, transform: 'translateX(-50%)', boxShadow: '0 4px 6px rgba(0,0,0,0.5)'}} />
    {label}
  </div>
);

/** Tableau de liège : cartes punaisées, FIL ROUGE qui se tend, caméra qui glisse vers la nouveauté. */
export const TableauEnquete: React.FC<Props> = ({centres, elements, mode = 'vue'}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const deuxCamps = centres.length > 1;
  const posCentres = deuxCamps
    ? [{x: PLATEAU.l / 2 - 520, y: PLATEAU.h / 2}, {x: PLATEAU.l / 2 + 520, y: PLATEAU.h / 2}]
    : [{x: PLATEAU.l / 2, y: PLATEAU.h / 2}];
  const pos = elements.map((_, i) => position(i, elements.length));
  const iNouveau = elements.findIndex((e) => e.nouveau);
  const tension = (debut: number) => interpolate(frame, [debut, debut + 16], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});

  // caméra
  const vueLarge = mode === 'ensemble' || mode === 'coupe';
  let cible = posCentres[0];
  // on cadre entre le centre et la nouvelle carte : on voit le fil rouge se tendre
  if (iNouveau >= 0) cible = {x: (pos[iNouveau].x + posCentres[0].x) / 2, y: (pos[iNouveau].y + posCentres[0].y) / 2};
  const p = interpolate(frame, [4, 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
  const depart = {x: PLATEAU.l / 2, y: PLATEAU.h / 2};
  const cam = vueLarge ? depart : {x: depart.x + (cible.x - depart.x) * p, y: depart.y + (cible.y - depart.y) * p};
  const echelle = vueLarge
    ? interpolate(frame, [0, durationInFrames], [0.72, 0.56])
    : iNouveau >= 0
      ? interpolate(p, [0, 1], [0.6, 0.85])
      : interpolate(frame, [0, durationInFrames], [0.68, 0.76]);

  const fil = (x1: number, y1: number, x2: number, y2: number, t: number, coupe = false) => {
    const mx = (x1 + x2) / 2;
    const my = (y1 + y2) / 2 + 60 * (1 - t) + 30; // le fil pend puis se tend
    const xe = x1 + (x2 - x1) * t;
    const ye = y1 + (y2 - y1) * t;
    return <path d={`M ${x1} ${y1} Q ${mx} ${my} ${xe} ${ye}`} stroke={couleurs.rouge} strokeWidth={coupe ? 4 : 6} fill="none" strokeDasharray={coupe ? '20 18' : undefined} opacity={0.95} />;
  };
  const coupe = mode === 'coupe' ? interpolate(frame, [30, 40], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;

  return (
    <AbsoluteFill style={{background: '#1E1611', overflow: 'hidden'}}>
      {iNouveau >= 0 ? <Son nom="frappe" a={22} volume={0.7} /> : null}
      <div
        style={{
          position: 'absolute',
          width: PLATEAU.l,
          height: PLATEAU.h,
          left: L / 2 - cam.x,
          top: H / 2 - cam.y,
          transform: `scale(${echelle})`,
          transformOrigin: `${cam.x}px ${cam.y}px`,
          // liège sombre
          background:
            'radial-gradient(circle at 20% 30%, rgba(120,80,40,0.25) 0 2px, transparent 3px), radial-gradient(circle at 70% 60%, rgba(0,0,0,0.25) 0 2px, transparent 3px), #3A2A1C',
          backgroundSize: '23px 19px, 31px 27px, auto',
          boxShadow: 'inset 0 0 300px rgba(0,0,0,0.9)',
        }}
      >
        <svg width={PLATEAU.l} height={PLATEAU.h} style={{position: 'absolute', left: 0, top: 0}}>
          {deuxCamps ? fil(posCentres[0].x, posCentres[0].y, posCentres[1].x, posCentres[1].y, mode === 'coupe' ? coupe : 1, mode === 'coupe') : null}
          {elements.map((e, i) => {
            const c = deuxCamps ? posCentres[pos[i].x < PLATEAU.l / 2 ? 0 : 1] : posCentres[0];
            const t = e.nouveau ? tension(26) : 1;
            return <g key={i}>{fil(c.x, c.y, pos[i].x, pos[i].y, t)}</g>;
          })}
        </svg>
        {posCentres.map((c, i) => (
          <Carte key={'c' + i} label={centres[i]} x={c.x} y={c.y} apparition={mode === 'nouveau' ? spring({frame: frame - 4, fps, config: {damping: 14}}) : 1} centre rot={i ? 2 : -2} />
        ))}
        {elements.map((e, i) => (
          <Carte key={i} label={e.label} x={pos[i].x} y={pos[i].y} apparition={e.nouveau ? spring({frame: frame - 18, fps, config: {damping: 12}}) : 1} rot={((i * 37) % 9) - 4} />
        ))}
      </div>
      {mode === 'coupe' ? <Son nom="flash" a={32} volume={0.5} /> : null}
    </AbsoluteFill>
  );
};
