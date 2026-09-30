import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

// Polices embarquées dans /polices (copiées dans public/ au lancement) : aucun accès internet requis.
const charger = (famille: string, fichier: string, weight = '400') =>
  loadFont({family: famille, url: staticFile(`polices/${fichier}`), weight, format: 'woff2'});

charger('Anton', 'Anton.woff2');
charger('Special Elite', 'SpecialElite.woff2');
charger('Inter', 'Inter.woff2', '100 900');

// Titres et gros chiffres
export const anton = '"Anton", "Impact", sans-serif';
// Annotations, fiches, dates (machine à écrire)
export const machine = '"Special Elite", "Courier New", monospace';
// Texte courant
export const inter = '"Inter", "Helvetica Neue", Arial, sans-serif';
