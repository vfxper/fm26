/**
 * CollisionSystem - Player-player and player-ball collision detection & response
 */
import { Vector2 } from '../core/Vector2.js';
import { PLAYER_RADIUS, PLAYER_MASS, BALL_RADIUS, PLAYER_CONTROL_RADIUS } from '../core/Constants.js';

export class CollisionSystem {
  constructor(eventBus) {
    this.eventBus = eventBus;
  }

  /**
   * Check and resolve all collisions
   * @param {Array} players - All player entities
   * @param {Object} ball - Ball entity
   * @param {number} dt - Delta time
   */
  update(players, ball, dt) {
    // Player-player collisions
    for (let i = 0; i < players.length; i++) {
      for (let j = i + 1; j < players.length; j++) {
        this._resolvePlayerCollision(players[i], players[j]);
      }
    }

    // Player-ball collisions (for ball control)
    for (const player of players) {
      this._checkPlayerBallInteraction(player, ball);
    }
  }

  /**
   * Resolve collision between two players
   */
  _resolvePlayerCollision(p1, p2) {
    const dx = p2.position.x - p1.position.x;
    const dy = p2.position.y - p1.position.y;
    const distSq = dx * dx + dy * dy;
    const minDist = PLAYER_RADIUS * 2;

    if (distSq >= minDist * minDist) return; // No collision
    if (distSq < 0.001) return; // Overlapping exactly, skip

    const dist = Math.sqrt(distSq);
    const overlap = minDist - dist;

    // Normal vector from p1 to p2
    const nx = dx / dist;
    const ny = dy / dist;

    // Separate players (push apart equally)
    const separation = overlap * 0.5;
    p1.position.x -= nx * separation;
    p1.position.y -= ny * separation;
    p2.position.x += nx * separation;
    p2.position.y += ny * separation;

    // Elastic collision response
    const relVelX = p2.velocity.x - p1.velocity.x;
    const relVelY = p2.velocity.y - p1.velocity.y;
    const relVelDotNormal = relVelX * nx + relVelY * ny;

    // Only resolve if players are moving towards each other
    if (relVelDotNormal > 0) return;

    // Impulse (equal mass simplification)
    const impulse = relVelDotNormal * 0.5;
    p1.velocity.x += impulse * nx;
    p1.velocity.y += impulse * ny;
    p2.velocity.x -= impulse * nx;
    p2.velocity.y -= impulse * ny;

    // Mark collision for tackle/foul detection
    p1.lastCollision = { player: p2, time: Date.now() };
    p2.lastCollision = { player: p1, time: Date.now() };
  }

  /**
   * Check if player is close enough to control/interact with ball
   */
  _checkPlayerBallInteraction(player, ball) {
    if (ball.isHeld && ball.holder !== player) return;

    const dist = player.position.distance(ball.position);
    
    // Ball control range
    if (dist < PLAYER_CONTROL_RADIUS && ball.height < 1.5) {
      player.canReachBall = true;
      player.distToBall = dist;
    } else {
      player.canReachBall = false;
      player.distToBall = dist;
    }
  }

  /**
   * Check if a tackle is successful
   * @param {Object} tackler - Player making tackle
   * @param {Object} ballHolder - Player with ball
   * @param {Object} rng - Random number generator
   * @returns {Object} Result: {success, foul, severity}
   */
  resolveTackle(tackler, ballHolder, rng) {
    const tackling = tackler.attributes.tackling || 10;
    const dribbling = ballHolder.attributes.dribbling || 10;
    const strength = tackler.attributes.strength || 10;
    const agility = ballHolder.attributes.agility || 10;

    // Base success chance
    let successChance = 0.3 + (tackling / 20) * 0.4 - (dribbling / 20) * 0.2;
    
    // Approach angle matters - tackles from behind are harder and more likely fouls
    const approachAngle = this._getApproachAngle(tackler, ballHolder);
    const fromBehind = Math.abs(approachAngle) > Math.PI * 0.6;
    
    if (fromBehind) {
      successChance *= 0.6;
    }

    // Foul probability
    let foulChance = 0.15 + (1 - tackling / 20) * 0.25;
    if (fromBehind) foulChance += 0.3;

    const success = rng.next() < successChance;
    const foul = !success && rng.next() < foulChance;

    let severity = 0; // 0=nothing, 1=yellow worthy, 2=red worthy
    if (foul) {
      severity = fromBehind ? (rng.next() < 0.3 ? 2 : 1) : (rng.next() < 0.1 ? 1 : 0);
    }

    return { success, foul, severity, fromBehind };
  }

  /**
   * Get approach angle of tackler relative to ball holder's facing
   */
  _getApproachAngle(tackler, ballHolder) {
    const approachDir = Math.atan2(
      ballHolder.position.y - tackler.position.y,
      ballHolder.position.x - tackler.position.x
    );
    let angle = approachDir - ballHolder.facing;
    while (angle > Math.PI) angle -= Math.PI * 2;
    while (angle < -Math.PI) angle += Math.PI * 2;
    return angle;
  }

  /**
   * Check if a header contest is won
   */
  resolveAerialDuel(player1, player2, ball, rng) {
    const jump1 = (player1.attributes.jumping || 10) + (player1.attributes.strength || 10) * 0.3;
    const jump2 = (player2.attributes.jumping || 10) + (player2.attributes.strength || 10) * 0.3;
    
    const total = jump1 + jump2;
    const p1Chance = jump1 / total;
    
    return rng.next() < p1Chance ? player1 : player2;
  }
}
