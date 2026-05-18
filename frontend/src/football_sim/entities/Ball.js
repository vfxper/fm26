/**
 * Ball - Ball entity with position, velocity, spin, height
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT } from '../core/Constants.js';

export class Ball {
  constructor() {
    // Position on pitch (meters)
    this.position = new Vector2(PITCH_WIDTH / 2, PITCH_HEIGHT / 2);
    
    // Velocity (m/s)
    this.velocity = new Vector2(0, 0);
    
    // Height above ground (meters) - for headers, lobs, crosses
    this.height = 0;
    
    // Vertical velocity (m/s)
    this.verticalVelocity = 0;
    
    // Spin (affects curve via Magnus effect)
    this.spin = 0; // positive = clockwise, negative = counter-clockwise
    
    // Roll angle for visual rotation
    this.rollAngle = 0;
    
    // State
    this.isHeld = false; // Is a player controlling the ball?
    this.holder = null; // Reference to controlling player
    this.lastTouchedBy = null; // Last player to touch
    this.lastTouchedTeam = null; // 'home' or 'away'
    
    // Out of bounds
    this.isOutOfBounds = false;
    this.outType = null; // 'throw_in', 'goal_kick', 'corner', 'goal'
    
    // Trail for rendering
    this.trail = [];
    this.maxTrailLength = 10;
    
    // Previous position for interpolation
    this.prevPosition = this.position.clone();
  }

  /**
   * Store previous position for render interpolation
   */
  storePrevious() {
    this.prevPosition.copy(this.position);
  }

  /**
   * Get interpolated position for smooth rendering
   * @param {number} alpha - Interpolation factor 0-1
   */
  getInterpolatedPosition(alpha) {
    return this.prevPosition.lerp(this.position, alpha);
  }

  /**
   * Update trail
   */
  updateTrail() {
    const speed = this.velocity.length();
    if (speed > 5) { // Only show trail for fast-moving ball
      this.trail.push({
        x: this.position.x,
        y: this.position.y,
        speed: speed
      });
      if (this.trail.length > this.maxTrailLength) {
        this.trail.shift();
      }
    } else {
      if (this.trail.length > 0) {
        this.trail.shift();
      }
    }
  }

  /**
   * Reset ball to center
   */
  resetToCenter() {
    this.position.set(PITCH_WIDTH / 2, PITCH_HEIGHT / 2);
    this.velocity.set(0, 0);
    this.height = 0;
    this.verticalVelocity = 0;
    this.spin = 0;
    this.isHeld = false;
    this.holder = null;
    this.isOutOfBounds = false;
    this.outType = null;
    this.trail = [];
  }

  /**
   * Place ball at specific position (for set pieces)
   */
  placeAt(x, y) {
    this.position.set(x, y);
    this.velocity.set(0, 0);
    this.height = 0;
    this.verticalVelocity = 0;
    this.spin = 0;
    this.isHeld = false;
    this.holder = null;
    this.isOutOfBounds = false;
    this.outType = null;
  }

  /**
   * Get ball speed in m/s
   */
  getSpeed() {
    return this.velocity.length();
  }

  /**
   * Check if ball is on the ground
   */
  isGrounded() {
    return this.height < 0.1;
  }

  /**
   * Check if ball is in the air (for headers)
   */
  isAerial() {
    return this.height > 1.0;
  }
}
