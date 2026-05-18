/**
 * Vector2 - 2D Vector math utility class
 * Immutable operations return new vectors; mutating operations modify in-place for performance.
 */
export class Vector2 {
  constructor(x = 0, y = 0) {
    this.x = x;
    this.y = y;
  }

  clone() {
    return new Vector2(this.x, this.y);
  }

  set(x, y) {
    this.x = x;
    this.y = y;
    return this;
  }

  copy(v) {
    this.x = v.x;
    this.y = v.y;
    return this;
  }

  add(v) {
    return new Vector2(this.x + v.x, this.y + v.y);
  }

  addMut(v) {
    this.x += v.x;
    this.y += v.y;
    return this;
  }

  sub(v) {
    return new Vector2(this.x - v.x, this.y - v.y);
  }

  subMut(v) {
    this.x -= v.x;
    this.y -= v.y;
    return this;
  }

  mul(scalar) {
    return new Vector2(this.x * scalar, this.y * scalar);
  }

  mulMut(scalar) {
    this.x *= scalar;
    this.y *= scalar;
    return this;
  }

  div(scalar) {
    if (scalar === 0) return new Vector2(0, 0);
    return new Vector2(this.x / scalar, this.y / scalar);
  }

  divMut(scalar) {
    if (scalar === 0) { this.x = 0; this.y = 0; return this; }
    this.x /= scalar;
    this.y /= scalar;
    return this;
  }

  dot(v) {
    return this.x * v.x + this.y * v.y;
  }

  cross(v) {
    return this.x * v.y - this.y * v.x;
  }

  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y);
  }

  lengthSq() {
    return this.x * this.x + this.y * this.y;
  }

  normalize() {
    const len = this.length();
    if (len === 0) return new Vector2(0, 0);
    return new Vector2(this.x / len, this.y / len);
  }

  normalizeMut() {
    const len = this.length();
    if (len === 0) { this.x = 0; this.y = 0; return this; }
    this.x /= len;
    this.y /= len;
    return this;
  }

  distance(v) {
    const dx = this.x - v.x;
    const dy = this.y - v.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  distanceSq(v) {
    const dx = this.x - v.x;
    const dy = this.y - v.y;
    return dx * dx + dy * dy;
  }

  angle() {
    return Math.atan2(this.y, this.x);
  }

  angleTo(v) {
    return Math.atan2(v.y - this.y, v.x - this.x);
  }

  rotate(radians) {
    const cos = Math.cos(radians);
    const sin = Math.sin(radians);
    return new Vector2(
      this.x * cos - this.y * sin,
      this.x * sin + this.y * cos
    );
  }

  lerp(v, t) {
    return new Vector2(
      this.x + (v.x - this.x) * t,
      this.y + (v.y - this.y) * t
    );
  }

  perpendicular() {
    return new Vector2(-this.y, this.x);
  }

  reflect(normal) {
    const d = 2 * this.dot(normal);
    return new Vector2(this.x - d * normal.x, this.y - d * normal.y);
  }

  clampLength(maxLen) {
    const lenSq = this.lengthSq();
    if (lenSq > maxLen * maxLen) {
      const len = Math.sqrt(lenSq);
      return new Vector2((this.x / len) * maxLen, (this.y / len) * maxLen);
    }
    return this.clone();
  }

  clampLengthMut(maxLen) {
    const lenSq = this.lengthSq();
    if (lenSq > maxLen * maxLen) {
      const len = Math.sqrt(lenSq);
      this.x = (this.x / len) * maxLen;
      this.y = (this.y / len) * maxLen;
    }
    return this;
  }

  equals(v, epsilon = 0.0001) {
    return Math.abs(this.x - v.x) < epsilon && Math.abs(this.y - v.y) < epsilon;
  }

  toString() {
    return `(${this.x.toFixed(2)}, ${this.y.toFixed(2)})`;
  }

  static fromAngle(radians, length = 1) {
    return new Vector2(Math.cos(radians) * length, Math.sin(radians) * length);
  }

  static zero() {
    return new Vector2(0, 0);
  }

  static random(rng) {
    const angle = (rng ? rng() : Math.random()) * Math.PI * 2;
    return new Vector2(Math.cos(angle), Math.sin(angle));
  }
}
