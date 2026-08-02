# Evermore

An MMORPG built to AAA visual standards by an agent pipeline — first town:
**Hearthmere**, in the world of **Arkadion**.

- [`PROMPT.md`](PROMPT.md) — the owner's standing order: mission, priorities,
  rules of evidence.
- [`CLAUDE.md`](CLAUDE.md) — hard technical constraints for agents.
- [`docs/`](docs/) — the governed documents: art bible, build directive, town
  plan, world bible, review protocol, decisions.

---

## Running it

**There is a `Makefile`, but `make` is not installed on Windows** — that is why
`make assets` fails. Every command below is the same thing without it, and they
all work on this machine. Run them from the repo root.

### Walk around the town

```bash
npm run serve
```

Then open **http://localhost:8080**. WASD to move, hold Shift to run, drag the
mouse to look, `E` to interact. You spawn on the altar in the Church of
Summoning; walk out of the west door. Stop the server with Ctrl-C.

This needs assets to exist on disk. They are no longer stored in git (D-067), so
on a fresh clone build them first — see below.

### Make new pictures

```bash
npm run town
```

Whole-town renders — the plan view, aerials, the arrival frame, the square, the
silhouette, and the three approach cameras — written to `review/shots/town/`.
This is the render set to look at when judging the town as a whole.

```bash
npm run shots -- --asset assets/meshes/church.gltf --site 43,-0.5 --out review/shots/church --label church --views gameplay,approach,detail,silhouette
```

One venue on its own, standing on the ground it actually stands on. Swap
`church` for any file in `assets/meshes/`.

A walk down a street, which is how streets get judged:

```bash
npm run town -- --views walk --frames 8 --route "0,-60;0,-20;0,20" --out review/shots/walk
```

### Rebuild the assets

```bash
npm run build
```

Rebuilds every venue mesh from its generator — about 10–15 minutes. Add
`-- --venue church` to do just one, which takes seconds.

```bash
npm run textures
```

Rebuilds the PBR texture sets. Slow, and skips anything already on disk; add
`-- --force-textures` when a material recipe has changed, or the pictures will
be judged against stale sheets.

### Check nothing is broken

```bash
npm run verify
```

Runs all four machine provers in order — geometry, palette, scale and
anachronism checks; that the town floods on foot from the spawn point; that the
real client boots clean; and that the plan and the shipped town still agree.

Individually: `npm run validate`, `npm run walkable`, `npm run playable`,
`npm run plan`, and `npm run determinism` (rebuilds twice and fails if the two
builds differ).

To refresh the machine verdict that every session reads at startup:

```bash
npm run validate > review/validate.txt
```

### First time on a new machine

```bash
npm install
npx playwright install chromium
npm run textures
npm run build
```

`npx playwright install chromium` is the one people miss — without it every
render command fails, because the screenshots are taken in a real browser.
