/**
 * Third-person character controller and camera rig.
 *
 * The game is always default third-person, so this rig — not a free-fly
 * camera — defines what the player sees and therefore what every asset in the
 * town is judged against. It matches the `gameplay` view in the review
 * harness: ~3.6m behind, ~2.05m high, 55° FOV, character in frame.
 */

import * as THREE from 'three';

export const EYE_HEIGHT = 1.62;      // Art Bible §3
export const BODY_HEIGHT = 1.75;

const WALK = 2.6;      // m/s — a relaxed town pace
const RUN = 5.2;
const ACCEL = 14.0;
const TURN_RATE = 9.0;

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
    this.minDistance = 1.2;
    this.maxDistance = 9.0;
    this.height = 2.05;

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
        this.distance + Math.sign(e.deltaY) * 0.45, this.minDistance, this.maxDistance);
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

  get speed() {
    return this.keys.has('ShiftLeft') || this.keys.has('ShiftRight') ? RUN : WALK;
  }

  update(dt, colliders = []) {
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
    const step = this.velocity.clone().multiplyScalar(dt);

    // Collision: cheap swept-circle against axis-aligned boxes. Enough to keep
    // the player out of buildings without a physics engine.
    const next = this.position.clone().add(step);
    this._resolve(next, colliders);
    this.position.copy(next);

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

    this._updateCamera(colliders);
  }

  _resolve(next, colliders) {
    const R = 0.32;   // player radius
    for (const c of colliders) {
      const minX = c.min.x - R, maxX = c.max.x + R;
      const minZ = c.min.z - R, maxZ = c.max.z + R;
      if (next.x > minX && next.x < maxX && next.z > minZ && next.z < maxZ) {
        // Push out along the shallowest axis.
        const dl = next.x - minX, dr = maxX - next.x;
        const db = next.z - minZ, df = maxZ - next.z;
        const m = Math.min(dl, dr, db, df);
        if (m === dl) next.x = minX;
        else if (m === dr) next.x = maxX;
        else if (m === db) next.z = minZ;
        else next.z = maxZ;
      }
    }
  }

  _updateCamera(colliders) {
    const focus = this.position.clone().setY(EYE_HEIGHT * 0.92);
    const dir = new THREE.Vector3(
      Math.sin(this.yaw) * Math.cos(this.pitch),
      Math.sin(this.pitch),
      Math.cos(this.yaw) * Math.cos(this.pitch),
    );

    // Pull in if a wall is between camera and player — without this the camera
    // clips through buildings constantly in a dense town.
    let dist = this.distance;
    for (const c of colliders) {
      for (let t = 0.25; t < dist; t += 0.25) {
        const p = focus.clone().addScaledVector(dir, t);
        if (p.x > c.min.x && p.x < c.max.x && p.z > c.min.z && p.z < c.max.z &&
            p.y > c.min.y && p.y < c.max.y) {
          dist = Math.max(this.minDistance, t - 0.25);
          break;
        }
      }
    }

    this.camera.position.copy(focus).addScaledVector(dir, dist);
    this.camera.position.y = Math.max(0.35, this.camera.position.y + (this.height - EYE_HEIGHT) * 0.55);
    this.camera.lookAt(focus.x, focus.y + 0.25, focus.z);
  }
}
