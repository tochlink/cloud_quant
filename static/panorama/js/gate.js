// Gate.io API v4 public endpoints (no auth). REST responses carry
// `access-control-allow-origin: *`, so the browser can call them directly.
export const REST_BASE = 'https://api.gateio.ws/api/v4';
export const SPOT_WS = 'wss://api.gateio.ws/ws/v4/';
export const PERP_WS = 'wss://fx-ws.gateio.ws/v4/ws/usdt';

export async function rest(path, params = {}, timeout = 15000) {
  const q = new URLSearchParams(params).toString();
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeout);
  try {
    const res = await fetch(REST_BASE + path + (q ? '?' + q : ''), { signal: ctl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
    return await res.json();
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Reconnecting Gate.io WebSocket client.
 * Subscriptions are reference-counted per (channel, payload) so overlapping
 * consumers (e.g. a coin that is both in the focus list and selected) can
 * unsubscribe independently without dropping each other's stream.
 */
export class GateWS {
  constructor(url, prefix, { onMessage, onStatus } = {}) {
    this.url = url;
    this.prefix = prefix; // 'spot' | 'futures'
    this.onMessage = onMessage || (() => {});
    this.onStatus = onStatus || (() => {});
    this.subs = new Map(); // key -> { channel, payload, refs }
    this.retry = 0;
    this.frames = 0;
    this.bytes = 0;
    this.ws = null;
    this.pingTimer = null;
  }

  connect() {
    this.onStatus('connecting');
    let ws;
    try {
      ws = this.ws = new WebSocket(this.url);
    } catch (e) {
      this._schedule();
      return;
    }
    ws.onopen = () => {
      this.retry = 0;
      this.onStatus('open');
      for (const s of this.subs.values()) this._send(s.channel, 'subscribe', s.payload);
      clearInterval(this.pingTimer);
      this.pingTimer = setInterval(() => this._send(this.prefix + '.ping'), 10000);
    };
    ws.onmessage = (e) => {
      this.frames++;
      this.bytes += e.data.length;
      let m;
      try { m = JSON.parse(e.data); } catch (err) { return; }
      this.onMessage(m, e.data.length);
    };
    ws.onclose = () => {
      clearInterval(this.pingTimer);
      if (this.ws !== ws) return;
      this.onStatus('closed');
      this._schedule();
    };
    ws.onerror = () => { try { ws.close(); } catch (e) { /* ignore */ } };
  }

  _schedule() {
    const delay = Math.min(30000, 1000 * 2 ** this.retry++) + Math.random() * 500;
    setTimeout(() => this.connect(), delay);
  }

  _send(channel, event, payload) {
    if (!this.ws || this.ws.readyState !== 1) return;
    const msg = { time: Math.floor(Date.now() / 1000), channel };
    if (event) msg.event = event;
    if (payload) msg.payload = payload;
    this.ws.send(JSON.stringify(msg));
  }

  subscribe(channel, payload) {
    const key = channel + '|' + JSON.stringify(payload);
    const cur = this.subs.get(key);
    if (cur) { cur.refs++; return; }
    this.subs.set(key, { channel, payload, refs: 1 });
    this._send(channel, 'subscribe', payload);
  }

  unsubscribe(channel, payload) {
    const key = channel + '|' + JSON.stringify(payload);
    const cur = this.subs.get(key);
    if (!cur) return;
    if (--cur.refs > 0) return;
    this.subs.delete(key);
    this._send(channel, 'unsubscribe', payload);
  }
}
