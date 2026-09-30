import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Son} from './Son';

type Props = {
  montant: number;
  devise?: string;
  sens?: 'gain' | 'perte';
  libelle?: string; // ex. « FORTUNE ESTIMÉE »
  prefixe?: string; // ex. « + DE »
  debutComptage?: number; // frame où la compteuse démarre
  dureeComptage?: number; // en frames
};

const formater = (n: number) => Math.floor(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');

/** Montant qui défile comme sur une compteuse de billets. Vert = gains, rouge = pertes. */
export const CompteurBillets: React.FC<Props> = ({
  montant,
  devise = '€',
  sens = 'gain',
  libelle,
  prefixe,
  debutComptage = 6,
  dureeComptage = 45,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const couleur = sens === 'gain' ? couleurs.vert : couleurs.rouge;
  const p = interpolate(frame, [debutComptage, debutComptage + dureeComptage], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const valeur = montant * p;
  const texteFinal = formater(montant);
  // on garde la largeur finale pour que les chiffres ne « sautent » pas
  const chiffres = formater(valeur).padStart(texteFinal.length, ' ');
  const enCours = p > 0 && p < 1;
  const arrivee = frame - (debutComptage + dureeComptage);
  const pulse = arrivee >= 0 && arrivee < 10 ? 1 + 0.06 * Math.sin((arrivee / 10) * Math.PI) : 1;
  const zoom = interpolate(frame, [0, 4 * fps], [1, 1.06]);

  return (
    <AbsoluteFill style={{background: couleurs.noir, justifyContent: 'center', alignItems: 'center'}}>
      <Son nom="liasse" a={debutComptage} duree={dureeComptage + 4} volume={0.8} />
      {/* billets flous en fond */}
      <AbsoluteFill
        style={{
          background: `repeating-linear-gradient(100deg, ${couleur}22 0 40px, transparent 40px 90px)`,
          opacity: 0.5,
          transform: `translateX(${-frame * (enCours ? 14 : 2)}px) scale(1.4)`,
          filter: 'blur(6px)',
        }}
      />
      <div style={{transform: `scale(${zoom * pulse})`, textAlign: 'center'}}>
        {libelle ? (
          <div style={{fontFamily: machine, fontSize: 46, color: couleurs.papier, letterSpacing: 8, marginBottom: 24}}>
            {libelle}
          </div>
        ) : null}
        <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 24}}>
          {prefixe ? <span style={{fontFamily: anton, fontSize: 110, color: couleurs.papier}}>{prefixe}</span> : null}
          <div style={{display: 'flex', gap: 6}}>
            {chiffres.split('').map((c, i) =>
              c === ' ' ? (
                <span key={i} style={{width: 34}} />
              ) : (
                <span
                  key={i}
                  style={{
                    fontFamily: anton,
                    fontSize: 200,
                    lineHeight: 1,
                    color: couleur,
                    background: 'rgba(239,230,210,0.06)',
                    borderRadius: 10,
                    padding: '10px 8px',
                    minWidth: 104,
                    textAlign: 'center',
                    textShadow: `0 0 40px ${couleur}AA`,
                    filter: enCours && i > chiffres.length - 8 ? 'blur(2.5px)' : 'none',
                  }}
                >
                  {c}
                </span>
              ),
            )}
          </div>
          <span style={{fontFamily: anton, fontSize: 150, color: couleur}}>{devise}</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
