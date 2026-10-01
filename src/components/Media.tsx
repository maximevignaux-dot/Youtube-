import React from 'react';
import {AbsoluteFill, Img, interpolate, OffthreadVideo, useCurrentFrame, useVideoConfig} from 'remotion';
import {trouverAsset} from '../lib/assets';
import {useSlug} from '../lib/contexte';
import {filtreDossier} from './Habillage';
import {Placeholder} from './Placeholder';

export type MouvementMedia = 'zoom-avant' | 'zoom-arriere' | 'gauche' | 'droite' | 'serre' | 'auto';

const MOUVEMENTS: MouvementMedia[] = ['zoom-avant', 'gauche', 'zoom-arriere', 'droite'];

/** Photo, vidéo ou image IA plein écran, toujours en mouvement. Carton « à fournir » si le fichier manque. */
export const Media: React.FC<{assetId: string; genre: 'photo' | 'video' | 'ia'; description: string; mouvement?: MouvementMedia}> = ({
  assetId,
  genre,
  description,
  mouvement = 'auto',
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const slug = useSlug();
  const asset = trouverAsset(slug, assetId);
  // mouvement « auto » : varie selon l'identifiant pour éviter la monotonie
  const m = mouvement === 'auto' ? MOUVEMENTS[[...assetId].reduce((a, c) => a + c.charCodeAt(0), 0) % 4] : mouvement;
  const p = interpolate(frame, [0, durationInFrames], [0, 1], {extrapolateRight: 'clamp'});
  const base = asset?.video ? 1.04 : 1.08;
  const echelle = !asset
    ? 1 + 0.05 * p // carton « à fournir » : mouvement léger, rien n'est coupé
    : m === 'serre' ? 1.32 + 0.06 * p : m === 'zoom-arriere' ? base + 0.14 - 0.12 * p : m === 'zoom-avant' ? base + 0.12 * p : base + 0.08;
  const x = !asset ? 0 : m === 'gauche' ? 50 - 100 * p : m === 'droite' ? -50 + 100 * p : m === 'serre' ? -60 : 0;
  const y = asset && m === 'serre' ? -30 : 0;

  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      <AbsoluteFill style={{transform: `scale(${echelle}) translate(${x}px, ${y}px)`}}>
        {asset ? (
          asset.video ? (
            <OffthreadVideo src={asset.src} muted style={{width: '100%', height: '100%', objectFit: 'cover', filter: filtreDossier}} />
          ) : (
            <Img src={asset.src} style={{width: '100%', height: '100%', objectFit: 'cover', filter: filtreDossier}} />
          )
        ) : (
          <Placeholder sceneId={assetId} description={description} genre={genre === 'video' ? 'VIDÉO' : genre === 'ia' ? 'IMAGE IA' : 'PHOTO'} />
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
