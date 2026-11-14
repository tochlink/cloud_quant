// Header "market pulse": the top coins by volume stand as light pillars on an
// elliptical ring that turns like a carousel. Pillars rise for gainers and sink
// for losers (heights relative to how much the market moved), a sweep beam runs
// around the ring and whale trades make a pillar flare.
import * as THREE from 'three';

const N = 64;
const GREEN = new THREE.Color(0x22e3a0), RED = new THREE.Color(0xff4f6e), CYAN = new THREE.Color(0x45d4ff);

function softDot() {
  const c = document.createElement('canvas'); c.width = c.height = 32;
  const g = c.getContext('2d'), gr = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(255,255,255,.45)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 32, 32);
  return new THREE.CanvasTexture(c);
}

// pillar: bright at the tip, fading towards the ring
const PILLAR_VS = /* glsl */`
varying float vY;
varying vec3 vCol;
void main() {
  vY = position.y;
  vCol = instanceColor;
  gl_Position = projectionMatrix * modelViewMatrix * instanceMatrix * vec4(position, 1.0);
}`;
const PILLAR_FS = /* glsl */`
varying float vY;
varying vec3 vCol;
void main() {
  float k = pow(clamp(vY, 0.0, 1.0), 1.6);
  gl_FragColor = vec4(vCol * (0.35 + 0.9 * k), 0.18 + 0.82 * k);
}`;

export function createPulse(canvas, { onPick, onFocus, onHover } = {}) {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  } catch (e) {
    return null;
  }
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  renderer.setPixelRatio(dpr);
  renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(13, 1, 0.1, 200);
  camera.position.set(0, 4.2, 30);
  camera.lookAt(0, 0.15, 0);
  const add = { transparent: true, depthWrite: false, blending: THREE.AdditiveBlending };
  const dot = softDot();

  // floor glow disc
  const disc = new THREE.Mesh(new THREE.CircleGeometry(1, 96), new THREE.MeshBasicMaterial({ color: 0x0f2d66, opacity: 0.55, ...add }));
  disc.rotation.x = -Math.PI / 2;
  scene.add(disc);

  // pillars
  const geo = new THREE.BoxGeometry(0.14, 1, 0.14);
  geo.translate(0, 0.5, 0);
  const bars = new THREE.InstancedMesh(geo, new THREE.ShaderMaterial({ vertexShader: PILLAR_VS, fragmentShader: PILLAR_FS, side: THREE.DoubleSide, ...add }), N);
  for (let i = 0; i < N; i++) bars.setColorAt(i, CYAN);
  scene.add(bars);

  // glowing tips
  const tipPos = new Float32Array(N * 3), tipCol = new Float32Array(N * 3);
  const tipGeo = new THREE.BufferGeometry();
  tipGeo.setAttribute('position', new THREE.BufferAttribute(tipPos, 3));
  tipGeo.setAttribute('color', new THREE.BufferAttribute(tipCol, 3));
  const tipMat = new THREE.PointsMaterial({ size: 0.7, map: dot, vertexColors: true, ...add });
  scene.add(new THREE.Points(tipGeo, tipMat));

  // floor rings + rising dust
  const ringGeo = (k, n) => {
    const p = new Float32Array(n * 3);
    return { geo: new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(p, 3)), p, k, n };
  };
  const rings = [ringGeo(1, 240), ringGeo(1.1, 240), ringGeo(0.55, 160)];
  rings.forEach((r, i) => scene.add(new THREE.LineLoop(r.geo,
    new THREE.LineBasicMaterial({ color: [0x3a78e0, 0x1d3a6e, 0x22508f][i], opacity: [0.9, 0.5, 0.45][i], ...add }))));
  const dust = ringGeo(1, 300);
  const dustSeed = Float32Array.from({ length: 300 }, () => Math.random());
  const dustMat = new THREE.PointsMaterial({ size: 0.16, map: dot, color: 0x4f7fd8, opacity: 0.8, ...add });
  scene.add(new THREE.Points(dust.geo, dustMat));

  // core: wireframe icosahedron in the middle of the ring
  const core = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.IcosahedronGeometry(1, 1)),
    new THREE.LineBasicMaterial({ color: 0x45d4ff, opacity: 0.8, ...add }));
  core.position.y = 0.9;
  scene.add(core);
  const coreGlow = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array([0, 0.9, 0]), 3)),
    new THREE.PointsMaterial({ size: 6, map: dot, color: 0x2a7fff, opacity: 0.6, ...add }));
  scene.add(coreGlow);

  // state
  const items = [];           // {sym, label, chg, h, target, flash, a}
  let rx = 8, rz = 3, bw = 1, t = 0, last = performance.now(), rot = 0, breadth = 0.5, focusIdx = -1, scale = 8;
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), pos = new THREE.Vector3(), scl = new THREE.Vector3(), col = new THREE.Color();

  const heightOf = (chg) => {
    const r = Math.min(Math.abs(chg || 0) / scale, 1.3) / 1.3;
    return Math.sign(chg || 0) * (0.12 + 2.3 * Math.sqrt(r));
  };

  function resize() {
    const W = canvas.clientWidth, H = canvas.clientHeight;
    if (!W || !H) return;
    renderer.setSize(W, H, false);
    camera.aspect = W / H;
    camera.updateProjectionMatrix();
    const halfH = Math.tan((camera.fov * Math.PI) / 360) * camera.position.z;
    rx = Math.max(4, halfH * camera.aspect * 0.86);
    rz = Math.min(5, rx * 0.3);
    bw = Math.max(1, Math.min(3, rx / 8));
    disc.scale.set(rx * 1.08, rz * 1.08, 1);
    core.scale.setScalar(Math.min(1.6, rz * 0.3));
    tipMat.size = 0.5 * bw; dustMat.size = 0.12 * bw;
    rings.forEach((r) => {
      for (let i = 0; i < r.n; i++) { const a = (i / r.n) * Math.PI * 2; r.p[i * 3] = Math.cos(a) * rx * r.k; r.p[i * 3 + 1] = 0; r.p[i * 3 + 2] = Math.sin(a) * rz * r.k; }
      r.geo.attributes.position.needsUpdate = true;
    });
  }
  new ResizeObserver(resize).observe(canvas);
  resize();

  function setData(list, br) {
    breadth = br;
    // scale heights to the 90th percentile move, so quiet and wild markets both read well
    const abs = list.slice(0, N).map((c) => Math.abs(c.chg || 0)).sort((a, b) => a - b);
    scale = Math.max(3, Math.min(30, abs[Math.floor(abs.length * 0.9)] || 8));
    const old = new Map(items.map((x) => [x.sym, x]));
    items.length = 0;
    const n = Math.min(N, list.length);
    list.slice(0, N).forEach((c, i) => {
      const prev = old.get(c.sym);
      items.push({ sym: c.sym, label: c.label, chg: c.chg, target: heightOf(c.chg), h: prev ? prev.h : 0, flash: prev ? prev.flash : 0, a: (i / n) * Math.PI * 2 });
    });
  }
  function update(sym, chg) {
    const it = items.find((x) => x.sym === sym);
    if (it) { it.chg = chg; it.target = heightOf(chg); }
  }
  function bump(sym, amt) {
    const it = items.find((x) => x.sym === sym);
    if (it) it.flash = Math.min(1.5, it.flash + amt);
  }

  // hover: hit-test the projected pillars (front ones win); click picks the hovered pillar or the front one
  const scr = Array.from({ length: N }, () => ({ x: 0, yb: 0, yt: 0, z: 0, ok: false }));
  const pv = new THREE.Vector3();
  let mouse = null, hoverIdx = -1;
  function hitTest() {
    hoverIdx = -1;
    if (!mouse) return;
    let best = Infinity;
    for (let i = 0; i < N; i++) {
      const s = scr[i];
      if (!s.ok) continue;
      const dx = Math.abs(s.x - mouse.x), y0 = Math.min(s.yb, s.yt) - 6, y1 = Math.max(s.yb, s.yt) + 6;
      if (dx > 9 || mouse.y < y0 || mouse.y > y1) continue;
      const score = dx - s.z * 4; // prefer pillars in front
      if (score < best) { best = score; hoverIdx = i; }
    }
  }
  canvas.addEventListener('pointermove', (e) => {
    const r = canvas.getBoundingClientRect();
    mouse = { x: e.clientX - r.left, y: e.clientY - r.top, cx: e.clientX, cy: e.clientY };
  });
  canvas.addEventListener('pointerleave', () => { mouse = null; hoverIdx = -1; onHover && onHover(null); });
  canvas.addEventListener('click', () => {
    const i = hoverIdx >= 0 ? hoverIdx : focusIdx;
    if (i >= 0 && items[i] && onPick) onPick(items[i].sym);
  });

  function frame(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now; t += dt;
    rot += dt * 0.1;
    const sweep = (t * 0.9) % (Math.PI * 2);
    let bestZ = -Infinity, best = -1;
    for (let i = 0; i < N; i++) {
      const it = items[i];
      if (!it) { m4.makeScale(0, 0, 0); bars.setMatrixAt(i, m4); tipPos[i * 3 + 1] = -99; continue; }
      it.h += (it.target - it.h) * Math.min(1, dt * 3);
      it.flash *= Math.exp(-dt * 1.8);
      const a = it.a + rot, x = Math.cos(a) * rx, z = Math.sin(a) * rz;
      const depth = (z / rz + 1) / 2; // 0 back .. 1 front
      if (z > bestZ) { bestZ = z; best = i; }
      const hh = it.h * (1 + it.flash * 0.5) * (0.94 + 0.06 * Math.sin(t * 3 + i));
      pos.set(x, 0, z);
      scl.set(bw * (1 + it.flash * 0.8), Math.abs(hh) < 0.03 ? 0.03 : hh, bw * (1 + it.flash * 0.8));
      m4.compose(pos, q, scl); bars.setMatrixAt(i, m4);
      const d = Math.abs(((a - sweep) % (Math.PI * 2) + Math.PI * 3) % (Math.PI * 2) - Math.PI);
      const sw = Math.max(0, 1 - d / 0.45);
      const k = Math.min(1, 0.35 + 0.5 * depth + sw * 0.5 + it.flash * 0.6);
      col.copy(it.chg >= 0 ? GREEN : RED).multiplyScalar(k);
      if (i === focusIdx || i === hoverIdx) col.lerp(CYAN, 0.6);
      bars.setColorAt(i, col);
      tipPos[i * 3] = x; tipPos[i * 3 + 1] = hh; tipPos[i * 3 + 2] = z;
      const cw = canvas.clientWidth, ch = canvas.clientHeight;
      pv.set(x, 0, z).project(camera); scr[i].x = (pv.x + 1) / 2 * cw; scr[i].yb = (1 - pv.y) / 2 * ch;
      pv.set(x, hh, z).project(camera); scr[i].yt = (1 - pv.y) / 2 * ch; scr[i].z = depth; scr[i].ok = true;
      tipCol[i * 3] = col.r; tipCol[i * 3 + 1] = col.g; tipCol[i * 3 + 2] = col.b;
    }
    bars.instanceMatrix.needsUpdate = true;
    if (bars.instanceColor) bars.instanceColor.needsUpdate = true;
    tipGeo.attributes.position.needsUpdate = true;
    tipGeo.attributes.color.needsUpdate = true;
    for (let i = 0; i < dust.n; i++) {
      const s = dustSeed[i], a = s * 40 + rot * (0.6 + s), r = 0.3 + s * 0.85;
      dust.p[i * 3] = Math.cos(a) * rx * r; dust.p[i * 3 + 1] = ((t * 0.25 * (0.3 + s) + s * 7) % 3.4) - 1.2; dust.p[i * 3 + 2] = Math.sin(a) * rz * r;
    }
    dust.geo.attributes.position.needsUpdate = true;
    core.rotation.set(t * 0.4, t * 0.6, 0);
    core.material.color.copy(breadth >= 0.5 ? GREEN : RED).lerp(CYAN, 0.45);
    renderer.render(scene, camera);
    if (best !== focusIdx) { focusIdx = best; onFocus && onFocus(items[best]); }
    hitTest();
    canvas.style.cursor = hoverIdx >= 0 ? 'pointer' : '';
    if (mouse && onHover) onHover(hoverIdx >= 0 ? items[hoverIdx] : null, mouse.cx, mouse.cy);
  }

  return { setData, update, bump, frame };
}
