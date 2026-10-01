import {geoMercator, geoPath} from 'd3-geo';
import type {Feature, FeatureCollection, Geometry} from 'geojson';
import React, {useMemo} from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {feature} from 'topojson-client';
import monde from 'world-atlas/countries-50m.json';
import {ms} from '../lib/contexte';
import {couleurs} from '../theme/palette';
import {anton, machine} from '../theme/polices';
import {Son} from './Son';

type Point = {nom: string; lon: number; lat: number; secondaire?: boolean};
type Pays = {nom: string; aMs: number; clic?: boolean};

type Props = {
  points: Point[];
  flux: [number, number][];
  pays: Pays[];
  regions: string[];
  zoom?: Point | null;
  accent?: 'vert' | 'rouge';
  debutSceneMs?: number;
};

const REGIONS: Record<string, [number, number, number, number]> = {
  afrique: [-20, -36, 53, 38],
  europe: [-12, 35, 30, 60],
  france: [-5.5, 41.2, 9.8, 51.3],
  monde: [-170, -58, 180, 80],
  suisse: [5.8, 45.7, 10.6, 47.9],
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const PAYS_GEO = feature(monde as any, (monde as any).objects.countries) as unknown as FeatureCollection<Geometry, {name: string}>;
const L = 1920;
const H = 1080;

/** Emprise à afficher : régions demandées + points + pays allumés, avec une marge. */
const emprise = (props: Props): [number, number, number, number] => {
  const boites: [number, number, number, number][] = props.regions.filter((r) => REGIONS[r]).map((r) => REGIONS[r]);
  const xs: number[] = [];
  const ys: number[] = [];
  props.points.forEach((p) => {
    xs.push(p.lon);
    ys.push(p.lat);
  });
  for (const b of boites) {
    xs.push(b[0], b[2]);
    ys.push(b[1], b[3]);
  }
  if (!xs.length) {
    const pg = PAYS_GEO.features.filter((f) => props.pays.some((p) => p.nom === f.properties.name));
    if (pg.length) {
      const [[a, b], [c, d]] = geoPath().bounds({type: 'FeatureCollection', features: pg} as FeatureCollection);
      return [a - 6, b - 6, c + 6, d + 6];
    }
    return REGIONS.monde;
  }
  let [o, s, e, n] = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  const mx = Math.max(3, (e - o) * 0.18);
  const my = Math.max(2, (n - s) * 0.18);
  o -= mx;
  e += mx;
  s -= my;
  n += my;
  return [o, s, e, n];
};

/** Carte sombre « ancienne » : pays qui s'allument au mot exact, flux d'argent en pointillés verts. */
export const CarteFlux: React.FC<Props> = (props) => {
  const {points, flux, pays, zoom, accent = 'vert', debutSceneMs = 0} = props;
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const couleurAccent = accent === 'rouge' ? couleurs.rouge : couleurs.vert;

  const {chemins, projetes} = useMemo(() => {
    const [o, s, e, n] = emprise(props);
    const cadre: Feature = {
      type: 'Feature',
      properties: {},
      geometry: {type: 'MultiPoint', coordinates: [[o, s], [e, n], [o, n], [e, s]]},
    };
    const proj = geoMercator().fitExtent([[120, 100], [L - 120, H - 100]], cadre);
    const chemin = geoPath(proj);
    return {
      chemins: PAYS_GEO.features.map((f) => ({nom: f.properties.name, d: chemin(f) ?? ''})).filter((c) => c.d),
      projetes: points.map((p) => proj([p.lon, p.lat]) ?? [0, 0]),
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(props)]);

  // caméra : léger travelling, ou zoom vers un point précis
  let echelle = interpolate(frame, [0, durationInFrames], [1, 1.07]);
  let tx = 0;
  let ty = 0;
  if (zoom) {
    const idx = points.findIndex((p) => p.nom === zoom.nom);
    const [zx, zy] = projetes[idx] ?? [L / 2, H / 2];
    const p = interpolate(frame, [20, 70], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
    echelle = 1 + 2.2 * p;
    tx = (L / 2 - zx) * p;
    ty = (H / 2 - zy) * p;
  }

  const allume = (nom: string) => {
    const p = pays.find((x) => x.nom === nom);
    if (!p) return 0;
    const a = Math.max(0, ms(p.aMs - debutSceneMs));
    return interpolate(frame, [a, a + 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  };

  return (
    <AbsoluteFill style={{background: '#0B0F0D'}}>
      {pays.filter((p) => p.clic).map((p) => (
        <Son key={p.nom} nom="frappe" a={Math.max(0, ms(p.aMs - debutSceneMs))} volume={0.7} />
      ))}
      {flux.length ? <Son nom="feuille" a={10} volume={0.4} /> : null}
      <svg width={L} height={H} style={{position: 'absolute', transform: `translate(${tx}px, ${ty}px) scale(${echelle})`, transformOrigin: `${L / 2 - tx}px ${H / 2 - ty}px`}}>
        <defs>
          <pattern id="quadrillage" width="60" height="60" patternUnits="userSpaceOnUse">
            <path d="M 60 0 L 0 0 0 60" fill="none" stroke={couleurs.papier} strokeOpacity="0.05" strokeWidth="1" />
          </pattern>
        </defs>
        <rect x={-L} y={-H} width={L * 3} height={H * 3} fill="url(#quadrillage)" />
        {chemins.map((c) => {
          const a = allume(c.nom);
          return (
            <path
              key={c.nom}
              d={c.d}
              fill={a > 0 ? couleurAccent : '#2A2620'}
              fillOpacity={a > 0 ? 0.35 + 0.5 * a : 1}
              stroke={a > 0 ? couleurs.papier : '#5A5145'}
              strokeWidth={(a > 0 ? 1.6 : 0.8) / echelle}
            />
          );
        })}
        {flux.map(([i, j], k) => {
          const [x1, y1] = projetes[i] ?? [0, 0];
          const [x2, y2] = projetes[j] ?? [0, 0];
          const mx = (x1 + x2) / 2;
          const my = (y1 + y2) / 2 - Math.hypot(x2 - x1, y2 - y1) * 0.25;
          const d = `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`;
          const debut = 12 + k * 8;
          const p = interpolate(frame, [debut, debut + 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.quad)});
          return (
            <g key={k}>
              <mask id={`trace-${k}`}>
                <path d={d} fill="none" stroke="#fff" strokeWidth={14 / echelle} pathLength={1000} strokeDasharray="1000 1000" strokeDashoffset={1000 * (1 - p)} />
              </mask>
              <path d={d} fill="none" stroke={couleurs.vert} strokeWidth={5 / echelle} strokeDasharray={`${14 / echelle} ${12 / echelle}`}
                strokeDashoffset={-frame * 1.5} mask={`url(#trace-${k})`} />
              {p >= 1 ? <circle cx={x2} cy={y2} r={10 / echelle} fill={couleurs.vert} /> : null}
            </g>
          );
        })}
        {points.filter((p) => !p.secondaire).map((p) => {
          const k = points.indexOf(p);
          const [x, y] = projetes[k];
          const pulse = 1 + 0.25 * Math.sin(frame / 6);
          return (
            <g key={p.nom + k}>
              <circle cx={x} cy={y} r={(16 * pulse) / echelle} fill={couleurs.rouge} opacity={0.35} />
              <circle cx={x} cy={y} r={8 / echelle} fill={couleurs.rouge} />
              <text x={x + 18 / echelle} y={y - 14 / echelle} fill={couleurs.papier} fontFamily={machine} fontSize={40 / echelle}
                style={{paintOrder: 'stroke', stroke: '#0B0F0D', strokeWidth: 8 / echelle}}>
                {p.nom}
              </text>
            </g>
          );
        })}
      </svg>
      {/* compteur de pays allumés */}
      {pays.length > 1 ? (
        <div style={{position: 'absolute', right: 90, bottom: 80, fontFamily: anton, fontSize: 90, color: couleurAccent, textAlign: 'right'}}>
          {pays.filter((p) => allume(p.nom) > 0.5).length}
          <div style={{fontFamily: machine, fontSize: 30, color: couleurs.papier, letterSpacing: 6}}>PAYS</div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
