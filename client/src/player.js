/**
 * Third-person character controller and camera rig.
 *
 * The game is always default third-person, so this rig — not a free-fly
 * camera — defines what the player sees and therefore what every asset in the
 * town is judged against. It matches the `gameplay` view in the review
 * harness: ~3.6m behind, ~2.05m high, 55° FOV, character in frame.
 *
 * Movement resolves a swept capsule against the AUTHORED collision volumes in
 * content/collision/ (client/src/collision.js). Three behaviours are what make
 * a town feel walkable rather than like a maze of invisible boxes:
 *
 *   - sliding, so a glancing hit on a wall costs speed and not control;
 *   - step-up, so kerbs, thresholds and the bottom step are walked over
 *     instead of being 0.16 m walls;
 *   - ground following, so the player stands on the road surface and on
 *     terrain rather than on the y=0 plane the town was authored against.
 */

import * as THREE from 'three';
import { STEP_HEIGHT } from './collision.js';

export const EYE_HEIGHT = 1.62;      // Art Bible §3
export const BODY_HEIGHT = 1.75;
export const RADIUS = 0.32;          // capsule cross-section

const WALK = 2.6;      // m/s — a relaxed town pace
const RUN = 5.2;
const ACCEL = 14.0;
const TURN_RATE = 9.0;

// Ground following. Rising is near-instant (a step should feel crisp);
// falling is slower so walking off a kerb does not snap the camera down.
const RISE_RATE = 18.0;
const FALL_RATE = 9.0;

export class ThirdPersonController {
  constructor(camera, domElement) {
    this.camera = camera;
    this.dom = domElement;

    this.position = new THREE.Vector3(0, 0, -44);
    this.velocity = new THREE.Vector3();
    this.facing = Math.PI;             // spawn looking south, down Ford Road

    // Camera orbit state.
    this.yaw = Math.PI;
    this.pitch = 0.13;                 // slight downward tilt, MMO default
    this.distance = 3.6;
    this.minDistance = 0.9;
    this.maxDistance = 9.0;
    this.height = 2.05;
    this._camDist = this.distance;     // smoothed boom length

    this.world = null;                 // CollisionWorld
    this.terrain = () => 0;            // height(x, z)
    this.groundY = 0;

    this.keys = new Set();
    this.dragging = false;
    this._bind();

    this.avatar = this._buildAvatar();
  }

  _bind() {
    const d = this.dom;
    addEventListener('keydown', e => {
      this.keys.add(e.code);
      if (e.code === 'Space') e.preventDefault();
    });
    addEventListener('keyup', e => this.keys.delete(e.code));

    d.addEventListener('mousedown', () => { this.dragging = true; });
    addEventListener('mouseup', () => { this.dragging = false; });
    addEventListener('mousemove', e => {
      if (!this.dragging) return;
      this.yaw -= e.movementX * 0.0042;
      this.pitch = THREE.MathUtils.clamp(this.pitch + e.movementY * 0.0034, -0.45, 1.05);
    });
    d.addEventListener('wheel', e => {
      this.distance = THREE.MathUtils.clamp(
        this.distance + Math.sign(e.deltaY) * 0.45, 1.2, this.maxDistance);
      e.preventDefault();
    }, { passive: false });
    d.addEventListener('contextmenu', e => e.preventDefault());
  }

  /** Placeholder avatar at exact Art Bible proportions (1.75m, eye at 1.62m). */
  _buildAvatar() {
    const g = new THREE.Group();
    const cloth = new THREE.MeshStandardMaterial({ color: 0x3E5470, roughness: 0.82 });
    const skin = new THREE.MeshStandardMaterial({ color: 0xC08A62, roughness: 0.7 });
    const add = (geo, mat, y, x = 0, z = 0) => {
      const m = new THREE.Mesh(geo, mat);
      m.position.set(x, y, z);
      m.castShadow = true;
      g.add(m);
      return m;
    };
    add(new THREE.CapsuleGeometry(0.17, 0.46, 6, 14), cloth, 1.16);
    add(new THREE.SphereGeometry(0.115, 20, 16), skin, 1.60);
    this.legL = add(new THREE.CapsuleGeometry(0.078, 0.60, 4, 10), cloth, 0.46, -0.10);
    this.legR = add(new THREE.CapsuleGeometry(0.078, 0.60, 4, 10), cloth, 0.46, 0.10);
    this.armL = add(new THREE.CapsuleGeometry(0.056, 0.50, 4, 10), cloth, 1.18, -0.255);
    this.armR = add(new THREE.CapsuleGeometry(0.056, 0.50, 4, 10), cloth, 1.18, 0.255);
    return g;
  }

  /** Attach the authored collision world and the terrain height function. */
  bindWorld(world, terrain) {
    this.world = world;
    if (terrain) this.terrain = terrain;
    this.position.y = this.groundHeight(this.position.x, this.position.z, this.position.y);
    this.groundY = this.position.y;
  }

  groundHeight(x, z, feetY) {
    const base = this.terrain(x, z);
    if (!this.world) return base;
    return this.world.groundAt(x, z, feetY, base, STEP_HEIGHT);
  }

  get speed() {
    return this.keys.has('ShiftLeft') || this.keys.has('ShiftRight') ? RUN : WALK;
  }

  update(dt) {
    // Movement is relative to the camera, which is what every MMO does and
    // what players expect from a third-person rig.
    const f = new THREE.Vector3(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
    const r = new THREE.Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw));

    const wish = new THREE.Vector3();
    if (this.keys.has('KeyW') || this.keys.has('ArrowUp')) wish.add(f);
    if (this.keys.has('KeyS') || this.keys.has('ArrowDown')) wish.sub(f);
    if (this.keys.has('KeyD') || this.keys.has('ArrowRight')) wish.add(r);
    if (this.keys.has('KeyA') || this.keys.has('ArrowLeft')) wish.sub(r);

    const moving = wish.lengthSq() > 1e-6;
    if (moving) wish.normalize().multiplyScalar(this.speed);

    this.velocity.lerp(wish, Math.min(1, ACCEL * dt));

    // Resolve against the surface the player is standing on RIGHT NOW, not the
    // smoothed render height: using the lagging value makes the base of every
    // step briefly solid and the player stalls against thresholds they are
    // already stepping onto.
    const stand = this.groundHeight(this.position.x, this.position.z, this.position.y);
    const feet = Math.max(this.position.y, stand);

    let nx = this.position.x + this.velocity.x * dt;
    let nz = this.position.z + this.velocity.z * dt;
    if (this.world) {
      const res = this.world.moveCircle(
        this.position.x, this.position.z,
        this.velocity.x * dt, this.velocity.z * dt,
        RADIUS, feet, BODY_HEIGHT, STEP_HEIGHT);
      nx = res.x; nz = res.z;
    }
    this.position.x = nx;
    this.position.z = nz;

    // Ground follow.
    this.groundY = this.groundHeight(nx, nz, feet);
    const dy = this.groundY - this.position.y;
    const rate = dy > 0 ? RISE_RATE : FALL_RATE;
    this.position.y += dy * Math.min(1, rate * dt);
    if (Math.abs(this.groundY - this.position.y) < 0.004) this.position.y = this.groundY;

    // Face the direction of travel.
    if (moving) {
      const target = Math.atan2(this.velocity.x, this.velocity.z);
      let d = target - this.facing;
      while (d > Math.PI) d -= Math.PI * 2;
      while (d < -Math.PI) d += Math.PI * 2;
      this.facing += d * Math.min(1, TURN_RATE * dt);
    }

    this.avatar.position.copy(this.position);
    this.avatar.rotation.y = this.facing;

    // Walk cycle — a static avatar reads as a mannequin.
    const sp = this.velocity.length();
    this._phase = (this._phase || 0) + dt * sp * 2.6;
    const sw = Math.sin(this._phase) * Math.min(0.5, sp * 0.14);
    this.legL.rotation.x = sw;
    this.legR.rotation.x = -sw;
    this.armL.rotation.x = -sw * 0.75;
    this.armR.rotation.x = sw * 0.75;

    this._updateCamera(dt);
  }

  _updateCamera(dt) {
    const focus = this.position.clone();
    focus.y += EYE_HEIGHT * 0.92;
    const dir = new THREE.Vector3(
      Math.sin(this.yaw) * Math.cos(this.pitch),
      Math.sin(this.pitch),
      Math.cos(this.yaw) * Math.cos(this.pitch),
    );

    // Pull in when something is between the camera and the player. The probe
    // has a radius, so the near plane never ends up inside a wall — testing an
    // infinitely thin ray is what makes a camera clip corners.
    let want = this.distance;
    if (this.world) {
      want = Math.min(want, this.world.probe(
        focus.x, focus.y, focus.z, dir.x, dir.y, dir.z, this.distance, 0.28));
      want = Math.max(this.minDistance, want);
    }

    // Asymmetric smoothing. Pulling IN must be fast or the camera is briefly
    // inside the wall, but instant is what makes it feel like a snap, so it is
    // damped rather than clamped; pushing OUT is slow, because a camera that
    // springs back the moment a doorway clears is worse than one that lingers.
    const tau = want < this._camDist ? 0.055 : 0.30;
    this._camDist += (want - this._camDist) * (1 - Math.exp(-dt / tau));

    this.camera.position.copy(focus).addScaledVector(dir, this._camDist);
    // Rise toward the shoulder as the boom extends; at minimum length the
    // camera must not climb, or a wall-pinned camera stares at the player's
    // scalp.
    const lift = (this.height - EYE_HEIGHT) * 0.55 *
                 THREE.MathUtils.clamp(this._camDist / this.distance, 0, 1);
    this.camera.position.y += lift;

    // Never let the eye drop below the ground it is standing over.
    const floor = this.terrain(this.camera.position.x, this.camera.position.z) + 0.45;
    if (this.camera.position.y < floor) this.camera.position.y = floor;

    this.camera.lookAt(focus.x, focus.y + 0.25, focus.z);
  }
}
