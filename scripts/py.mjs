// Lance un script Python avec « python3 » (Mac/Linux) ou « python » (Windows).
import {spawnSync} from 'node:child_process';

const args = process.argv.slice(2);
for (const exe of ['python3', 'python', 'py']) {
  const r = spawnSync(exe, args, {stdio: 'inherit'});
  if (r.error?.code === 'ENOENT') continue;
  process.exit(r.status ?? 1);
}
console.error('Python introuvable : installe-le depuis https://www.python.org/downloads');
process.exit(1);
