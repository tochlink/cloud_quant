// One floating tooltip shared by every chart on the page (position: fixed).
let el = null;

export function showTip(html, cx, cy) {
  if (!el) {
    el = document.createElement('div');
    el.className = 'g-tip';
    document.body.appendChild(el);
  }
  if (el._html !== html) { el._html = html; el.innerHTML = html; }
  el.style.display = 'block';
  const w = el.offsetWidth, h = el.offsetHeight;
  let x = cx + 16, y = cy + 16;
  if (x + w > window.innerWidth - 6) x = cx - w - 16;
  if (y + h > window.innerHeight - 6) y = cy - h - 16;
  el.style.transform = `translate(${Math.max(4, x)}px, ${Math.max(4, y)}px)`;
}

export function hideTip() { if (el) el.style.display = 'none'; }

/** tooltip row: label · value */
export const tr = (label, value, cls = '') => `<div class="tt-r"><span>${label}</span><b class="${cls}">${value}</b></div>`;

/**
 * Track the pointer over a canvas: sets cv._hover = {x, y, cx, cy} (canvas + client
 * coordinates) and calls redraw() so the chart can paint its crosshair at once.
 */
export function hoverable(cv, redraw) {
  cv.addEventListener('pointermove', (e) => {
    const r = cv.getBoundingClientRect();
    cv._hover = { x: e.clientX - r.left, y: e.clientY - r.top, cx: e.clientX, cy: e.clientY };
    redraw();
  });
  cv.addEventListener('pointerleave', () => { cv._hover = null; hideTip(); redraw(); });
}
