import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Son} from './Son';
import {Tampon} from './Tampon';
import {Tape} from './Tape';

type Props = {
  numero: number; // 1 → « DOSSIER N°001 »
  titre: string; // tapé sur la première page
  sousTitre?: string;
  frappe?: number; // frame du tampon sur la couverture
  ouverture?: number; // frame où la chemise s'ouvre
};

/** Chemise cartonnée : tampon « DOSSIER N°00X » frappé sur la couverture, puis elle s'ouvre. */
export const OuvertureDossier: React.FC<Props> = ({numero, titre, sousTitre, frappe = 12, ouverture = 34}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const numeroTexte = `N°${String(numero).padStart(3, '0')}`;
  const entree = interpolate(frame, [0, 10], [700, 0], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const angle = interpolate(frame, [ouverture, ouverture + 16], [0, -168], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.cubic),
  });
  const camera = interpolate(frame, [0, durationInFrames], [0.92, 1.08]);
  const L = 1300;
  const H = 860;

  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center', perspective: 2600}}>
      <Son nom="feuille" a={ouverture} volume={0.8} />
      <div style={{position: 'relative', width: L, height: H, transform: `translateY(${entree}px) scale(${camera})`, transformStyle: 'preserve-3d'}}>
        {/* dos de la chemise + onglet */}
        <div style={{position: 'absolute', inset: 0, background: couleurs.cartonFonce, borderRadius: 6, boxShadow: '0 50px 140px rgba(0,0,0,0.9)'}} />
        <div style={{position: 'absolute', top: -52, right: 90, width: 320, height: 60, background: couleurs.cartonFonce, borderRadius: '10px 10px 0 0'}} />
        {/* première page */}
        <div
          style={{
            position: 'absolute',
            inset: 26,
            background: couleurs.papier,
            padding: '90px 110px',
            boxSizing: 'border-box',
            fontFamily: machine,
            color: couleurs.encre,
          }}
        >
          <div style={{fontSize: 36, letterSpacing: 8, opacity: 0.6}}>DOSSIER {numeroTexte}</div>
          <div style={{fontFamily: anton, fontSize: 110, lineHeight: 1.05, marginTop: 40, textTransform: 'uppercase'}}>
            <Tape texte={titre} debut={ouverture + 14} lettresParSeconde={30} />
          </div>
          {sousTitre ? (
            <div style={{fontSize: 44, marginTop: 30}}>
              <Tape texte={sousTitre} debut={ouverture + 14 + Math.ceil((titre.length / 30) * 30)} lettresParSeconde={30} />
            </div>
          ) : null}
        </div>
        {/* couverture qui pivote */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            transformOrigin: 'left center',
            transform: `rotateY(${angle}deg)`,
            background: `linear-gradient(160deg, #CDB283, ${couleurs.carton})`,
            borderRadius: 6,
            backfaceVisibility: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            boxShadow: 'inset 0 0 80px rgba(0,0,0,0.25)',
          }}
        >
          <div style={{position: 'absolute', top: 60, left: 80, fontFamily: machine, fontSize: 32, color: couleurs.encre, opacity: 0.7}}>
            ARCHIVES — COULISSES DE L'ARGENT
          </div>
          <Tampon texte="DOSSIER" sousTexte={numeroTexte} taille={170} rotation={-8} debut={frappe} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
