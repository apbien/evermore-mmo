/**
 * Authoritative simulation.
 *
 * Owns all gameplay state. Validates every intent before mutating anything —
 * range checks, stock checks, funds checks — because a client that can assert
 * a purchase is a client that can duplicate gold.
 *
 * Runs in-process today (see client/src/net.js LocalTransport). It imports
 * nothing from the renderer and must never do so: that import boundary is what
 * keeps it liftable into a real server process.
 */

export class Sim {
  constructor(town, entities) {
    this.town = town;
    this.entities = new Map();
    for (const e of entities) this.entities.set(e.id, e);

    this.players = new Map();
    this.players.set('local-player', {
      id: 'local-player',
      pos: [...(town.playerSpawn?.pos || [0, 0, -44])],
      purse: 250,             // copper
      inventory: new Map(),
      questLog: [],
    });

    this.cellSize = town.grid?.cellSize ?? 16;
  }

  // -- spatial ------------------------------------------------------------

  /**
   * Cell key for a world position. Today this drives culling; unchanged, it
   * becomes network interest management (subscribe to own cell + 8 neighbours).
   */
  cellOf(pos) {
    const cx = Math.floor(pos[0] / this.cellSize);
    const cz = Math.floor(pos[2] / this.cellSize);
    return `${cx},${cz}`;
  }

  /** Entities a viewer should receive. The interest set, already correct. */
  interestSet(pos, radiusCells = 1) {
    const cs = this.cellSize;
    const cx = Math.floor(pos[0] / cs), cz = Math.floor(pos[2] / cs);
    const out = [];
    for (const e of this.entities.values()) {
      const p = e.transform?.pos;
      if (!p) continue;
      const ex = Math.floor(p[0] / cs), ez = Math.floor(p[2] / cs);
      if (Math.abs(ex - cx) <= radiusCells && Math.abs(ez - cz) <= radiusCells) out.push(e);
    }
    return out;
  }

  // -- intents ------------------------------------------------------------

  handleIntent(type, payload, playerId) {
    const player = this.players.get(playerId);
    if (!player) return this._fail('no_such_player');
    const fn = this[`_on${type}`];
    if (typeof fn !== 'function') return this._fail('unknown_intent', { type });
    return fn.call(this, payload, player);
  }

  _fail(reason, extra = {}) {
    return { ok: false, reason, ...extra, events: [] };
  }

  _inRange(player, entity, extra = 0) {
    const p = entity.transform?.pos;
    if (!p) return false;
    const range = (entity.components?.interactable?.range ?? 2.0) + extra;
    const dx = p[0] - player.pos[0], dz = p[2] - player.pos[2];
    return (dx * dx + dz * dz) <= range * range;
  }

  /** Presentation-only. Movement is client-predicted; this records the truth. */
  _onMove({ pos }, player) {
    if (!Array.isArray(pos) || pos.length !== 3) return this._fail('bad_pos');
    player.pos = [...pos];
    return { ok: true, events: [] };
  }

  _onInspect({ target }, player) {
    const e = this.entities.get(target);
    if (!e) return this._fail('no_such_entity');
    if (!this._inRange(player, e)) return this._fail('out_of_range');
    return { ok: true, entity: e, events: [{ type: 'Inspected', id: target }] };
  }

  _onRequestPurchase({ vendor, item, qty = 1 }, player) {
    const v = this.entities.get(vendor);
    if (!v) return this._fail('no_such_vendor');
    if (!this._inRange(player, v)) return this._fail('out_of_range');

    const stock = v.components?.vendor?.stock;
    if (!stock) return this._fail('not_a_vendor');
    const line = stock.find(s => s.item === item);
    if (!line) return this._fail('not_stocked');
    if (line.qty !== -1 && line.qty < qty) return this._fail('insufficient_stock');

    const cost = line.price * qty;
    if (player.purse < cost) return this._fail('insufficient_funds', { cost, purse: player.purse });

    // Only now does anything change.
    player.purse -= cost;
    if (line.qty !== -1) line.qty -= qty;
    player.inventory.set(item, (player.inventory.get(item) || 0) + qty);

    return {
      ok: true, cost, purse: player.purse,
      events: [{ type: 'Purchased', vendor, item, qty, cost, purse: player.purse }],
    };
  }

  _onRequestQuestBoard({ target }, player) {
    const e = this.entities.get(target);
    if (!e) return this._fail('no_such_entity');
    if (!this._inRange(player, e)) return this._fail('out_of_range');
    const notices = e.components?.quest_board?.notices || [];
    return { ok: true, notices, events: [{ type: 'QuestBoardOpened', id: target }] };
  }

  _onRequestRest({ target }, player) {
    const e = this.entities.get(target);
    if (!e) return this._fail('no_such_entity');
    if (!this._inRange(player, e)) return this._fail('out_of_range');
    if (!e.components?.rest_point) return this._fail('not_a_rest_point');
    return { ok: true, events: [{ type: 'Rested', id: target }] };
  }

  _onOpen({ target }, player) {
    const e = this.entities.get(target);
    if (!e) return this._fail('no_such_entity');
    if (!this._inRange(player, e, 0.5)) return this._fail('out_of_range');
    e.state = e.state || {};
    e.state.open = !e.state.open;
    return { ok: true, open: e.state.open,
             events: [{ type: 'Opened', id: target, open: e.state.open }] };
  }
}
