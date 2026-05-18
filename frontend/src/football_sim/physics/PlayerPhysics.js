/**
 * PlayerPhysics - Player movement physics with inertia, turning radius, acceleration curves
 */
import { Vector2 } from '../core/Vector2.js';
import {
  PLAYER_RADIUS, PLAYER_MASS, PLAYER_MIN_SPEED, PLAYER_MAX_SPEED,
  PLAYER_WALK_SPEED, PLAYER_JOG_SPEED, PLAYER_ACCEL_TIME_MIN,
  PLAYER_ACCEL_TIME_MAX, PLAYER_DECEL_FACTOR, PLAYER_TURN_RATE_BASE,
  PLAYER_TURN_RATE_SPRINT, ATTR_MIN, ATTR_MAX, PITCH_WIDTH, PITCH_HEIGHT
} from '../core/Constants.js';

export class PlayerPhysics {
  constructor() {
    // Reusable vectors to reduce GC
    this._tempVec = new Vector2();
  }

  /**
   * Calculate max sprint speed for a player based on pace attribute
   * @param {number} pace - Pace attribute 1-20
   * @param {number} fatigueFactor - 0-1 (1 = full stamina)
   * @returns {number} Max speed in m/s
   */
  getMaxSpeed(pace, fatigueFactor = 1) {
    const normalized = (pace - ATTR_MIN) / (ATTR_MAX - ATTR_MIN);
    const baseSpeed = PLAYER_MIN_SPEED + normalized * (PLAYER_MAX_SPEED - PLAYER_MIN_SPEED);
    return baseSpeed * fatigueFactor;
  }

  /**
   * Calculate acceleration for a player
   * @param {number} accelAttr - Acceleration attribute 1-20
   * @returns {number} Acceleration in m/s²
   */
  getAcceleration(accelAttr) {
    const normalized = (accelAttr - ATTR_MIN) / (ATTR_MAX - ATTR_MIN);
    const accelTime = PLAYER_ACCEL_TIME_MAX - normalized * (PLAYER_ACCEL_TIME_MAX - PLAYER_ACCEL_TIME_MIN);
    // a = v_max / t
    return PLAYER_MAX_SPEED / accelTime;
  }

  /**
   * Calculate deceleration (faster than acceleration)
   * @param {number} accelAttr
   * @returns {number}
   */
  getDeceleration(accelAttr) {
    return this.getAcceleration(accelAttr) / PLAYER_DECEL_FACTOR;
  }

  /**
   * Calculate turning rate based on current speed
   * @param {number} currentSpeed - Current speed in m/s
   * @param {number} agilityAttr - Agility attribute 1-20
   * @returns {number} Turn rate in radians/sec
   */
  getTurnRate(currentSpeed, agilityAttr) {
    const speedFactor = currentSpeed / PLAYER_MAX_SPEED; // 0-1
    const agilityFactor = agilityAttr / ATTR_MAX;
    
    // Interpolate between base and sprint turn rates
    const baseTurn = PLAYER_TURN_RATE_BASE * (0.5 + 0.5 * agilityFactor);
    const sprintTurn = PLAYER_TURN_RATE_SPRINT * (0.5 + 0.5 * agilityFactor);
    
    return baseTurn + (sprintTurn - baseTurn) * speedFactor;
  }

  /**
   * Update player physics for one timestep
   * @param {Object} player - Player entity
   * @param {number} dt - Delta time
   */
  update(player, dt) {
    if (!player.isActive) return;

    const attrs = player.attributes;
    const fatigueFactor = player.getFatigueFactor();

    // Determine target based on movement state
    const targetPos = player.targetPosition;
    if (!targetPos) {
      // No target - decelerate to stop
      this._decelerate(player, dt);
      return;
    }

    const toTarget = targetPos.sub(player.position);
    const distToTarget = toTarget.length();

    // If very close to target, stop
    if (distToTarget < 0.3) {
      this._decelerate(player, dt);
      player.targetPosition = null;
      return;
    }

    // Calculate desired direction
    const desiredAngle = Math.atan2(toTarget.y, toTarget.x);
    
    // Turn towards target
    this._turnTowards(player, desiredAngle, dt, attrs.agility || 10);

    // Determine desired speed based on movement mode
    let desiredSpeed;
    switch (player.movementMode) {
      case 'sprint':
        desiredSpeed = this.getMaxSpeed(attrs.pace || 10, fatigueFactor);
        break;
      case 'jog':
        desiredSpeed = PLAYER_JOG_SPEED;
        break;
      case 'walk':
        desiredSpeed = PLAYER_WALK_SPEED;
        break;
      default:
        desiredSpeed = PLAYER_JOG_SPEED;
    }

    // Slow down when approaching target
    if (distToTarget < 3) {
      desiredSpeed = Math.min(desiredSpeed, distToTarget * 2);
    }

    // Accelerate or decelerate to desired speed
    const currentSpeed = player.velocity.length();
    const accel = this.getAcceleration(attrs.acceleration || 10);
    const decel = this.getDeceleration(attrs.acceleration || 10);

    if (currentSpeed < desiredSpeed) {
      // Accelerate
      const newSpeed = Math.min(desiredSpeed, currentSpeed + accel * dt);
      const dir = Vector2.fromAngle(player.facing);
      player.velocity = dir.mul(newSpeed);
    } else if (currentSpeed > desiredSpeed + 0.5) {
      // Decelerate
      const newSpeed = Math.max(desiredSpeed, currentSpeed - decel * dt);
      if (newSpeed < 0.1) {
        player.velocity.set(0, 0);
      } else {
        player.velocity.normalizeMut().mulMut(newSpeed);
      }
    } else {
      // Maintain speed in facing direction
      const dir = Vector2.fromAngle(player.facing);
      player.velocity = dir.mul(currentSpeed);
    }

    // Integrate position
    player.position.x += player.velocity.x * dt;
    player.position.y += player.velocity.y * dt;

    // Keep player on pitch (with small margin)
    player.position.x = Math.max(0.5, Math.min(PITCH_WIDTH - 0.5, player.position.x));
    player.position.y = Math.max(0.5, Math.min(PITCH_HEIGHT - 0.5, player.position.y));

    // Update speed for animation
    player.currentSpeed = player.velocity.length();
  }

  /**
   * Turn player towards desired angle
   */
  _turnTowards(player, desiredAngle, dt, agility) {
    const currentAngle = player.facing;
    let angleDiff = desiredAngle - currentAngle;

    // Normalize to [-PI, PI]
    while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
    while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;

    const turnRate = this.getTurnRate(player.currentSpeed, agility);
    const maxTurn = turnRate * dt;

    if (Math.abs(angleDiff) <= maxTurn) {
      player.facing = desiredAngle;
    } else {
      player.facing += Math.sign(angleDiff) * maxTurn;
    }

    // Normalize facing
    while (player.facing > Math.PI) player.facing -= Math.PI * 2;
    while (player.facing < -Math.PI) player.facing += Math.PI * 2;
  }

  /**
   * Decelerate player to stop
   */
  _decelerate(player, dt) {
    const speed = player.velocity.length();
    if (speed < 0.1) {
      player.velocity.set(0, 0);
      player.currentSpeed = 0;
      return;
    }

    const decel = this.getDeceleration(player.attributes.acceleration || 10);
    const newSpeed = Math.max(0, speed - decel * dt);
    player.velocity.normalizeMut().mulMut(newSpeed);
    player.currentSpeed = newSpeed;
  }

  /**
   * Move player directly to a position (for set pieces, teleporting)
   */
  teleport(player, position) {
    player.position.copy(position);
    player.velocity.set(0, 0);
    player.currentSpeed = 0;
  }
}
