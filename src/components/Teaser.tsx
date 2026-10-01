import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {trouverAsset} from '../lib/assets';
import {useSlug} from '../lib/contexte';
import {Media} from './Media';
import {Tampon} from './Tampon';
import {Tape} from './Tape';

/** Teaser du prochain dossier : chemise fermée, tampon « DOSSIER N°00X », sujet tapé. */
export const Teaser: React.FC<{numero: number; titre: string; fondAssetId?: string}> = ({numero, titre, fondAssetId}) => {
  const frame = useCurrentFrame();
  const slug = useSlug();
  const fondDispo = fondAssetId ? trouverAsset(slug, fondAssetId) : undefined;
  const entree = interpolate(frame, [0, 14], [600, 0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{background: couleurs.noir}}>
      {fondAssetId && fondDispo ? (
        <AbsoluteFill style={{opacity: 0.35}}>
          <Media assetId={fondAssetId} genre="video" description="Fond du teaser" mouvement="gauche" />
        </AbsoluteFill>
      ) : null}
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div
          style={{
            width: 1100,
            height: 720,
            transform: `translateY(${entree}px) rotate(-2deg)`,
            background: `linear-gradient(160deg, #CDB283, ${couleurs.carton})`,
            boxShadow: '0 50px 140px rgba(0,0,0,0.9)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            gap: 40,
          }}
        >
          <div style={{fontFamily: machine, fontSize: 36, color: couleurs.encre, letterSpacing: 8}}>PROCHAIN DOSSIER</div>
          <Tampon texte="DOSSIER" sousTexte={`N°${String(numero).padStart(3, '0')}`} taille={130} rotation={-7} debut={16} />
          <div style={{fontFamily: anton, fontSize: 110, color: couleurs.encre, textTransform: 'uppercase', minHeight: 120}}>
            <Tape texte={titre} debut={36} lettresParSeconde={12} />
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
