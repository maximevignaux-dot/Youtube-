import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {ms} from '../lib/contexte';
import {couleurs} from '../theme/palette';
import {anton, inter, machine} from '../theme/polices';
import {Son} from './Son';
import {Tampon} from './Tampon';

export type LigneDocument = {
  texte: string;
  caviarde?: boolean; // barre noire par-dessus
  revelerAMs?: number | null; // moment (ms dans la vidéo) où la barre se retire
  surligner?: boolean; // surligneur jaune (l'info clé)
};

type Props = {
  entete: string;
  style?: 'document' | 'journal' | 'rapport';
  tampon?: string | null;
  lignes: LigneDocument[];
  debutSceneMs?: number;
};

/**
 * Document recréé (contrat, arrêt, article…). Les barres noires se retirent au moment où la phrase
 * est prononcée, puis l'info clé est surlignée. Mention « reconstitution » discrète, toujours.
 */
export const DocumentCaviarde: React.FC<Props> = ({entete, style = 'document', tampon, lignes, debutSceneMs = 0}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.08]);
  const glisse = interpolate(frame, [0, 14], [120, 0], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const longueur = lignes.reduce((a, l) => a + l.texte.length, 0);
  const taille = longueur > 420 ? 34 : longueur > 260 ? 40 : 48;
  const journal = style === 'journal';

  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <Son nom="feuille" volume={0.6} />
      <div
        style={{
          position: 'relative',
          width: 1360,
          padding: journal ? '60px 90px 80px' : '70px 100px 80px',
          background: journal ? 'linear-gradient(170deg, #E9E3D3, #CFC6B0)' : `linear-gradient(170deg, ${couleurs.papier}, ${couleurs.papierOmbre})`,
          boxShadow: '0 40px 100px rgba(0,0,0,0.8)',
          transform: `translateY(${glisse}px) scale(${zoom}) rotate(${journal ? -1.2 : 0.8}deg)`,
          fontFamily: journal ? inter : machine,
          color: couleurs.encre,
        }}
      >
        {journal ? (
          <div style={{borderBottom: `4px double ${couleurs.encre}`, paddingBottom: 14, marginBottom: 30, textAlign: 'center'}}>
            <div style={{fontFamily: anton, fontSize: 30, letterSpacing: 10, opacity: 0.6}}>ÉDITION DU JOUR</div>
            <div style={{fontFamily: anton, fontSize: 74, lineHeight: 1.05}}>{entete}</div>
          </div>
        ) : (
          <div style={{fontFamily: anton, fontSize: entete.length > 34 ? 46 : 58, letterSpacing: 2, borderBottom: `3px solid ${couleurs.encre}`, paddingBottom: 14, marginBottom: 34, paddingRight: tampon ? 330 : 0}}>
            {style === 'rapport' ? <div style={{fontSize: 26, letterSpacing: 8, opacity: 0.6}}>RAPPORT</div> : null}
            {entete}
          </div>
        )}
        {lignes.map((l, i) => {
          const a = l.revelerAMs != null ? Math.max(6, ms(l.revelerAMs - debutSceneMs)) : 8 + i * 6;
          const retrait = l.caviarde ? interpolate(frame, [a, a + 9], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.quad)}) : 0;
          const debutSurligne = (l.caviarde ? a + 10 : Math.max(a, 18)) + 6;
          const surligne = l.surligner ? interpolate(frame, [debutSurligne, debutSurligne + 14], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 0;
          return (
            <div key={i} style={{position: 'relative', fontSize: taille, lineHeight: 1.35, margin: '18px 0', fontWeight: journal ? 600 : 400}}>
              {l.caviarde && l.revelerAMs != null ? <Son nom="feuille" a={a} volume={0.45} /> : null}
              <span
                style={{
                  backgroundImage: `linear-gradient(${couleurs.jaune}, ${couleurs.jaune})`,
                  backgroundRepeat: 'no-repeat',
                  backgroundSize: `${surligne}% 100%`,
                  boxDecorationBreak: 'clone',
                  WebkitBoxDecorationBreak: 'clone',
                  padding: '0 6px',
                }}
              >
                {l.texte}
              </span>
              {l.caviarde ? (
                <div style={{position: 'absolute', inset: '-4px -10px', background: '#050505', transformOrigin: 'right center', transform: `scaleX(${retrait})`}} />
              ) : null}
            </div>
          );
        })}
        <div style={{position: 'absolute', left: 30, bottom: 16, fontFamily: machine, fontSize: 20, opacity: 0.45, letterSpacing: 3}}>
          RECONSTITUTION — DOCUMENT NON ORIGINAL
        </div>
        {tampon ? (
          <div style={{position: 'absolute', right: 60, top: 36}}>
            <Tampon texte={tampon} taille={58} rotation={8} debut={12} />
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
