// "Neural shell": a particle body where every top-volume coin owns a cluster
// of needles. Needle length = |24h change|, density = volume, colour = direction,
// glow = live trade pulses. Also draws the 2D overlay wires to the HUD cards.
// Skins: torus / globe (Natural Earth land mask) / galaxy. Every particle and
// needle has a position on all three shapes; switching skins morphs between them.
import * as THREE from 'three';
import { base as baseOf, pct } from './fmt.js';
import { isLand } from './landmask.js';

const NC = 48;          // max clusters
const K = 30;           // needles per cluster
const TR = 3.0, Tr = 1.3;
const NU = 220, NV = 44; // base particle grid
const RS = 3.3;           // globe radius
const GAL_R = 4.4;        // galaxy outer radius
export const SKINS = ['torus', 'globe', 'galaxy'];

const COMMON = /* glsl */`
#define NC ${NC}
uniform float uTime;
uniform vec4 uCl[NC];
uniform float uPulse[NC];
uniform float uSel;
uniform float uPx;
uniform float uWT, uWG, uWX;   // skin weights: torus, globe, galaxy
uniform vec2 uClG[NC];         // cluster lon/lat on the globe
uniform vec2 uClX[NC];         // cluster angle/radius on the galaxy
const float TR = ${TR.toFixed(2)};
const float Tr = ${Tr.toFixed(2)};
const float RS = ${RS.toFixed(2)};
vec3 gnorm(float lon, float lat) { return vec3(cos(lat) * sin(lon), sin(lat), cos(lat) * cos(lon)); }
vec3 xpos(float a, float r) { return vec3(r * cos(a), 0.0, r * sin(a)); }
vec3 tnorm(float u, float v) { return vec3(cos(v) * cos(u), sin(v), cos(v) * sin(u)); }
vec3 tpos(float u, float v, float rr) { return vec3(TR * cos(u), 0.0, TR * sin(u)) + rr * tnorm(u, v); }
float wob(float u, float v) {
  return 0.035 * sin(3.0 * u + 2.0 * v + uTime * 0.6)
       + 0.030 * sin(5.0 * v - uTime * 0.8 + 2.0 * u)
       + 0.020 * sin(7.0 * u - uTime * 0.45);
}
vec2 adiff(vec2 a, vec2 b) { vec2 d = a - b; return atan(sin(d), cos(d)); }
varying vec3 vCol;
varying float vA;
`;

const BASE_VS = COMMON + /* glsl */`
attribute vec2 aUV;
attribute float aSeed;
attribute vec2 aGeo;   // lon, lat (radians)
attribute float aLand;
attribute vec2 aGal;   // angle, radius
void main() {
  float u = aUV.x, v = aUV.y;
  vec3 nG = gnorm(aGeo.x, aGeo.y);
  vec3 pX0 = xpos(aGal.x, aGal.y);
  float heat = 0.0, sg = 0.0, pl = 0.0, sel = 0.0;
  for (int i = 0; i < NC; i++) {
    vec4 c = uCl[i];
    if (c.z <= 0.0) continue;
    float g = 0.0;
    if (uWT > 0.001) { vec2 d = adiff(vec2(u, v), c.xy); d.x *= 2.6; g += uWT * exp(-dot(d, d) * 18.0); }
    if (uWG > 0.001) { g += uWG * exp(-(1.0 - dot(nG, gnorm(uClG[i].x, uClG[i].y))) * 90.0); }
    if (uWX > 0.001) { vec3 dd = pX0 - xpos(uClX[i].x, uClX[i].y); g += uWX * exp(-dot(dd, dd) * 10.0); }
    heat += g * c.z; sg += g * c.w; pl += g * uPulse[i];
    if (float(i) == uSel) sel += g;
  }
  // the galaxy arms are dense, so damp the cluster glow there to avoid white blobs
  float hx = 1.0 - 0.6 * uWX;
  heat = min(heat, 1.2) * hx;
  pl = min(pl, 1.6) * hx * hx;
  float lift = heat * 0.07 + pl * 0.10;
  vec3 pT = tpos(u, v, Tr + wob(u, v) + lift);
  vec3 pG = nG * (RS + lift + (1.0 - aLand) * 0.015 * sin(uTime * 0.8 + aSeed * 30.0));
  float thick = (aSeed - 0.5) * 0.32 * (1.25 - aGal.y / ${GAL_R.toFixed(1)});
  vec3 pX = pX0 + vec3(0.0, thick + lift, 0.0);
  vec3 p = pT * uWT + pG * uWG + pX * uWX;
  vec3 n = normalize(tnorm(u, v) * uWT + nG * uWG + vec3(0.0, 1.0, 0.0) * uWX + vec3(1e-5));
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  float facing = dot(normalize(normalMatrix * n), normalize(-mv.xyz));
  float tw = 0.65 + 0.35 * sin(uTime * (1.5 + aSeed * 2.0) + aSeed * 60.0);
  vec3 coldT = mix(vec3(0.30, 0.50, 1.0), vec3(0.82, 0.91, 1.0), aSeed * aSeed);
  vec3 coldG = aLand > 0.5 ? mix(vec3(0.30, 0.78, 1.0), vec3(0.86, 0.97, 1.0), aSeed) : vec3(0.10, 0.22, 0.58);
  vec3 coldX = mix(vec3(1.0, 0.82, 0.55), mix(vec3(0.45, 0.62, 1.0), vec3(0.78, 0.55, 1.0), aSeed), clamp(aGal.y / 2.2, 0.0, 1.0));
  vec3 cold = coldT * uWT + coldG * uWG + coldX * uWX;
  vec3 hot = sg >= 0.0 ? vec3(1.0, 0.74, 0.24) : vec3(1.0, 0.34, 0.46);
  vCol = mix(cold, hot, clamp(heat * 1.3, 0.0, 0.85)) + vec3(pl * 0.8) + sel * vec3(0.1, 0.6, 0.8);
  float ocean = uWG * (1.0 - aLand);
  // the globe's far side is almost hidden so the continents read clearly
  float backFade = mix(0.16, 0.0, uWG);
  vA = (backFade + (1.0 - backFade) * smoothstep(mix(-0.35, -0.05, uWG), 0.45, facing)) * tw * (1.0 - ocean * 0.78);
  vA *= 1.0 + uWG * aLand * 0.35;
  // galaxy: dimmer, smaller particles towards the dense core so it doesn't blow out to white
  float core = 1.0 - clamp(aGal.y / 2.0, 0.0, 1.0);
  if (uWX > 0.001) vA = mix(vA, (0.32 + 0.3 * tw) * (1.0 - core * 0.55), uWX);
  float sz = (0.75 + 0.5 * aSeed + heat * 0.9 + pl * 1.6) * (1.0 - ocean * 0.5) * (1.0 - uWX * core * 0.45);
  gl_PointSize = uPx * sz / -mv.z;
}`;

const NEEDLE_VS = COMMON + /* glsl */`
attribute vec2 aOff;
attribute float aEnd;
attribute float aCl;
attribute float aRand;
attribute float aK;
void main() {
  int ci = int(aCl + 0.5);
  vec4 c = uCl[ci];
  float pulse = min(uPulse[ci], 1.5);
  float vis = (c.z > 0.0 && aK <= c.z) ? 1.0 : 0.0;
  float flick = 0.82 + 0.18 * sin(uTime * (1.8 + aRand * 3.0) + aRand * 40.0);
  float len = (0.08 + 0.95 * abs(c.w)) * (0.25 + 0.75 * aRand * aRand) * flick * (1.0 + pulse * 0.8) * vis;
  vec2 dd = aOff * vec2(2.6, 1.0);
  float bump = c.z * 0.07 * exp(-dot(dd, dd) * 18.0);
  // torus
  float u = c.x + aOff.x, v = c.y + aOff.y;
  vec3 nT = tnorm(u, v);
  vec3 pT = tpos(u, v, Tr + wob(u, v) + bump + 0.015 + len * aEnd);
  // globe
  vec2 gc = uClG[ci];
  float lat = gc.y + dd.y * 0.55;
  float lon = gc.x + dd.x * 0.55 / max(cos(lat), 0.3);
  vec3 nG = gnorm(lon, lat);
  vec3 pG = nG * (RS + bump + 0.015 + len * aEnd);
  // galaxy
  vec2 xc = uClX[ci];
  vec3 pX = xpos(xc.x + dd.x * 0.5 / max(xc.y, 0.8), xc.y + dd.y * 0.7) + vec3(0.0, 0.02 + bump + len * aEnd, 0.0);
  vec3 p = pT * uWT + pG * uWG + pX * uWX;
  vec3 n = normalize(nT * uWT + nG * uWG + vec3(0.0, 1.0, 0.0) * uWX + vec3(1e-5));
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  float facing = dot(normalize(normalMatrix * n), normalize(-mv.xyz));
  vec3 tip = c.w >= 0.0 ? vec3(0.16, 1.0, 0.62) : vec3(1.0, 0.28, 0.42);
  vec3 col = mix(vec3(1.0, 0.66, 0.18), tip, aEnd * 0.85);
  if (float(ci) == uSel) col = mix(col, vec3(0.45, 0.92, 1.0), 0.65);
  vCol = col + vec3(min(pulse, 1.0) * 0.5);
  float back = mix(0.25, 0.06, uWG);
  vA = vis * (0.22 + 0.78 * aEnd) * (back + (1.0 - back) * smoothstep(-0.4, 0.4, facing));
  if (uWX > 0.001) vA = mix(vA, vis * (0.3 + 0.7 * aEnd), uWX);
  gl_PointSize = uPx * (1.1 + pulse) / -mv.z;
}`;

const LINE_FS = /* glsl */`
varying vec3 vCol; varying float vA;
void main() { gl_FragColor = vec4(vCol, vA); }`;

const POINT_FS = /* glsl */`
varying vec3 vCol; varying float vA;
void main() {
  vec2 c = gl_PointCoord - 0.5;
  float d = length(c);
  if (d > 0.5) discard;
  gl_FragColor = vec4(vCol, pow(1.0 - d * 2.0, 1.6) * vA);
}`;

function slotLayout() {
  const slots = [];
  for (let i = 0; i < NC; i++) {
    const u = 2 * Math.PI * ((i * 0.6180339887 + 0.13) % 1);
    const v = -1.0 + 3.4 * ((i + 0.5) / NC); // lower-outer → top → upper-inner
    // globe: golden-angle spiral between ~50°S and ~62°N
    const lat = Math.asin(-0.76 + 1.64 * ((i + 0.5) / NC));
    const lon = ((i * 2.399963) % (Math.PI * 2)) - Math.PI;
    // galaxy: along three spiral arms
    const arm = i % 3, r = 1.0 + 3.2 * ((Math.floor(i / 3) + 0.5) / (NC / 3));
    const ga = arm * (Math.PI * 2 / 3) + r * 1.15;
    slots.push({ u, v, lon, lat, ga, gr: r });
  }
  // most prominent slots (upper-outer face) first
  const order = slots.map((s, i) => i).sort((a, b) => Math.abs(slots[a].v - 0.55) - Math.abs(slots[b].v - 0.55));
  return { slots, order };
}

function softDot() {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.3, 'rgba(255,255,255,.5)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
// signed needle scale: sqrt so that ±4% is visible and +300% outliers don't explode
const needle = (chg) => Math.sign(chg) * Math.min(1, Math.sqrt(Math.abs(chg || 0) / 30));

export function createShell(wrap, { onPick, onHover } = {}) {
  const canvas = wrap.querySelector('#cv-shell');
  const over = wrap.querySelector('#cv-wires');
  const labelsEl = wrap.querySelector('#shell-labels');
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  } catch (e) {
    return null; // no WebGL2
  }
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  renderer.setPixelRatio(dpr);
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 200);
  const group = new THREE.Group();
  scene.add(group);

  const { slots, order } = slotLayout();
  const uniforms = {
    uTime: { value: 0 },
    uCl: { value: Array.from({ length: NC }, () => new THREE.Vector4(0, 0, 0, 0)) },
    uPulse: { value: new Float32Array(NC) },
    uSel: { value: -1 },
    uPx: { value: 36 * dpr },
    uWT: { value: 1 }, uWG: { value: 0 }, uWX: { value: 0 },
    uClG: { value: slots.map((s) => new THREE.Vector2(s.lon, s.lat)) },
    uClX: { value: slots.map((s) => new THREE.Vector2(s.ga, s.gr)) },
  };
  const additive = { transparent: true, depthWrite: false, blending: THREE.AdditiveBlending };

  // --- base particle skin
  {
    const n = NU * NV, uv = new Float32Array(n * 2), seed = new Float32Array(n), pos = new Float32Array(n * 3);
    const geo = new Float32Array(n * 2), land = new Float32Array(n), gal = new Float32Array(n * 2);
    let k = 0;
    for (let i = 0; i < NU; i++) for (let j = 0; j < NV; j++, k++) {
      uv[k * 2] = ((i + Math.random()) / NU) * Math.PI * 2;
      uv[k * 2 + 1] = ((j + Math.random()) / NV) * Math.PI * 2;
      seed[k] = Math.random();
    }
    // globe: 80% of the particles on land (≈8× denser than the oceans)
    for (k = 0; k < n; k++) {
      const wantLand = Math.random() < 0.8;
      let lon, lat, l, tries = 0;
      do {
        lon = Math.random() * 360 - 180;
        lat = (Math.asin(2 * Math.random() - 1) * 180) / Math.PI;
        l = isLand(lon, lat);
      } while (l !== wantLand && ++tries < 40);
      geo[k * 2] = (lon * Math.PI) / 180; geo[k * 2 + 1] = (lat * Math.PI) / 180; land[k] = l ? 1 : 0;
    }
    // galaxy: three logarithmic-ish arms + a diffuse disc + a bright bulge
    for (k = 0; k < n; k++) {
      const q = Math.random();
      let r, a;
      if (q < 0.14) { r = 0.15 + 0.9 * Math.pow(Math.random(), 1.6); a = Math.random() * Math.PI * 2; }
      else if (q < 0.32) { r = 0.6 + (GAL_R - 0.6) * Math.sqrt(Math.random()); a = Math.random() * Math.PI * 2; }
      else {
        r = 0.6 + (GAL_R - 0.6) * Math.pow(Math.random(), 0.85);
        const arm = k % 3, spread = (Math.random() + Math.random() + Math.random() - 1.5) * (0.22 + 0.1 * r);
        a = arm * (Math.PI * 2 / 3) + r * 1.15 + spread;
      }
      gal[k * 2] = a; gal[k * 2 + 1] = r;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('aUV', new THREE.BufferAttribute(uv, 2));
    g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
    g.setAttribute('aGeo', new THREE.BufferAttribute(geo, 2));
    g.setAttribute('aLand', new THREE.BufferAttribute(land, 1));
    g.setAttribute('aGal', new THREE.BufferAttribute(gal, 2));
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 8);
    group.add(new THREE.Points(g, new THREE.ShaderMaterial({ uniforms, vertexShader: BASE_VS, fragmentShader: POINT_FS, ...additive })));
  }

  // --- needles (lines) + needle tips (points)
  {
    const nv = NC * K * 2;
    const off = new Float32Array(nv * 2), end = new Float32Array(nv), cl = new Float32Array(nv), rnd = new Float32Array(nv), kk = new Float32Array(nv);
    const tOff = new Float32Array(NC * K * 2), tEnd = new Float32Array(NC * K), tCl = new Float32Array(NC * K), tRnd = new Float32Array(NC * K), tK = new Float32Array(NC * K);
    let p = 0, q = 0;
    for (let c = 0; c < NC; c++) for (let s = 0; s < K; s++) {
      const a = Math.random() * Math.PI * 2, rho = 0.23 * Math.sqrt(Math.random());
      const du = (rho * Math.sin(a)) / 2.6, dv = rho * Math.cos(a), r = Math.random(), kn = (s + 0.5) / K;
      for (let e = 0; e < 2; e++, p++) {
        off[p * 2] = du; off[p * 2 + 1] = dv; end[p] = e; cl[p] = c; rnd[p] = r; kk[p] = kn;
      }
      tOff[q * 2] = du; tOff[q * 2 + 1] = dv; tEnd[q] = 1; tCl[q] = c; tRnd[q] = r; tK[q] = kn; q++;
    }
    const mk = (o, e, c, r, k, count) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(count * 3), 3));
      g.setAttribute('aOff', new THREE.BufferAttribute(o, 2));
      g.setAttribute('aEnd', new THREE.BufferAttribute(e, 1));
      g.setAttribute('aCl', new THREE.BufferAttribute(c, 1));
      g.setAttribute('aRand', new THREE.BufferAttribute(r, 1));
      g.setAttribute('aK', new THREE.BufferAttribute(k, 1));
      g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 9);
      return g;
    };
    group.add(new THREE.LineSegments(mk(off, end, cl, rnd, kk, nv),
      new THREE.ShaderMaterial({ uniforms, vertexShader: NEEDLE_VS, fragmentShader: LINE_FS, ...additive })));
    group.add(new THREE.Points(mk(tOff, tEnd, tCl, tRnd, tK, NC * K),
      new THREE.ShaderMaterial({ uniforms, vertexShader: NEEDLE_VS, fragmentShader: POINT_FS, ...additive })));
  }

  // --- selection beacon
  const beaconGeo = new THREE.BufferGeometry();
  beaconGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(6), 3));
  const beacon = new THREE.Line(beaconGeo, new THREE.LineBasicMaterial({ color: 0x45d4ff, ...additive, opacity: 0.9 }));
  beacon.visible = false;
  group.add(beacon);

  // --- ambient dust + orbit rings
  const dot = softDot();
  const dust = new THREE.Group();
  {
    const n = 900, pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const r = 5 + Math.random() * 7, th = Math.random() * Math.PI * 2, ph = Math.acos(2 * Math.random() - 1);
      pos[i * 3] = r * Math.sin(ph) * Math.cos(th); pos[i * 3 + 1] = r * Math.cos(ph) * 0.55; pos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    dust.add(new THREE.Points(g, new THREE.PointsMaterial({ size: 0.07, map: dot, color: 0x5d82d0, opacity: 0.55, ...additive })));
  }
  scene.add(dust);
  const rings = [];
  for (const [rad, tilt, col] of [[4.9, 0.05, 0x2a4f95], [5.7, -0.08, 0x1f3a70]]) {
    const pts = [];
    for (let i = 0; i <= 256; i++) { const a = (i / 256) * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(a) * rad, 0, Math.sin(a) * rad)); }
    const ring = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: col, opacity: 0.55, ...additive }));
    ring.rotation.x = tilt;
    const runners = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array(4 * 3), 3)),
      new THREE.PointsMaterial({ size: 0.28, map: dot, color: 0x7fc8ff, ...additive }));
    ring.add(runners);
    ring.userData = { rad, runners };
    scene.add(ring); rings.push(ring);
  }

  // --- globe extras: graticule + atmosphere halo
  const grid = (() => {
    const pts = [], R = RS * 1.004, seg = 72;
    for (let lat = -60; lat <= 60; lat += 30) {
      const la = (lat * Math.PI) / 180;
      for (let i = 0; i < seg; i++) {
        const a0 = (i / seg) * Math.PI * 2, a1 = ((i + 1) / seg) * Math.PI * 2;
        pts.push(R * Math.cos(la) * Math.sin(a0), R * Math.sin(la), R * Math.cos(la) * Math.cos(a0));
        pts.push(R * Math.cos(la) * Math.sin(a1), R * Math.sin(la), R * Math.cos(la) * Math.cos(a1));
      }
    }
    for (let lon = 0; lon < 360; lon += 30) {
      const lo = (lon * Math.PI) / 180;
      for (let i = 0; i < seg / 2; i++) {
        const b0 = -Math.PI / 2 + (i / (seg / 2)) * Math.PI, b1 = -Math.PI / 2 + ((i + 1) / (seg / 2)) * Math.PI;
        pts.push(R * Math.cos(b0) * Math.sin(lo), R * Math.sin(b0), R * Math.cos(b0) * Math.cos(lo));
        pts.push(R * Math.cos(b1) * Math.sin(lo), R * Math.sin(b1), R * Math.cos(b1) * Math.cos(lo));
      }
    }
    const geo = new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array(pts), 3));
    return new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: 0x2c5bb0, opacity: 0, ...additive }));
  })();
  group.add(grid);
  const haloTex = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 256;
    const g = c.getContext('2d'), gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, 'rgba(40,110,255,0)'); gr.addColorStop(0.74, 'rgba(40,110,255,0.05)');
    gr.addColorStop(0.8, 'rgba(90,180,255,0.75)'); gr.addColorStop(0.86, 'rgba(60,140,255,0.25)'); gr.addColorStop(1, 'rgba(40,110,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    return new THREE.CanvasTexture(c);
  })();
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: haloTex, opacity: 0, ...additive }));
  halo.scale.setScalar((RS * 2) / 0.8);
  scene.add(halo);
  // --- galaxy extras: bright bulge
  const bulge = new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, color: 0xffd9a0, opacity: 0, ...additive }));
  bulge.scale.setScalar(3.2);
  scene.add(bulge);

  // --- labels pool
  const LBL = 12;
  const labels = Array.from({ length: LBL }, () => {
    const el = document.createElement('div'); el.className = 'lbl'; el.style.opacity = 0; labelsEl.appendChild(el);
    return { el, key: '' };
  });

  // --- state
  const slotOf = new Map(), slotSym = new Array(NC).fill(null), meta = new Map(), anchors = new Map();
  let selected = null, W = 1, H = 1, t = 0, last = performance.now();
  let yaw = 0.6, pitch = 0.0, yawVel = 0, dragging = false, moved = 0;
  let skin = 'torus', baseD = 12;
  const w = { torus: 1, globe: 0, galaxy: 0 };
  const links = [];

  function resize() {
    W = wrap.clientWidth; H = canvas.clientHeight || wrap.clientHeight;
    renderer.setSize(W, H, false);
    over.width = Math.round(W * dpr); over.height = Math.round(over.clientHeight * dpr);
    const aspect = W / H;
    camera.aspect = aspect;
    baseD = Math.max(12, 16.5 / aspect);
    camera.updateProjectionMatrix();
    placeCamera();
  }
  // each skin has its own viewing angle; blend by the morph weights
  function placeCamera() {
    const el = 0.6 * w.torus + 0.22 * w.globe + 0.78 * w.galaxy;
    const d = baseD * (w.torus + 1.04 * w.globe + 1.0 * w.galaxy);
    camera.position.set(0, Math.sin(el) * d, Math.cos(el) * d);
    camera.lookAt(0, -0.25 * w.torus - 0.1 * w.galaxy, 0);
  }
  new ResizeObserver(resize).observe(wrap);
  resize();

  const v3 = new THREE.Vector3(), n3 = new THREE.Vector3(), view = new THREE.Vector3();
  const tmpA = new THREE.Vector3(), tmpN = new THREE.Vector3();
  /** position (and normal) of slot i lifted by `lift`, blended across skins */
  function slotPoint(i, lift, out, nOut) {
    const s = slots[i];
    const ct = TR + (Tr + lift) * Math.cos(s.v);
    out.set(ct * Math.cos(s.u) * w.torus, (Tr + lift) * Math.sin(s.v) * w.torus, ct * Math.sin(s.u) * w.torus);
    const gx = Math.cos(s.lat) * Math.sin(s.lon), gy = Math.sin(s.lat), gz = Math.cos(s.lat) * Math.cos(s.lon);
    out.x += gx * (RS + lift) * w.globe; out.y += gy * (RS + lift) * w.globe; out.z += gz * (RS + lift) * w.globe;
    out.x += s.gr * Math.cos(s.ga) * w.galaxy; out.y += lift * w.galaxy; out.z += s.gr * Math.sin(s.ga) * w.galaxy;
    if (nOut) {
      nOut.set(Math.cos(s.v) * Math.cos(s.u) * w.torus + gx * w.globe, Math.sin(s.v) * w.torus + gy * w.globe + w.galaxy,
        Math.cos(s.v) * Math.sin(s.u) * w.torus + gz * w.globe).normalize();
    }
    return out;
  }

  function updateBeacon() {
    const i = selected != null ? slotOf.get(selected) : undefined;
    uniforms.uSel.value = i ?? -1;
    if (i == null) { beacon.visible = false; return; }
    const p = beaconGeo.attributes.position;
    slotPoint(i, 0.05, tmpA); p.setXYZ(0, tmpA.x, tmpA.y, tmpA.z);
    slotPoint(i, 2.2, tmpA); p.setXYZ(1, tmpA.x, tmpA.y, tmpA.z);
    p.needsUpdate = true; beacon.visible = true;
  }

  function setSkin(name) {
    if (SKINS.includes(name)) skin = name;
  }

  function setClusters(list) {
    const top = list.slice(0, NC), keep = new Set(top.map((c) => c.sym));
    for (let i = 0; i < NC; i++) {
      if (slotSym[i] && !keep.has(slotSym[i])) {
        slotOf.delete(slotSym[i]); meta.delete(slotSym[i]); slotSym[i] = null; uniforms.uCl.value[i].set(0, 0, 0, 0); uniforms.uPulse.value[i] = 0;
      }
    }
    top.forEach((c, rank) => {
      let i = slotOf.get(c.sym);
      if (i == null) { i = order.find((s) => slotSym[s] == null); slotSym[i] = c.sym; slotOf.set(c.sym, i); }
      meta.set(c.sym, { ...c, rank });
      uniforms.uCl.value[i].set(slots[i].u, slots[i].v, 0.25 + 0.75 * c.volNorm, needle(c.chg));
    });
    updateBeacon();
  }

  function updateTicker(sym, chg, lastPx) {
    const i = slotOf.get(sym), m = meta.get(sym);
    if (i == null || !m) return;
    m.chg = chg; if (lastPx) m.last = lastPx;
    uniforms.uCl.value[i].w = needle(chg);
  }

  function pulse(sym, amt) {
    const i = slotOf.get(sym);
    if (i != null) uniforms.uPulse.value[i] = Math.min(2, uniforms.uPulse.value[i] + amt);
  }

  function setSelected(sym) { selected = sym; updateBeacon(); }

  function link(sym, el) { links.push({ sym, el, t0: performance.now() }); if (links.length > 6) links.shift(); }

  function pick(x, y) {
    let best = null, bd = 26 * 26;
    for (const [sym, a] of anchors) {
      if (a.f < -0.25) continue;
      const d = (a.x - x) ** 2 + (a.y - y) ** 2;
      if (d < bd) { bd = d; best = sym; }
    }
    return best;
  }

  // --- pointer: drag to rotate, click to pick, hover tooltip
  let px = 0, py = 0, lastDx = 0;
  canvas.addEventListener('pointerdown', (e) => {
    dragging = true; moved = 0; px = e.clientX; py = e.clientY; canvas.setPointerCapture(e.pointerId); canvas.classList.add('drag');
  });
  canvas.addEventListener('pointermove', (e) => {
    const r = canvas.getBoundingClientRect();
    if (dragging) {
      const dx = e.clientX - px, dy = e.clientY - py; px = e.clientX; py = e.clientY;
      moved += Math.abs(dx) + Math.abs(dy); lastDx = dx;
      yaw += dx * 0.006; pitch = clamp(pitch + dy * 0.003, -0.35, 0.4);
      return;
    }
    const sym = pick(e.clientX - r.left, e.clientY - r.top);
    canvas.style.cursor = sym ? 'pointer' : '';
    onHover && onHover(sym, e.clientX - wrap.getBoundingClientRect().left, e.clientY - wrap.getBoundingClientRect().top);
  });
  const end = (e) => {
    if (!dragging) return;
    dragging = false; canvas.classList.remove('drag');
    yawVel = clamp(lastDx * 0.02, -0.6, 0.6);
    if (moved < 5) {
      const r = canvas.getBoundingClientRect(), sym = pick(e.clientX - r.left, e.clientY - r.top);
      if (sym && onPick) onPick(sym);
    }
  };
  canvas.addEventListener('pointerup', end);
  canvas.addEventListener('pointercancel', end);
  canvas.addEventListener('pointerleave', () => onHover && onHover(null));

  // --- overlay wires
  const octx = over.getContext('2d');
  const bez = (p0, p1, p2, p3, s) => {
    const m = 1 - s;
    return [m * m * m * p0[0] + 3 * m * m * s * p1[0] + 3 * m * s * s * p2[0] + s * s * s * p3[0],
      m * m * m * p0[1] + 3 * m * m * s * p1[1] + 3 * m * s * s * p2[1] + s * s * s * p3[1]];
  };
  function curve(a, b, color, alpha, lw, dots, speed, seed) {
    const dx = b[0] - a[0];
    const c1 = [a[0] + dx * 0.45, a[1]], c2 = [b[0] - dx * 0.3, b[1] - 24 + (seed % 3) * 16];
    const g = octx.createLinearGradient(a[0], a[1], b[0], b[1]);
    g.addColorStop(0, color.replace('A', alpha)); g.addColorStop(1, color.replace('A', alpha * 0.25));
    octx.strokeStyle = g; octx.lineWidth = lw;
    octx.beginPath(); octx.moveTo(a[0], a[1]); octx.bezierCurveTo(c1[0], c1[1], c2[0], c2[1], b[0], b[1]); octx.stroke();
    for (let k = 0; k < dots; k++) {
      const s = (t * speed + k / dots + seed * 0.137) % 1, p = bez(a, c1, c2, b, s);
      octx.fillStyle = color.replace('A', 0.95 * alpha + 0.05);
      octx.beginPath(); octx.arc(p[0], p[1], 1.8, 0, Math.PI * 2); octx.fill();
    }
  }
  const rgbaT = (hex) => { const n = parseInt(hex.slice(1), 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},A)`; };

  function drawOverlay(wires) {
    octx.setTransform(dpr, 0, 0, dpr, 0, 0);
    octx.clearRect(0, 0, over.width, over.height);
    const wr = wrap.getBoundingClientRect();
    const narrow = wrap.clientWidth < 760;
    octx.shadowBlur = 6;
    if (!narrow) {
      const syms = [...anchors.keys()];
      wires.forEach((w, wi) => {
        const a = anchors.get(w.sym);
        if (!a) return;
        const r = w.el.getBoundingClientRect();
        const from = [r.right - wr.left, r.top + r.height / 2 - wr.top];
        const col = rgbaT(w.color);
        octx.shadowColor = w.color;
        curve(from, [a.x, a.y], col, a.f > -0.2 ? 0.75 : 0.3, 1.2, 3, 0.18 + (w.activity || 0) * 0.5, wi);
        // two faint secondary fibres per card, for the "neural" look
        for (let k = 1; k <= 2; k++) {
          const b = anchors.get(syms[(wi * 7 + k * 11) % syms.length]);
          if (b) curve(from, [b.x, b.y], col, 0.16, 0.7, 1, 0.12, wi + k);
        }
      });
    }
    // transient whale links: cluster → card
    const now = performance.now();
    for (let i = links.length - 1; i >= 0; i--) {
      const L = links[i], age = (now - L.t0) / 2600;
      if (age >= 1 || !L.el.isConnected) { links.splice(i, 1); continue; }
      const a = anchors.get(L.sym);
      if (!a || narrow) continue;
      const r = L.el.getBoundingClientRect();
      const to = [r.left - wr.left, r.top + r.height / 2 - wr.top];
      octx.shadowColor = '#ffb22e';
      curve(to, [a.x, a.y], 'rgba(255,178,46,A)', (1 - age) * 0.9, 1.3, 2, 0.6, i);
    }
    octx.shadowBlur = 0;
  }

  function updateLabels() {
    const vis = [...anchors.entries()]
      .filter(([s, a]) => a.f > -0.05 && a.x > 0 && a.x < W && a.y > 0 && a.y < H)
      .map(([s, a]) => ({ s, a, rank: s === selected ? -1 : (meta.get(s)?.rank ?? 99) }))
      .sort((x, y) => x.rank - y.rank)
      .slice(0, LBL);
    labels.forEach((L, i) => {
      const it = vis[i];
      if (!it) { L.el.style.opacity = 0; return; }
      const m = meta.get(it.s);
      const key = it.s + (m ? m.chg.toFixed(2) : '') + (it.s === selected);
      if (key !== L.key) {
        L.key = key;
        const c = m ? m.chg : 0;
        L.el.innerHTML = `${baseOf(it.s)}<em class="${c > 0 ? 'up' : c < 0 ? 'dn' : ''}">${pct(c)}</em>`;
        L.el.classList.toggle('sel', it.s === selected);
      }
      L.el.style.opacity = (0.45 + 0.55 * clamp(it.a.f * 2, 0, 1)).toFixed(2);
      L.el.style.transform = `translate(${(it.a.x + 7).toFixed(1)}px, ${(it.a.y - 18).toFixed(1)}px)`;
    });
  }

  function frame(now, wires = []) {
    const raw = Math.max(0, (now - last) / 1000), dt = Math.min(0.05, raw); last = now; t += dt;
    // morph towards the chosen skin (wall-clock based, so slow frame rates still finish in ~2 s)
    const k = 1 - Math.exp(-Math.min(1, raw) * 2.4);
    let sum = 0;
    for (const sk of SKINS) { w[sk] += ((sk === skin ? 1 : 0) - w[sk]) * k; if (w[sk] < 1e-4) w[sk] = 0; sum += w[sk]; }
    for (const sk of SKINS) w[sk] /= sum;
    uniforms.uWT.value = w.torus; uniforms.uWG.value = w.globe; uniforms.uWX.value = w.galaxy;
    grid.material.opacity = 0.22 * w.globe; halo.material.opacity = 0.85 * w.globe; bulge.material.opacity = 0.9 * w.galaxy;
    placeCamera();
    updateBeacon();
    if (!dragging) { yaw += (0.045 + yawVel) * dt; yawVel *= 0.96; }
    group.rotation.set(pitch + Math.sin(t * 0.21) * 0.035, yaw, Math.sin(t * 0.17) * 0.02);
    dust.rotation.y = -t * 0.01;
    const pu = uniforms.uPulse.value, decay = Math.exp(-dt * 2.2);
    for (let i = 0; i < NC; i++) pu[i] *= decay;
    uniforms.uTime.value = t;
    rings.forEach((ring, ri) => {
      ring.rotation.y = t * (ri ? -0.03 : 0.05);
      const p = ring.userData.runners.geometry.attributes.position, rad = ring.userData.rad;
      for (let k = 0; k < 4; k++) { const a = t * (0.25 + k * 0.05) * (ri ? -1 : 1) + k * 1.7; p.setXYZ(k, Math.cos(a) * rad, 0, Math.sin(a) * rad); }
      p.needsUpdate = true;
    });
    renderer.render(scene, camera);

    // project cluster anchors to screen
    anchors.clear();
    for (const [sym, i] of slotOf) {
      slotPoint(i, 0.18, v3, n3).applyMatrix4(group.matrixWorld);
      n3.applyQuaternion(group.quaternion);
      const f = n3.dot(view.copy(camera.position).sub(v3).normalize());
      v3.project(camera);
      anchors.set(sym, { x: (v3.x + 1) / 2 * W, y: (1 - v3.y) / 2 * H, f });
    }
    drawOverlay(wires);
    updateLabels();
  }

  return { setClusters, updateTicker, pulse, setSelected, setSkin, frame, pick, link, count: () => slotOf.size };
}
