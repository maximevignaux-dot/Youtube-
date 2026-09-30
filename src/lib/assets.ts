import {getStaticFiles, staticFile} from 'remotion';

const EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'mp4', 'mov', 'webm'];

/** Cherche videos/<slug>/assets/<sceneId>.<ext> ; renvoie undefined si le fichier n'existe pas encore. */
export const trouverAsset = (slug: string, sceneId: string): {src: string; video: boolean} | undefined => {
  const fichiers = new Set(getStaticFiles().map((f) => f.name));
  for (const ext of EXTENSIONS) {
    const nom = `videos/${slug}/assets/${sceneId}.${ext}`;
    if (fichiers.has(nom)) return {src: staticFile(nom), video: ['mp4', 'mov', 'webm'].includes(ext)};
  }
  return undefined;
};
