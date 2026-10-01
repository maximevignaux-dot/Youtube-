import {createContext, useContext} from 'react';
import {FPS} from '../theme/palette';

/** Infos communes à toute la vidéo (dossier en cours). */
export const ContexteVideo = createContext<{slug: string}>({slug: 'demo'});
export const useSlug = () => useContext(ContexteVideo).slug;

export const ms = (v: number) => Math.round((v / 1000) * FPS);
