"""Siting — put a venue mesh on its authored slot, the right way round.

**`Site` is the only siting class in this repo.** There used to be two —
`core.siting.Site` and `core.venue.Plot` — written a day apart by two agents
who each found the same bug and each shipped their own cure into shared core.
That is exactly the divergence CLAUDE.md forbids, so D-025 collapsed them into
this one. If you need something siting-shaped, extend this class.

## The bug both of them were written to fix

There are two rotation conventions in the repo and they are mirrors of each
other. Both are load-bearing and neither can move:

  **The plan convention.** `docs/areas/hearthmere/TOWN_PLAN.md` §6 and `core.building.Footprint`
  define a slot's frame as `world = centre + U*a + V*b` with
  `U = (cos t, sin t)`, so the frontage runs along `U`, the front normal is
  `-V = (sin t, -cos t)`, and `rotationDeg` is a compass heading. The
  `polygon` in every `buildingSlots[]` row is drawn in that frame, and
  `venues/townhouse.py` builds 63 masses straight into world space from it.

  **The placement convention.** A venue mesh is not in world space. The client
  (`client/src/main.js:174`), the client's collision loader
  (`client/src/collision.js:201`), the town harness
  (`tools/render/town.html:413`) and `tools/check_walkable.mjs` all place it
  with a three.js `rotation.y` of `rotationDeg`, i.e.
  `world = origin + rot_y(t) * local`, where `rot_y(t)` sends local `+X` to
  `(cos t, -sin t)`. `mesh.Mesh.rotate_y` and `collision.rot_xz` are the same
  matrix, so build and runtime agree.

Compose the two and a mesh authored front-to-local-`-Z` comes out facing
`(-sin t, -cos t)` — the mirror of the `(sin t, -cos t)` the plan asked for.
At `t = 0` or `180` nobody notices, which is why fourteen venues shipped before
it surfaced. At the moot hall's `t = 60` the building is 120 degrees out and
its front elevation looks away from the market place.

## The fix, once, here

One corrective yaw makes the two conventions compose to the identity:

    rot_y(t) * rot_y(-2t) * d  ==  rot_y(-t) * d

and `rot_y(-t)` is precisely the plan's `world = centre + U*a + V*b`. So a
venue authored with its front at design `-Z` and passed through `Site` lands
corner-exact on its own `buildingSlots[].polygon`, at any `t`. Geometry,
colliders, entities and instance transforms all go through the same rotation,
so they cannot drift apart. `tools/plan/check_siting.py` proves it numerically
for every slot in the town.

## Using it

Everything a venue author writes is in the **design frame**:

    +X   along the frontage, left to right as you stand in the street
    -Z   out of the front door, toward the street the slot fronts
     0   the venue placement origin — `venues[].origin` in the town file

which is the frame `docs/areas/hearthmere/plan/schedule.md` is written in: `w` runs along the
frontage and `d` back into the plot, so the footprint is `x in [-w/2, w/2]`,
`z in [-d/2, d/2]` and the street-side wall face is `z = site.front`. No venue
has to know about theta at all.

    SITE = Site("moot_hall")            # module scope: constants can read it

    def build(ctx, asset_id=ASSET):
        SITE.bind(ctx)
        SITE.emit(geom)                 # geom authored front toward -Z
        SITE.collider("box", center=(0, 1.2, SITE.front), half=(2, 1.2, .3))
        SITE.entity(f"{ASSET}.door.01", "door.moot", (0, 0.4, SITE.front - .4),
                    verbs=["enter"])

Venues that own several slots (`stables`, `quay`, `watermill`) pass `slot=`.
`Site(slot=33, ctx=ctx)` works too, for a venue built entirely inside `build`.

## Site also owns the ground

`y = 0` in a venue mesh is `origin[1]`, which the town file writes from
`terrain.height` at the slot centre — so it is the ground at ONE point, and a
footprint has corners. `site.base` is the level the building's plinth should
top out at, `site.lo`/`site.hi` are the extremes of the real terrain round the
plot, and `site.ground(x, z)` reads the terrain at any design-frame point in
local Y. Nothing here ever assumes `y = 0` is the ground (Directive §6.1).
"""

from __future__ import annotations

import math

import numpy as np

from . import collision as COL
from . import mesh as M
from . import terrain as T
# One reader, one cache, one town document. `core.siting` used to open and
# cache `hearthmere.json` a second time, which is a fork of exactly the kind
# this module was written to end.
from .venue import TOWN_JSON as TOWN, town, slot        # noqa: F401


class Site:
    """A venue's slot, its ground, and the frame correction that lands it there.

    `name` is the venue id in `content/town/hearthmere.json`. Where one venue
    owns several slots (`stables`, `quay`, `watermill`) pass `slot=` the slot
    number; otherwise the first row wins. `slot=` alone is enough — the venue
    name is then taken from the row.

    `ctx` may be given here or later with `bind()`. It has to be optional
    because the useful pattern is a module-scope `SITE = Site(NAME)` whose `w`,
    `d`, `eaves` and `front` become the module's dimensional constants, and the
    context does not exist until `build()` is called.

    `authored` declares that this venue's source coordinates are already the
    design frame turned by that many radians — for a venue whose geometry was
    authored before this class existed and is too large to re-coordinate. The
    residual `fix - authored` is what gets applied, so it is 0 today and becomes
    non-zero the moment the plan changes the slot's rotation, which turns a
    silent mirror into a loud one. `venues/church.py` is the only user.
    """

    def __init__(self, name=None, slot=None, *, ctx=None, asset_id=None,
                 authored=0.0, freeboard=0.06):
        doc = town()
        rows = doc["buildingSlots"]
        if name is not None:
            rows = [s for s in rows if s.get("venue") == name]
        if slot is not None:
            rows = [s for s in rows if s["n"] == slot]
        if not rows:
            raise KeyError(f"no buildingSlots row with venue={name!r} "
                           f"{'slot=' + str(slot) if slot is not None else ''}")
        self.slot = rows[0]
        name = name or self.slot.get("venue")
        vs = [v for v in doc["venues"] if v.get("slot") == self.slot["n"]]
        if not vs:
            raise KeyError(f"slot {self.slot['n']} has no venues[] entry; the "
                           f"mesh would never be placed")
        self.venue = vs[0]

        self.name = name
        self.id = self.slot["id"]
        self.asset_id = asset_id or self.id
        self.cells = list(self.slot.get("cells") or [])
        self.note = self.slot.get("note") or ""
        self.centre = (float(self.slot["centre"][0]), float(self.slot["centre"][1]))
        self.polygon = [(float(x), float(z)) for x, z in self.slot.get("polygon", [])]
        self.w = float(self.slot["footprint"]["w"])
        self.d = float(self.slot["footprint"]["d"])
        self.hw, self.hd = self.w * 0.5, self.d * 0.5
        self.front = -self.hd            # z of the street-side wall face
        self.back = +self.hd             # z of the rear wall face
        self.storeys = int(self.slot.get("storeys", 1))
        self.eaves = float(self.slot.get("eavesHeight") or (self.storeys * 3.2 + 0.6))
        self.ridge = self.slot.get("ridge", "along")
        self.ground_y = float(self.slot.get("groundY", 0.0))
        self.outside_wall = bool(self.slot.get("outsideWall", False))
        self.rot_deg = float(self.slot.get("rotationDeg", 0.0))
        self.theta = math.radians(self.rot_deg)

        # The correction. See the module docstring: design -> venue frame.
        self.authored = float(authored)
        self.fix = -2.0 * self.theta
        # What `place` actually applies, normalised to (-pi, pi] so that a
        # residual of -4pi (church: fix -3pi, authored +pi) reads as the zero
        # it is and `place` can skip the rotation entirely.
        self.turn = (self.fix - self.authored + math.pi) % (2 * math.pi) - math.pi
        if abs(self.turn) < 1e-9:
            self.turn = 0.0
        self._c, self._s = math.cos(self.turn), math.sin(self.turn)
        self._ctx = ctx

        # -- ground ---------------------------------------------------------
        # origin[1] is the Y the runtime applies, so venue-local 0 is that
        # world level and every height below is measured from it.
        self.origin_y = float(self.venue["origin"][1])
        g = self._samples(6, margin=0.0)
        ge = self._samples(6, margin=0.45)
        level = None
        for cand in (f"hm.pad.{self.id}", f"hm.pad.{self.id.split('.')[-1]}",
                     f"hm.pad.{name}"):
            try:
                level = T.pad_level(cand)
                break
            except KeyError:
                continue
        self.padded = level is not None
        if level is None:
            # No graded pad: clear the ground the footprint actually touches,
            # or the uphill corner is buried in the slope.
            level = float(np.percentile(g, 92))
        # Local Y of: the floor, and the lowest / highest ground round the plot.
        self.base = level + freeboard - self.origin_y
        self.lo = float(ge.min()) - self.origin_y
        self.hi = float(ge.max()) - self.origin_y

    # -- context ------------------------------------------------------------

    def bind(self, ctx):
        """Attach the build context. Returns self, so `SITE.bind(ctx)` chains."""
        self._ctx = ctx
        return self

    @property
    def ctx(self):
        if self._ctx is None:
            raise RuntimeError(f"Site({self.name!r}) has no context — call "
                               f"SITE.bind(ctx) at the top of build()")
        return self._ctx

    # -- frame --------------------------------------------------------------

    def local(self, x, z):
        """Design-frame (x, z) -> venue-local (x, z)."""
        return (self._c * x + self._s * z, -self._s * x + self._c * z)

    xz = local                       # `Plot`'s name for it

    def p(self, x, y, z):
        """Design-frame point -> venue-local point. For colliders and entities."""
        lx, lz = self.local(x, z)
        return (lx, float(y), lz)

    p3 = p                           # `Plot`'s name for it

    def world(self, x, z):
        """Design-frame (x, z) -> WORLD (x, z). Terrain queries, render cameras.

        This is the composition the whole module exists for, written out: the
        venue frame turned by the runtime's `rotation.y = theta` about the
        placement origin. It reduces to `centre + U*a + V*b`, the plan's own
        formula, which is what makes the result corner-exact on the polygon.
        """
        lx, lz = self.local(x, z)
        c, s = math.cos(self.theta), math.sin(self.theta)
        return (self.centre[0] + c * lx + s * lz,
                self.centre[1] - s * lx + c * lz)

    def yaw(self, a=0.0):
        """Design-frame yaw -> venue-local yaw, for `rot_y=` on a collider."""
        return float(a) + self.turn

    def ground(self, x, z):
        """Terrain height at a design-frame point, in venue-local Y."""
        wx, wz = self.world(x, z)
        return float(T.height(wx, wz)) - self.origin_y

    def drape(self, geom, offset=0.0):
        """Push design-frame geometry onto the ground, per vertex.

        `ground()` answers for ONE point, which is the whole tool a venue has
        had, and a residue patch is not one point. `props.dust_film` and
        `props.spill` lay every lobe at a single flat Y because they cannot
        know the ground; on the 1-in-14 fall of Bakers' Row a 4.4 m ring of
        flour authored at y = 0 was **0.46 m under the street and rendered
        nothing at all**, and the dovecote's droppings ran from +0.44 m in the
        air to −0.36 m buried across one 2.7 m patch. Both were validate
        failures and both are this.

        Semantics are `terrain.drape`'s, which is the contract every generator
        already knows: the local Y is KEPT and read as a height above ground,
        so a 4 mm film stays 4 mm proud of whatever the ground is doing under
        it. The difference is the frame — this takes DESIGN-frame geometry,
        before `place()`, which is what a venue module is holding.

        For ground-hugging residue, paths and scatter. Never a building: a
        building is placed on `base`/`pad_level`, and draping one racks its
        floor.
        """
        if geom is None:
            return geom
        if isinstance(geom, M.Group):
            for m in geom.parts.values():
                self.drape(m, offset)
            return geom
        if len(geom.v) == 0:
            return geom
        c, s = math.cos(self.theta), math.sin(self.theta)
        lx = self._c * geom.v[:, 0] + self._s * geom.v[:, 2]
        lz = -self._s * geom.v[:, 0] + self._c * geom.v[:, 2]
        wx = self.centre[0] + c * lx + s * lz
        wz = self.centre[1] - s * lx + c * lz
        h = T.height(np.asarray(wx, np.float64), np.asarray(wz, np.float64))
        geom.v = geom.v.copy()
        geom.v[:, 1] = (geom.v[:, 1] + h - self.origin_y + offset).astype(np.float32)
        return geom

    def cell_at(self, x=0.0, z=0.0):
        """Grid cell for a design-frame position — for `entity(cell=...)`."""
        wx, wz = self.world(x, z)
        ci = max(0, min(11, int(math.floor(wx / 16.0)) + 6))
        ri = max(1, min(12, int(math.floor(wz / 16.0)) + 7))
        return f"{chr(ord('A') + ci)}{ri}"

    def corners(self):
        """The four world-space footprint corners this Site's frame produces.

        Compared against `slot['polygon']` by `tools/plan/check_siting.py`.
        """
        return [self.world(a, b) for a, b in
                ((-self.hw, self.hd), (self.hw, self.hd),
                 (self.hw, -self.hd), (-self.hw, -self.hd))]

    def _samples(self, n=6, margin=0.0):
        hw, hd = self.w * 0.5 + margin, self.d * 0.5 + margin
        xs, zs = [], []
        for i in range(n):
            for j in range(n):
                a = -hw + 2 * hw * i / (n - 1)
                b = -hd + 2 * hd * j / (n - 1)
                wx, wz = self.world(a, b)
                xs.append(wx)
                zs.append(wz)
        return np.asarray(T.height(np.asarray(xs), np.asarray(zs)), float)

    # -- output -------------------------------------------------------------

    def place(self, geom):
        """Rotate design-frame geometry into the venue frame, in place."""
        if geom is not None and abs(self.turn) > 1e-9:
            geom.rotate_y(self.turn)
        return geom

    def emit(self, geom, material_key=None, **kw):
        if geom is None:
            return None
        return self.ctx.emit(self.place(geom), material_key, **kw)

    def instance(self, mesh_id, mesh, transforms):
        """Instance transforms as (x, y, z) or (x, y, z, yaw), design frame."""
        out = []
        for t in transforms:
            t = list(t)
            lx, lz = self.local(float(t[0]), float(t[2]))
            out.append((lx, float(t[1]), lz,
                        float(t[3]) + self.turn if len(t) > 3 else self.turn))
        return self.ctx.instance(mesh_id, mesh, out)

    def entity(self, eid, archetype, pos, cell=None, **kw):
        return self.ctx.entity(eid, archetype, self.p(*pos),
                               cell=cell or self.cell_at(pos[0], pos[2]), **kw)

    def collider(self, shape="box", **kw):
        """As `ctx.collider`, with centres, hull points and rotations in design
        terms. Also accepts a volume or list of volumes already built by a
        `core.collision` helper, so `segment_box` and `wall_ring` compose."""
        if isinstance(shape, dict):
            return self.ctx.collider(self._turn(shape))
        if isinstance(shape, (list, tuple)):
            return self.ctx.collider([self._turn(v) for v in shape])
        fn = {"box": COL.box, "cylinder": COL.cylinder, "hull": COL.hull}.get(shape)
        if fn is None:
            raise KeyError(f"unknown collider shape '{shape}' (box | cylinder | hull)")
        return self.ctx.collider(self._turn(fn(**kw)))

    def collider_walls(self, width, depth, height, y=0.0, thickness=0.35,
                       center=(0.0, 0.0), rot_y=0.0, doors=(), tag="wall"):
        vols = COL.wall_ring(width, depth, height, y=y, thickness=thickness,
                             center=center, rot_y=rot_y, doors=doors, tag=tag)
        return self.ctx.collider([self._turn(v) for v in vols])

    def collider_steps(self, front, height, tread=0.6, width=1.4, rot_y=0.0):
        vols = COL.steps(front, height, tread=tread, width=width, rot_y=rot_y)
        return self.ctx.collider([self._turn(v) for v in vols])

    def collider_from(self, geom, inset=0.0, y0=None, y1=None, rot_y=0.0,
                      kind="solid", tag=None):
        """Bounds-derived box. NOTE the geometry must still be in design space —
        call this BEFORE `emit`, which is when the mesh is turned."""
        lo, hi = geom.bounds()
        return self.ctx.collider(self._turn(
            COL.from_bounds(lo, hi, inset=inset, y0=y0, y1=y1, rot_y=rot_y,
                            kind=kind, tag=tag)))

    def _turn(self, vol):
        v = dict(vol)
        if "center" in v:
            x, y, z = v["center"]
            lx, lz = self.local(x, z)
            v["center"] = [round(lx, 4), round(y, 4), round(lz, 4)]
        if "points" in v:
            v["points"] = [[round(c, 4) for c in self.local(p[0], p[1])]
                           for p in v["points"]]
        if v.get("shape") == "box":
            r = float(v.get("rotY", 0.0)) + self.turn
            # Normalise so a box on an unrotated plot does not carry a -0.0.
            r = (r + math.pi) % (2 * math.pi) - math.pi
            if abs(r) > 1e-9:
                v["rotY"] = round(r, 4)
            else:
                v.pop("rotY", None)
        return v

    # -- reporting ----------------------------------------------------------

    def report(self):
        return (f"      slot {self.slot['n']:02d} {self.id}  {self.w:g}x{self.d:g} m  "
                f"rot {self.rot_deg:g}  frame fix {math.degrees(self.fix) % 360:.0f}  "
                f"origin_y {self.origin_y:+.2f}  base {self.base:+.2f}  "
                f"ground {self.lo:+.2f}..{self.hi:+.2f}"
                f"{'  [pad]' if self.padded else ''}")


def slab(poly, y0, y1, mat="rubble", chamfer=0.03, uv=None):
    """A vertical prism between two levels, from a PLAN polygon of (x, z).

    `mesh.chamfered_prism` extrudes an XY profile along Z, which is the right
    primitive for a gable and the wrong axes for a plinth; every venue that
    wanted a shaped base was re-deriving the same `rotate_x` by hand. Convex
    polygons only, same as the primitive it wraps.
    """
    h = float(y1) - float(y0)
    if h <= 1e-4:
        return None
    m = M.chamfered_prism([(float(x), float(z)) for x, z in poly], h, mat,
                          chamfer, uv_scale=uv)
    m.rotate_x(math.pi * 0.5)
    m.translate(0.0, float(y0) + h * 0.5, 0.0)
    return m


def plinth_under(site, poly, top, mat="rubble", chamfer=0.03, uv=None,
                 skirt=0.10, minimum=0.34):
    """A stone base from `top` down past the lowest ground under `poly`.

    Directive §6.1: a building on falling ground grows an underbuilding rather
    than floating or gapping at its base. `poly` is a design-frame polygon of
    (x, z) and the base is taken from the terrain under its own corners, not
    from a constant. Returns `(mesh, base_y)`.
    """
    lo = min(site.ground(x, z) for x, z in poly)
    y0 = min(float(top) - minimum, lo - skirt)
    return slab(poly, y0, top, mat, chamfer, uv), y0


def rect(cx, cz, w, d):
    """Plan rectangle as a CCW polygon of (x, z), for `slab`/`plinth_under`."""
    return [(cx - w * 0.5, cz - d * 0.5), (cx + w * 0.5, cz - d * 0.5),
            (cx + w * 0.5, cz + d * 0.5), (cx - w * 0.5, cz + d * 0.5)]
