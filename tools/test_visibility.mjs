#!/usr/bin/env node
/**
 * Tests for client/src/lod.js — LOD selection, culling and portals.
 *
 *     node tools/test_visibility.mjs
 *
 * The runtime half of what tools/test_batching.py covers on the build side,
 * and it exists for the same reason: `ctx.interior` has no venue consumer yet.
 * The church is the first building with a walkable interior and it is not
 * built, so without this the portal code would first run in anger inside the
 * most important composition in the project (Directive section 3), and the
 * agent who found the bug would have no way to tell whose it was.
 *
 * Synthetic placements rather than real venues on purpose: this is about the
 * DECISION — draw / do not draw, and at which level — not about geometry.
 */
import * as THREE from 'three';
import { VisibilitySet } from '../client/src/lod.js';

let fails = 0;
const check = (c, m) => { console.log((c ? '  ok   ' : '  FAIL ') + m); if (!c) fails++; };

function boxObj(name, hm, size, pos) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(...size), new THREE.MeshBasicMaterial());
  m.name = name;
  m.userData.hm = hm;
  m.position.set(...pos);
  return m;
}

// A venue at the origin: one street cell, plus a nave running z = -28 .. -10
// with its great door in the z = -10 wall. The door's OUTWARD normal is +z,
// because the street is at +z — getting that sign backwards is the whole of
// what a portal can get wrong, and it makes the interior visible from behind
// the building and invisible from the doorway.
const root = new THREE.Group();
root.add(boxObj('v#0_0', { venue: 'v', cell: '0_0', interior: null, lod: 0, prims: 3, tris: 900 },
                [8, 6, 8], [0, 3, 0]));
root.add(boxObj('v#0_0$lod1', { venue: 'v', cell: '0_0', interior: null, lod: 1, prims: 2, tris: 450 },
                [8, 6, 8], [0, 3, 0]));
root.add(boxObj('v#0_0$lod3', { venue: 'v', cell: '0_0', interior: null, lod: 3, prims: 1, tris: 60 },
                [8, 6, 8], [0, 3, 0]));
root.add(boxObj('v#int:nave', { venue: 'v', cell: null, interior: 'nave', lod: 0, prims: 4, tris: 9000 },
                [8, 8, 18], [0, 4, -19]));
// Clutter with a build-time size cull.
root.add(boxObj('v#0_0@grit', { venue: 'v', cell: '0_0', interior: null, lod: 0,
                                meshId: 'grit', instances: 200, cullAt: 40, prims: 1, tris: 6000 },
                [0.2, 0.1, 0.2], [4, 0, 4]));
root.position.set(0, 0, 0);

const manifest = {
  lodDistances: [15, 40, 100],
  interiors: [{ id: 'nave', aabb: [[-4, 0, -28], [4, 8, -10]],
                portals: [{ pos: [0, 1.4, -10], size: [3, 4], normal: [0, 1], range: 30 }] }],
};

const vis = new VisibilitySet({ grid: { cellSize: 16, cols: 'ABCDEFGHIJKL'.split(''), rows: [...Array(12)].map((_, i) => i + 1) } });
vis.addPlacement(root, manifest, 'v');

const cam = new THREE.PerspectiveCamera(55, 16 / 9, 0.1, 500);
const look = (x, y, z, tx, ty, tz) => {
  cam.position.set(x, y, z); cam.lookAt(tx, ty, tz);
  cam.updateMatrixWorld(true);
  return vis.update(cam);
};
const grp = n => vis.groups.find(g => g.key.includes(n));
const drawn = n => grp(n).current >= 0;

console.log('LOD selection');
look(0, 1.6, 10, 0, 3, 0);
check(grp('#0_0').current === 0, `at 6 m the cell draws LOD0 (got ${grp('#0_0').current})`);
look(0, 1.6, 40, 0, 3, 0);
check(grp('#0_0').current === 1, `at 36 m it draws LOD1 (got ${grp('#0_0').current})`);
look(0, 1.6, 130, 0, 3, 0);
check(grp('#0_0').current === 3, `at 126 m it falls to the impostor, skipping the absent LOD2 ` +
                                 `(got ${grp('#0_0').current})`);

console.log('\nfrustum + distance culling');
look(0, 1.6, -60, 0, 3, -120);
check(!drawn('#0_0'), 'a cell behind the camera is not drawn');
const s = look(0, 1.6, 300, 0, 3, 260);
check(s.culledDistance >= 1, `beyond the 190 m cull radius nothing is drawn ` +
                             `(${s.culledDistance} culled by distance)`);

console.log('\nbuild-time size cull');
look(4, 1.6, 14, 4, 0, 4);
check(drawn('@grit'), 'clutter 10 m away is drawn');
look(4, 1.6, 60, 4, 0, 4);
check(!drawn('@grit'), 'the same clutter at 56 m is dropped by its cullAt of 40 m');
check(drawn('#0_0'), '...while the building beside it is not');

console.log('\nportals');
look(0, 1.6, 2, 0, 1.4, -10);
check(drawn('int:nave'), 'drawn from the street 12 m in front of the open door, looking in');
look(0, 1.6, 2, 0, 1.4, 40);
check(!drawn('int:nave'), 'not drawn from the same spot with the door behind the camera');
look(0, 4, -19, 0, 4, -28);
check(drawn('int:nave'), 'drawn when the camera is inside the volume');
look(0, 1.6, -60, 0, 1.4, -20);
check(!drawn('int:nave'), 'not drawn from behind the church, through the far wall');
look(0, 1.6, 45, 0, 1.4, -10);
check(!drawn('int:nave'), 'not drawn from 55 m up the street — past the portal range');
look(60, 1.6, -10, 0, 1.4, -10);
check(!drawn('int:nave'), 'not drawn from side-on, where the doorway is edge-to-camera');

console.log('\nattribution');
const st = look(0, 1.6, 10, 0, 3, 0);
check(st.byVenue.v && st.byVenue.v.prims > 0, `per-venue attribution present (v: ${st.byVenue.v?.prims} prims)`);
check(Object.keys(st.byCell).some(k => /^[A-L]\d+$/.test(k)),
      `per-cell attribution uses town cell labels (${Object.keys(st.byCell).join(', ')})`);

console.log(`\n${fails} failure(s)`);
process.exit(fails ? 1 : 0);
