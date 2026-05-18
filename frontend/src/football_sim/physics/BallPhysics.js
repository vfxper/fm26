/**
 * BallPhysics - Realistic ball physics with drag, Magnus effect, bounce, spin
 */
import { Vector2 } from '../core/Vector2.js';
import {
  BALL_MASS, BALL_RADIUS, BALL_DRAG_COEFFICIENT, BALL_AIR_DENSITY,
  BALL_CROSS_SECTION, BALL_BOUNCE_RESTITUTION, BALL_MAX_SPEED,
  BALL_MAGNUS_COEFFICIENT, GRAVITY, FRICTION_DRY, FRICTION_WET, FRICTION_SNOW,
  PITCH_WIDTH, PITCH_HEIGHT
} from '../core/Constants.js';

export class BallPhysics {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.weatherFriction = FRICTION_DRY;
    this.windForce = new Vector2(0, 0);
  }

  /**
   * Set weather conditions
   * @param {string} weather - 'dry', 'wet', 'snow'
   * @param {Vector2} wind - Wind force vector
   */
  setWeather(weather, wind = new Vector2(0, 0)) {
    switch (weather) {
      case 'wet': this.weatherFriction = FRICTION_WET; break;
      case 'snow': this.weatherFriction = FRICTION_SNOW; break;
      default: this.weatherFriction = FRICTION_DRY;
    }
    this.windForce = wind;
  }

  /**
   * Update ball physics for one timestep
   * @param {Object} ball - Ball entity
   * @param {number} dt - Delta time in seconds
   */
  update(ball, dt) {
    if (ball.isHeld) return; // Ball is being controlled by a player

    // Apply forces
    this._applyAirDrag(ball, dt);
    this._applyMagnusEffect(ball, dt);
    this._applyWind(ball, dt);
    this._applyGravity(ball, dt);
    this._applyGroundFriction(ball, dt);

    // Integrate position
    ball.position.x += ball.velocity.x * dt;
    ball.position.y += ball.velocity.y * dt;
    ball.height += ball.verticalVelocity * dt;

    // Ground bounce
    if (ball.height <= 0 && ball.verticalVelocity < 0) {
      ball.height = 0;
      ball.verticalVelocity = -ball.verticalVelocity * BALL_BOUNCE_RESTITUTION;
      // Reduce horizontal velocity on bounce
      ball.velocity.mulMut(0.85);
      // Reduce spin on bounce
      ball.spin *= 0.7;

      // If very small bounce, settle on ground
      if (Math.abs(ball.verticalVelocity) < 0.3) {
        ball.verticalVelocity = 0;
        ball.height = 0;
      }
    }

    // Clamp max speed
    const speed = ball.velocity.length();
    if (speed > BALL_MAX_SPEED) {
      ball.velocity.normalizeMut().mulMut(BALL_MAX_SPEED);
    }

    // Spin decay
    ball.spin *= (1 - 0.5 * dt);

    // Track ball roll distance for spin visual
    ball.rollAngle += speed * dt / BALL_RADIUS;

    // Boundary checks (ball out of play handled by MatchManager)
    this._checkBoundaries(ball);
  }

  /**
   * Apply quadratic air drag: F = -0.5 * Cd * rho * A * v² * v_hat
   * ONLY applies when ball is in the air (height > 0.1m)
   */
  _applyAirDrag(ball, dt) {
    if (ball.height < 0.1) return; // NO air drag on ground - only friction
    
    const speed = ball.velocity.length();
    if (speed < 0.1) return;

    const dragMagnitude = 0.5 * BALL_DRAG_COEFFICIENT * BALL_AIR_DENSITY * BALL_CROSS_SECTION * speed * speed;
    const dragForce = ball.velocity.normalize().mul(-dragMagnitude);
    const acceleration = dragForce.div(BALL_MASS);
    ball.velocity.x += acceleration.x * dt;
    ball.velocity.y += acceleration.y * dt;
  }

  /**
   * Apply Magnus effect: spin causes lateral force
   * ONLY when ball is moving fast and in the air
   */
  _applyMagnusEffect(ball, dt) {
    if (ball.height < 0.1) return; // No Magnus on ground
    if (Math.abs(ball.spin) < 0.1) return;

    const speed = ball.velocity.length();
    if (speed < 2) return; // Need meaningful speed

    // Magnus force perpendicular to velocity
    const magnusForce = BALL_MAGNUS_COEFFICIENT * ball.spin * speed;
    const perpendicular = ball.velocity.perpendicular().normalize();
    const force = perpendicular.mul(magnusForce);
    const acceleration = force.div(BALL_MASS);
    ball.velocity.x += acceleration.x * dt;
    ball.velocity.y += acceleration.y * dt;
  }

  /**
   * Apply wind force to ball (ONLY when ball is in air)
   */
  _applyWind(ball, dt) {
    if (ball.height < 0.1) return; // No wind effect on ground ball
    if (this.windForce.lengthSq() < 0.01) return;

    // Wind has more effect on airborne ball
    const heightFactor = 1 + ball.height * 0.5;
    const windAccel = this.windForce.mul(heightFactor / BALL_MASS);
    ball.velocity.x += windAccel.x * dt;
    ball.velocity.y += windAccel.y * dt;
  }

  /**
   * Apply gravity to vertical component
   */
  _applyGravity(ball, dt) {
    if (ball.height > 0 || ball.verticalVelocity > 0) {
      ball.verticalVelocity -= GRAVITY * dt;
    }
  }

  /**
   * Apply ground friction when ball is on the ground
   */
  _applyGroundFriction(ball, dt) {
    if (ball.height > 0.05) return; // Ball is in the air

    const speed = ball.velocity.length();
    if (speed < 0.01) {
      ball.velocity.set(0, 0);
      return;
    }

    // Friction deceleration: a = -mu * g
    const frictionDecel = this.weatherFriction * GRAVITY;
    const newSpeed = Math.max(0, speed - frictionDecel * dt);
    
    if (newSpeed === 0) {
      ball.velocity.set(0, 0);
    } else {
      ball.velocity.normalizeMut().mulMut(newSpeed);
    }
  }

  /**
   * Check if ball is out of bounds
   */
  _checkBoundaries(ball) {
    ball.isOutOfBounds = false;
    ball.outType = null;

    if (ball.position.x < 0) {
      ball.isOutOfBounds = true;
      ball.outType = ball.position.y >= (PITCH_HEIGHT - GOAL_WIDTH) / 2 && 
                     ball.position.y <= (PITCH_HEIGHT + GOAL_WIDTH) / 2 ? 'goal_left' : 'goal_kick_or_corner_left';
      ball.position.x = 0;
      ball.velocity.x = 0;
    } else if (ball.position.x > PITCH_WIDTH) {
      ball.isOutOfBounds = true;
      ball.outType = ball.position.y >= (PITCH_HEIGHT - GOAL_WIDTH) / 2 && 
                     ball.position.y <= (PITCH_HEIGHT + GOAL_WIDTH) / 2 ? 'goal_right' : 'goal_kick_or_corner_right';
      ball.position.x = PITCH_WIDTH;
      ball.velocity.x = 0;
    }

    if (ball.position.y < 0) {
      ball.isOutOfBounds = true;
      ball.outType = 'throw_in_top';
      ball.position.y = 0;
      ball.velocity.y = 0;
    } else if (ball.position.y > PITCH_HEIGHT) {
      ball.isOutOfBounds = true;
      ball.outType = 'throw_in_bottom';
      ball.position.y = PITCH_HEIGHT;
      ball.velocity.y = 0;
    }
  }

  /**
   * Apply a kick to the ball
   * @param {Object} ball - Ball entity
   * @param {Vector2} direction - Normalized direction
   * @param {number} power - Power 0-1
   * @param {number} height - Loft 0-1 (0=ground, 1=high)
   * @param {number} spin - Spin amount (-1 to 1, negative=left curve, positive=right curve)
   * @param {number} playerTechnique - Player technique attribute 1-20
   */
  kick(ball, direction, power, height = 0, spin = 0, playerTechnique = 10) {
    // Base speed from power (max ~35 m/s for full power shot)
    const maxKickSpeed = 28 + (playerTechnique / 20) * 7; // 28-35 m/s
    const speed = power * maxKickSpeed;

    // Apply direction and speed
    ball.velocity.x = direction.x * speed;
    ball.velocity.y = direction.y * speed;

    // Vertical component for lofted balls
    ball.verticalVelocity = height * speed * 0.6;

    // Apply spin
    ball.spin = spin * 10; // Scale spin

    // Ball is no longer held
    ball.isHeld = false;
    ball.holder = null;
  }

  /**
   * Apply a pass (lower power, more accurate)
   */
  pass(ball, target, power, playerPassing, rng) {
    const direction = target.sub(ball.position).normalize();
    const distance = ball.position.distance(target);
    
    // Auto-calculate power to reach target (accounting for friction)
    // Ball needs enough speed to cover distance with friction slowing it
    const frictionDecel = this.weatherFriction * 9.81;
    // v² = 2*a*d → v = sqrt(2*a*d) + margin
    const neededSpeed = Math.sqrt(2 * frictionDecel * distance) * 1.3; // 30% margin
    const passSpeed = Math.min(BALL_MAX_SPEED * 0.6, Math.max(5, neededSpeed));
    
    // Add inaccuracy based on passing attribute
    const accuracy = playerPassing / 20; // 0.05 to 1.0
    const errorAngle = (1 - accuracy) * 0.08 * (rng.next() - 0.5); // Much less error
    const adjustedDir = direction.rotate(errorAngle);

    ball.velocity.x = adjustedDir.x * passSpeed;
    ball.velocity.y = adjustedDir.y * passSpeed;
    ball.height = 0;
    ball.verticalVelocity = 0;
    ball.spin = 0;
    ball.isHeld = false;
    ball.holder = null;
  }

  /**
   * Apply a through ball (leading pass)
   */
  throughBall(ball, targetPos, targetVelocity, power, playerVision, rng) {
    // Lead the target based on their velocity
    const leadTime = 0.8 + (playerVision / 20) * 0.4;
    const leadPos = targetPos.add(targetVelocity.mul(leadTime));
    const direction = leadPos.sub(ball.position).normalize();
    const distance = ball.position.distance(leadPos);
    
    const autoPower = Math.min(1, distance / 35) * (power || 0.7);
    
    // Through balls need more vision/technique
    const accuracy = playerVision / 20;
    const errorAngle = (1 - accuracy) * 0.2 * (rng.next() - 0.5);
    const adjustedDir = direction.rotate(errorAngle);

    this.kick(ball, adjustedDir, autoPower, 0.05, 0, playerVision);
  }

  /**
   * Apply a cross
   */
  cross(ball, targetArea, playerCrossing, rng) {
    const direction = targetArea.sub(ball.position).normalize();
    const distance = ball.position.distance(targetArea);
    
    const power = Math.min(1, distance / 45) * 0.75;
    const loft = 0.4 + rng.next() * 0.2; // Crosses are lofted
    const spin = (rng.next() - 0.5) * 0.5; // Some curve

    const accuracy = playerCrossing / 20;
    const errorAngle = (1 - accuracy) * 0.2 * (rng.next() - 0.5);
    const adjustedDir = direction.rotate(errorAngle);

    this.kick(ball, adjustedDir, power, loft, spin, playerCrossing);
  }

  /**
   * Apply a shot
   */
  shoot(ball, targetPos, power, playerShooting, playerTechnique, rng) {
    const direction = targetPos.sub(ball.position).normalize();
    
    // Shooting accuracy
    const accuracy = (playerShooting + playerTechnique) / 40;
    const errorAngle = (1 - accuracy) * 0.15 * (rng.next() - 0.5);
    const errorHeight = (1 - accuracy) * 0.2 * rng.next();
    const adjustedDir = direction.rotate(errorAngle);

    // Shot speed: 20-32 m/s based on power and technique
    const shotSpeed = 20 + power * 12;
    
    ball.velocity.x = adjustedDir.x * shotSpeed;
    ball.velocity.y = adjustedDir.y * shotSpeed;
    ball.verticalVelocity = errorHeight * shotSpeed * 0.3;
    ball.height = 0.2; // Slightly off ground
    ball.spin = (rng.next() - 0.5) * 5;
    ball.isHeld = false;
    ball.holder = null;
  }
}

// Need GOAL_WIDTH for boundary check
const GOAL_WIDTH = 7.32;
