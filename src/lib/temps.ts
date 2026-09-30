import {FPS} from '../theme/palette';

export type MotHorodate = {mot: string; debut: number; fin: number};
export type Horodatage = {moteur?: string; dureeMs: number; mots: MotHorodate[]};

export const msEnFrames = (ms: number) => Math.round((ms / 1000) * FPS);
export const secondes = (s: number) => Math.round(s * FPS);

// « s'appelle » → « appelle », « Soixante-dix » → « soixantedix », accents retirés.
const normaliser = (mot: string) =>
  (mot.toLowerCase().split(/['’]/).pop() ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]/g, '');

/**
 * Renvoie une fonction qui trouve, dans l'ordre du texte, le moment (en frames)
 * où un mot est prononcé. Chaque appel reprend la recherche après le mot précédent.
 */
export const curseurDeMots = (h: Horodatage) => {
  let i = 0;
  return (ancre: string): number => {
    const cible = normaliser(ancre);
    for (let j = i; j < h.mots.length; j++) {
      if (normaliser(h.mots[j].mot).startsWith(cible)) {
        i = j + 1;
        return msEnFrames(h.mots[j].debut);
      }
    }
    throw new Error(`Mot « ${ancre} » introuvable dans la voix (après le mot n°${i}).`);
  };
};
