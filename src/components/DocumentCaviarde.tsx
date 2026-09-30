import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Son} from './Son';
import {Tampon} from './Tampon';

export type LigneDocument = {
  texte: string;
  caviarde?: boolean; // barre noire par-dessus
  revelerA?: number; // frame où la barre se retire (sinon reste caviardée)
  surligner?: boolean; // surligneur jaune après révélation (l'info clé)
};

type Props = {
  entete: string; // ex. « FICHE D'IDENTIFICATION »
  tampon?: string; // ex. « CONFIDENTIEL »
  lignes: LigneDocument[];
};

/** Document recréé : les barres noires se retirent une par une, puis l'info clé est surlignée. */
export const DocumentCaviarde: React.FC<Props> = ({entete, tampon, lignes}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.12]);
  const glisse = interpolate(frame, [0, 12], [80, 0], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});

  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <Son nom="feuille" volume={0.6} />
      <div
        style={{
          position: 'relative',
          width: 1180,
          padding: '80px 100px',
          background: `linear-gradient(170deg, ${couleurs.papier}, ${couleurs.papierOmbre})`,
          boxShadow: '0 40px 100px rgba(0,0,0,0.8)',
          transform: `translateY(${glisse}px) scale(${zoom}) rotate(1deg)`,
          fontFamily: machine,
          color: couleurs.encre,
        }}
      >
        <div style={{fontFamily: anton, fontSize: 60, letterSpacing: 3, borderBottom: `3px solid ${couleurs.encre}`, paddingBottom: 16, marginBottom: 40}}>
          {entete}
        </div>
        {lignes.map((l, i) => {
          const retrait =
            l.caviarde && l.revelerA !== undefined
              ? interpolate(frame, [l.revelerA, l.revelerA + 8], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.quad)})
              : l.caviarde
                ? 1
                : 0;
          const debutSurligne = (l.revelerA ?? 0) + 10;
          const surligne = l.surligner
            ? interpolate(frame, [debutSurligne, debutSurligne + 10], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
            : 0;
          return (
            <div key={i} style={{position: 'relative', fontSize: 50, lineHeight: 1.25, margin: '22px 0', display: 'inline-block', width: '100%'}}>
              {l.caviarde && l.revelerA !== undefined ? <Son nom="feuille" a={l.revelerA} volume={0.5} /> : null}
              <span style={{position: 'relative', display: 'inline-block'}}>
                <span
                  style={{
                    position: 'absolute',
                    left: -8,
                    top: '12%',
                    height: '80%',
                    width: `calc(${surligne}% + 16px)`,
                    background: couleurs.jaune,
                    opacity: surligne > 0 ? 0.9 : 0,
                  }}
                />
                <span style={{position: 'relative'}}>{l.texte}</span>
                <span
                  style={{
                    position: 'absolute',
                    left: -10,
                    right: -10,
                    top: '-6%',
                    bottom: '2%',
                    background: '#050505',
                    transformOrigin: 'right center',
                    transform: `scaleX(${retrait})`,
                  }}
                />
              </span>
            </div>
          );
        })}
        {tampon ? (
          <div style={{position: 'absolute', right: 60, top: 40}}>
            <Tampon texte={tampon} taille={62} rotation={8} debut={10} />
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
