import React from 'react';
import {AbsoluteFill} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';

/**
 * Remplace une image / vidéo manquante : carton papier crème, description tapée à la machine,
 * numéro de scène. L'aperçu reste regardable, et on voit tout de suite quoi fournir.
 */
export const Placeholder: React.FC<{sceneId: string; description: string; genre?: 'PHOTO' | 'VIDÉO' | 'IMAGE IA'}> = ({
  sceneId,
  description,
  genre = 'PHOTO',
}) => (
  <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
    <div
      style={{
        width: '78%',
        height: '72%',
        background: `linear-gradient(160deg, ${couleurs.papier} 0%, ${couleurs.papierOmbre} 100%)`,
        boxShadow: '0 30px 80px rgba(0,0,0,0.7)',
        transform: 'rotate(-1.2deg)',
        padding: '70px 90px',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        border: `2px dashed ${couleurs.cartonFonce}`,
      }}
    >
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline'}}>
        <span style={{fontFamily: anton, fontSize: 90, color: couleurs.encre}}>{sceneId}</span>
        <span style={{fontFamily: machine, fontSize: 34, color: couleurs.rouge, letterSpacing: 6}}>
          {genre} À FOURNIR
        </span>
      </div>
      <div style={{fontFamily: machine, fontSize: description.length > 120 ? 40 : 50, lineHeight: 1.3, color: couleurs.encre}}>{description}</div>
      <div style={{fontFamily: machine, fontSize: 26, color: couleurs.cartonFonce}}>
        → assets/{sceneId}.{genre === 'VIDÉO' ? 'mp4' : genre === 'IMAGE IA' ? 'png' : 'jpg'}
      </div>
    </div>
  </AbsoluteFill>
);
