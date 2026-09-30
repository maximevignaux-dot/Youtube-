// Copie /sfx, /musique et les fichiers des vidéos dans /public pour que Remotion puisse les lire.
// Lancé automatiquement avant le Studio et avant chaque rendu.
import {cpSync, existsSync, mkdirSync, readdirSync, rmSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';

const racine = fileURLToPath(new URL('..', import.meta.url));
const pub = join(racine, 'public');
rmSync(pub, {recursive: true, force: true});
mkdirSync(pub, {recursive: true});

for (const dossier of ['sfx', 'musique', 'polices']) {
  if (existsSync(join(racine, dossier))) cpSync(join(racine, dossier), join(pub, dossier), {recursive: true});
}
const videos = join(racine, 'videos');
for (const slug of existsSync(videos) ? readdirSync(videos) : []) {
  const src = join(videos, slug);
  const dst = join(pub, 'videos', slug);
  mkdirSync(dst, {recursive: true});
  for (const f of readdirSync(src)) {
    if (/^(voix.*\.(mp3|wav)|assets)$/.test(f)) cpSync(join(src, f), join(dst, f), {recursive: true});
  }
}
console.log('public/ prêt');
