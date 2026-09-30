import React from 'react';
import {AbsoluteFill, Img, interpolate, OffthreadVideo, useCurrentFrame, useVideoConfig} from 'remotion';
import {trouverAsset} from '../lib/assets';
import {filtreDossier} from './Habillage';
import {couleurs} from '../theme/palette';
import {machine} from '../theme/polices';
import {Placeholder} from './Placeholder';
import {Son} from './Son';
import {Tape} from './Tape';

export type Mouvement = 'zoom-avant' | 'zoom-arriere' | 'gauche' | 'droite';

type Props = {
  slug: string;
  sceneId: string;
  description: string;
  mouvement?: Mouvement;
  legende?: string; // petite légende tapée à la machine en bas à gauche
};

/** Photo (ou clip) plein écran avec mouvement permanent. Placeholder si l'asset manque. */
export const PhotoKenBurns: React.FC<Props> = ({slug, sceneId, description, mouvement = 'zoom-avant', legende}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const p = interpolate(frame, [0, durationInFrames], [0, 1], {extrapolateRight: 'clamp'});
  const echelle = mouvement === 'zoom-arriere' ? 1.2 - 0.12 * p : mouvement === 'zoom-avant' ? 1.06 + 0.12 * p : 1.14;
  const x = mouvement === 'gauche' ? 40 - 80 * p : mouvement === 'droite' ? -40 + 80 * p : 0;
  const asset = trouverAsset(slug, sceneId);

  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#000'}}>
      <AbsoluteFill style={{transform: `scale(${echelle}) translateX(${x}px)`}}>
        {asset ? (
          asset.video ? (
            <OffthreadVideo src={asset.src} muted style={{width: '100%', height: '100%', objectFit: 'cover', filter: filtreDossier}} />
          ) : (
            <Img src={asset.src} style={{width: '100%', height: '100%', objectFit: 'cover', filter: filtreDossier}} />
          )
        ) : (
          <Placeholder sceneId={sceneId} description={description.replace(/^VIDÉO\s*:\s*/i, '')} genre={/^VIDÉO/i.test(description) ? 'VIDÉO' : 'PHOTO'} />
        )}
      </AbsoluteFill>
      {legende ? <LegendeMachine texte={legende} /> : null}
    </AbsoluteFill>
  );
};

const LegendeMachine: React.FC<{texte: string}> = ({texte}) => (
  <div
    style={{
      position: 'absolute',
      left: 90,
      bottom: 90,
      background: couleurs.papier,
      color: couleurs.encre,
      fontFamily: machine,
      fontSize: 40,
      padding: '10px 22px',
      transform: 'rotate(-1.5deg)',
      boxShadow: '0 10px 30px rgba(0,0,0,0.6)',
    }}
  >
    <Son nom="machine-a-ecrire" a={4} volume={0.5} duree={Math.ceil(texte.length / 22 * 30)} />
    <Tape texte={texte} debut={4} />
  </div>
);
