import {getStaticFiles, staticFile} from 'remotion';

const EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'mp4', 'mov', 'webm'];
let cache: Set<string> | null = null;

/**
 * Cherche le visuel d'une scène : d'abord TON fichier (assets/<ID>.ext), sinon celui trouvé
 * automatiquement (assets/auto/<ID>.ext). Renvoie undefined s'il n'existe pas encore.
 */
export const trouverAsset = (slug: string, id: string): {src: string; video: boolean} | undefined => {
  cache = cache ?? new Set(getStaticFiles().map((f) => f.name));
  for (const sous of ['', 'auto/']) {
    for (const ext of EXTENSIONS) {
      const nom = `videos/${slug}/assets/${sous}${id}.${ext}`;
      if (cache.has(nom)) return {src: staticFile(nom), video: ['mp4', 'mov', 'webm'].includes(ext)};
    }
  }
  return undefined;
};
