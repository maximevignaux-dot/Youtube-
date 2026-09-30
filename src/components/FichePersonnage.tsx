import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {trouverAsset} from '../lib/assets';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {filtreDossier} from './Habillage';
import {Son} from './Son';
import {Tampon} from './Tampon';
import {Tape} from './Tape';

type Props = {
  slug: string;
  sceneId: string; // la photo est cherchée dans assets/<sceneId>.jpg
  descriptionPhoto: string;
  nom: string;
  role: string;
  fortune: string;
  statut: string;
  tampon: string; // « CONDAMNÉ », « EN FUITE », « MILLIARDAIRE »…
  couleurTampon?: string;
  debutTampon?: number; // frame (sinon : quand tous les champs sont tapés)
  lettresParSeconde?: number;
};

/** Fiche d'identification : photo agrafée de travers, champs tapés à la machine, tampon final. */
export const FichePersonnage: React.FC<Props> = ({
  slug,
  sceneId,
  descriptionPhoto,
  nom,
  role,
  fortune,
  statut,
  tampon,
  couleurTampon = couleurs.rouge,
  debutTampon,
  lettresParSeconde: LPS = 26,
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const photo = trouverAsset(slug, sceneId);
  const arrivee = interpolate(frame, [0, 10], [0, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.back(1.4))});
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.07]);

  // chaque champ commence quand le précédent est fini
  const champs = [
    {label: 'NOM', valeur: nom.toUpperCase()},
    {label: 'RÔLE', valeur: role},
    {label: 'FORTUNE', valeur: fortune},
    {label: 'STATUT', valeur: statut},
  ];
  let t = 8;
  const planning = champs.map((c) => {
    const debut = t;
    t += Math.ceil(((c.valeur.length + 2) / LPS) * fps);
    return {...c, debut};
  });
  const frappeTampon = debutTampon ?? t + 4;

  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <Son nom="feuille" volume={0.5} />
      <Son nom="machine-a-ecrire" a={8} duree={t - 8} volume={0.55} boucle />
      <div
        style={{
          position: 'relative',
          width: 1500,
          height: 820,
          background: `linear-gradient(165deg, #E4D3AE, ${couleurs.carton})`,
          boxShadow: '0 40px 120px rgba(0,0,0,0.85)',
          transform: `translateY(${(1 - arrivee) * 300}px) rotate(${-1.5 + arrivee * 0.5}deg) scale(${zoom})`,
          display: 'flex',
          padding: 70,
          boxSizing: 'border-box',
          gap: 70,
        }}
      >
        {/* photo agrafée de travers */}
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
                  fontSize: 28,
                  color: couleurs.encre,
                  padding: 26,
                  boxSizing: 'border-box',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'center',
                  gap: 20,
                }}
              >
                <span style={{fontFamily: anton, fontSize: 48}}>{sceneId}</span>
                <span>PHOTO À FOURNIR :</span>
                <span>{descriptionPhoto}</span>
              </div>
            )}
          </div>
          {/* agrafe */}
          <div style={{position: 'absolute', top: -8, left: 200, width: 90, height: 14, border: '4px solid #9a9a9a', borderBottom: 'none', borderRadius: 3}} />
        </div>
        {/* champs */}
        <div style={{flex: 1, fontFamily: machine, color: couleurs.encre, paddingTop: 20}}>
          <div style={{fontFamily: anton, fontSize: 44, letterSpacing: 6, opacity: 0.6, marginBottom: 30}}>FICHE D'IDENTIFICATION</div>
          {planning.map((c) => (
            <div key={c.label} style={{marginBottom: 34}}>
              <div style={{fontSize: 28, opacity: 0.65, letterSpacing: 4}}>{c.label}</div>
              <div style={{fontSize: c.label === 'NOM' ? 70 : 46, borderBottom: `2px dotted ${couleurs.encre}55`, minHeight: 60}}>
                <Tape texte={c.valeur} debut={c.debut} lettresParSeconde={LPS} />
              </div>
            </div>
          ))}
        </div>
        <div style={{position: 'absolute', right: 110, bottom: 90}}>
          <Tampon texte={tampon} couleur={couleurTampon} taille={96} rotation={-14} debut={frappeTampon} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
