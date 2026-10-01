import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {trouverAsset} from '../lib/assets';
import {useSlug} from '../lib/contexte';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {filtreDossier} from './Habillage';
import {Son} from './Son';
import {Tampon} from './Tampon';
import {Tape} from './Tape';

export type Champ = {label: string; valeur: string};

type Props = {
  assetId: string; // photo cherchée dans assets/<assetId>.jpg
  descriptionPhoto: string;
  nom: string;
  champs: Champ[];
  tampon?: string | null; // « CONDAMNÉ », « EN FUITE », « MILLIARDAIRE »…
  couleurTampon?: string;
  lettresParSeconde?: number;
};

/** Fiche d'identification : photo agrafée de travers, champs tapés à la machine, tampon final. */
export const FichePersonnage: React.FC<Props> = ({
  assetId,
  descriptionPhoto,
  nom,
  champs,
  tampon,
  couleurTampon = couleurs.rouge,
  lettresParSeconde: LPS = 24,
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const slug = useSlug();
  const photo = trouverAsset(slug, assetId);
  const arrivee = interpolate(frame, [0, 12], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.back(1.3))});
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.06]);

  const lignes = [{label: 'NOM', valeur: nom.toUpperCase()}, ...champs];
  // le nom tout de suite, puis chaque champ quand le précédent est tapé (avec une petite respiration)
  let t = 10;
  const planning = lignes.map((c) => {
    const debut = t;
    t += Math.ceil(((c.valeur.length + 4) / LPS) * fps) + 4;
    return {...c, debut};
  });
  const frappeTampon = Math.min(t + 6, Math.max(t, durationInFrames - 40));
  const grandNom = nom.length > 18 ? 58 : 74;

  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <Son nom="feuille" volume={0.5} />
      <Son nom="machine-a-ecrire" a={10} duree={Math.max(1, t - 10)} volume={0.45} boucle />
      <div
        style={{
          position: 'relative',
          width: 1520,
          height: 840,
          background: `linear-gradient(165deg, #E4D3AE, ${couleurs.carton})`,
          boxShadow: '0 40px 120px rgba(0,0,0,0.85)',
          transform: `translateY(${(1 - arrivee) * 300}px) rotate(${-1.5 + arrivee * 0.5}deg) scale(${zoom})`,
          display: 'flex',
          padding: 70,
          boxSizing: 'border-box',
          gap: 70,
        }}
      >
        <div style={{position: 'relative', transform: 'rotate(-4deg)', flexShrink: 0}}>
          <div style={{width: 470, height: 600, background: '#fff', padding: 18, boxShadow: '0 12px 30px rgba(0,0,0,0.45)'}}>
            {photo ? (
              <Img src={photo.src} style={{width: '100%', height: '100%', objectFit: 'cover', filter: `${filtreDossier} grayscale(0.6)`}} />
            ) : (
              <div
                style={{
                  width: '100%',
                  height: '100%',
                  background: couleurs.papierOmbre,
                  fontFamily: machine,
                  fontSize: 27,
                  color: couleurs.encre,
                  padding: 26,
                  boxSizing: 'border-box',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  gap: 18,
                }}
              >
                <span style={{fontFamily: anton, fontSize: 52}}>{assetId}</span>
                <span style={{color: couleurs.rouge}}>PHOTO À FOURNIR</span>
                <span>{descriptionPhoto.length > 150 ? descriptionPhoto.slice(0, 147) + '…' : descriptionPhoto}</span>
              </div>
            )}
          </div>
          <div style={{position: 'absolute', top: -8, left: 200, width: 90, height: 14, border: '4px solid #9a9a9a', borderBottom: 'none', borderRadius: 3}} />
        </div>
        <div style={{flex: 1, fontFamily: machine, color: couleurs.encre, paddingTop: 10, minWidth: 0}}>
          <div style={{fontFamily: anton, fontSize: 40, letterSpacing: 6, opacity: 0.55, marginBottom: 26}}>FICHE D'IDENTIFICATION</div>
          {planning.map((c) => (
            <div key={c.label} style={{marginBottom: 28}}>
              <div style={{fontSize: 26, opacity: 0.6, letterSpacing: 4}}>{c.label}</div>
              <div style={{fontSize: c.label === 'NOM' ? grandNom : 44, lineHeight: 1.15, borderBottom: `2px dotted ${couleurs.encre}55`, minHeight: 56}}>
                <Tape texte={c.valeur} debut={c.debut} lettresParSeconde={c.label === 'NOM' ? LPS * 1.3 : LPS} />
              </div>
            </div>
          ))}
        </div>
        {tampon ? (
          <div style={{position: 'absolute', right: 100, bottom: 70}}>
            <Tampon texte={tampon} couleur={couleurTampon} taille={tampon.length > 10 ? 72 : 96} rotation={-14} debut={frappeTampon} />
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
