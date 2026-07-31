/**
 * Intent transport.
 *
 * docs/ARCHITECTURE.md §4: the client never mutates gameplay state. It says
 * what the player wants; the server validates, mutates, and broadcasts the
 * result.
 *
 * Today `LocalTransport` runs the authoritative sim in-process with a direct
 * call. Swapping in `WebSocketTransport` later changes nothing at any call
 * site — which is the entire point of putting this indirection in now rather
 * than after the world is built.
 */

export class LocalTransport {
  constructor(sim) {
    this.sim = sim;
    this.handlers = new Map();
    this.latencyMs = 0;   // set >0 to rehearse real network conditions
  }

  /** Fire an intent. Returns a promise resolving to the authoritative result. */
  async intent(type, payload = {}) {
    const send = () => this.sim.handleIntent(type, payload, 'local-player');
    if (this.latencyMs > 0) {
      await new Promise(r => setTimeout(r, this.latencyMs));
    }
    const result = send();
    this._dispatch(result);
    return result;
  }

  on(event, fn) {
    if (!this.handlers.has(event)) this.handlers.set(event, []);
    this.handlers.get(event).push(fn);
  }

  _dispatch(result) {
    if (!result || !result.events) return;
    for (const ev of result.events) {
      for (const fn of this.handlers.get(ev.type) || []) fn(ev);
    }
  }
}

/**
 * Not wired up yet — present to make the seam explicit and to document that
 * the swap is a transport change, not an architecture change.
 */
export class WebSocketTransport {
  constructor(url) {
    this.url = url;
    this.handlers = new Map();
    this.pending = new Map();
    this.seq = 0;
  }

  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.ack !== undefined && this.pending.has(msg.ack)) {
        this.pending.get(msg.ack)(msg.result);
        this.pending.delete(msg.ack);
      }
      for (const fn of this.handlers.get(msg.type) || []) fn(msg);
    };
    return new Promise(r => { this.ws.onopen = r; });
  }

  intent(type, payload = {}) {
    const id = ++this.seq;
    this.ws.send(JSON.stringify({ id, type, payload }));
    return new Promise(res => this.pending.set(id, res));
  }

  on(event, fn) {
    if (!this.handlers.has(event)) this.handlers.set(event, []);
    this.handlers.get(event).push(fn);
  }
}
