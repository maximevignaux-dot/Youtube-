import React from 'react';
import {AbsoluteFill, CalculateMetadataFunction, Img, staticFile} from 'remotion';
import {GrainVignette, Tampon} from './components';
import {trouverAsset, trouverDecoupe} from './lib/assets';
import {couleurs} from './theme/palette';
import {anton, machine} from './theme/polices';

type InfosMiniature = {tampon: string; chiffre: string | null; sujet: string; assetId: string | null; numero: number};
export type PropsMiniature = {slug: string; variante: number; infos?: InfosMiniature | null};

export const calculerMiniature: CalculateMetadataFunction<PropsMiniature> = async ({props}) => {
  const rep = await fetch(staticFile(`videos/${props.slug}/scenes.json`));
  const plan = await rep.json();
  return {props: {...props, infos: plan.miniature}};
};

/** Silhouette de remplacement tant qu'il n'y a pas de photo détourée. */
const Silhouette: React.FC<{taille: number}> = ({taille}) => (
  <svg width={taille} height={taille * 1.15} viewBox="0 0 200 230">
    <circle cx="100" cy="70" r="48" fill="#26221d" />
    <path d="M10 230 C 20 150, 60 128, 100 128 C 140 128, 180 150, 190 230 Z" fill="#26221d" />
  </svg>
);

const Sujet: React.FC<{slug: string; id: string | null; hauteur: number}> = ({slug, id, hauteur}) => {
  const decoupe = id ? trouverDecoupe(slug, id) : undefined;
  const photo = id ? trouverAsset(slug, id) : undefined;
  if (decoupe) return <Img src={decoupe} style={{height: hauteur, filter: 'contrast(1.15) saturate(0.85) drop-shadow(0 0 40px rgba(0,0,0,0.9))'}} />;
  if (photo && !photo.video)
    return (
      <Img
        src={photo.src}
        style={{height: hauteur, filter: 'contrast(1.15) saturate(0.8)', WebkitMaskImage: 'radial-gradient(ellipse 60% 70% at 50% 45%, #000 55%, transparent 75%)'}}
      />
    );
  return <Silhouette taille={hauteur * 0.85} />;
};

/** Miniature YouTube : fond noir, sujet détouré, tampon rouge en diagonale, 3 mots max, détail vert billet. */
export const Miniature: React.FC<PropsMiniature> = ({slug, variante, infos}) => {
  if (!infos) return null;
  const mots = infos.sujet.toUpperCase().split(/\s+/).slice(0, 3).join(' ');
  const chiffre = infos.chiffre ? (
    <div style={{fontFamily: anton, color: couleurs.vert, fontSize: 150, lineHeight: 1, textShadow: '0 0 40px rgba(31,138,91,0.6), 0 6px 0 #000'}}>{infos.chiffre}</div>
  ) : null;
  return (
    <AbsoluteFill style={{background: couleurs.noir, overflow: 'hidden'}}>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 70% 40%, #2a241c 0%, #0D0D0D 60%)'}} />
      {variante === 1 ? (
        <>
          <div style={{position: 'absolute', right: 40, bottom: 0}}><Sujet slug={slug} id={infos.assetId} hauteur={700} /></div>
          <div style={{position: 'absolute', left: 60, top: 140}}>
            <Tampon texte={infos.tampon} taille={170} rotation={-14} son={false} debut={-30} />
          </div>
          <div style={{position: 'absolute', left: 70, bottom: 60}}>{chiffre}</div>
        </>
      ) : variante === 2 ? (
        <>
          <div style={{position: 'absolute', left: -20, bottom: 0}}><Sujet slug={slug} id={infos.assetId} hauteur={720} /></div>
          <div style={{position: 'absolute', right: 60, top: 70, width: 620, textAlign: 'right'}}>
            <div style={{fontFamily: anton, fontSize: 130, lineHeight: 0.95, color: couleurs.papier, textShadow: '0 8px 0 #000'}}>{mots}</div>
            <div style={{marginTop: 30}}>{chiffre}</div>
          </div>
          <div style={{position: 'absolute', right: 70, bottom: 60}}>
            <Tampon texte={infos.tampon} taille={110} rotation={-10} son={false} debut={-30} />
          </div>
        </>
      ) : (
        <>
          <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, display: 'flex', justifyContent: 'center'}}>
            <Sujet slug={slug} id={infos.assetId} hauteur={680} />
          </div>
          <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
            <Tampon texte={infos.tampon} taille={230} rotation={-18} son={false} debut={-30} style={{background: 'rgba(13,13,13,0.35)'}} />
          </AbsoluteFill>
          <div style={{position: 'absolute', left: 50, top: 40}}>{chiffre}</div>
          <div style={{position: 'absolute', right: 50, top: 50, fontFamily: machine, fontSize: 40, color: couleurs.papier, letterSpacing: 6}}>
            DOSSIER N°{String(infos.numero).padStart(3, '0')}
          </div>
        </>
      )}
      <GrainVignette intensite={0.7} />
    </AbsoluteFill>
  );
};
