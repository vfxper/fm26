/**
 * BallContact - Handles ball-player interactions: first touch, dribbling, tackles
 * Implements the "ball always belongs to someone" principle.
 */
import { Vector2 } from '../core/Vector2.js';
import {
  PLAYER_KICK_RANGE, PLAYER_CONTROL_RADIUS, PLAYER_TACKLE_RANGE,
  BALL_BOUNCE_RESTITUTION, ATTR_MAX
} from '../core/Constants.js';

export class BallContact {
  constructor(eventBus) {
    this.eventBus = eventBus;
  }

  /**
   * Process first touch (receiving a pass)
   * Quality depends on First Touch attribute, ball speed, body orientation
   * @param {Object} player - Player entity
   * @param {Object} ball - Ball entity
   * @param {Object} rng - Random number generator
   * @returns {Object} Result { success, deflectionDist, controlTime }
   */
  processFirstTouch(player, ball, rng) {
    const firstTouch = player.getEffectiveAttr('technique');
    const ballSpeed = ball.velocity.length();
    
    // Orientation penalty: if player isn't facing the ball, harder to control
    const ballDir = ball.position.sub(player.position).normalize();
    const facingDir = Vector2.fromAngle(player.facing);
    const facingDot = facingDir.dot(ballDir);
    const orientationPenalty = Math.max(0, (1 - facingDot) * 0.3); // 0-0.3 penalty
    
    // Speed penalty: faster balls are harder to control
    const speedPenalty = Math.min(0.4, ballSpeed / 50); // 0-0.4 penalty
    
    // Effective control quality (0-1)
    const quality = (firstTouch / ATTR_MAX) * (1 - orientationPenalty - speedPenalty);
    
    // Calculate deflection distance based on quality
    let deflectionDist;
    let controlTime;
    
    if (quality > 0.85) {
      // Excellent touch: ball stops 0.2-0.4m away in desired direction
      deflectionDist = rng.range(0.2, 0.4);
      controlTime = 0.1;
    } else if (quality > 0.65) {
      // Good touch: ball goes 0.5-1.0m
      deflectionDist = rng.range(0.5, 1.0);
      controlTime = 0.2;
    } else if (quality > 0.4) {
      // Mediocre touch: ball bounces 1.0-2.0m, might lose briefly
      deflectionDist = rng.range(1.0, 2.0);
      controlTime = 0.5;
    } else {
      // Poor touch: ball bounces 2-4m, near-loss
      deflectionDist = rng.range(2.0, 4.0);
      controlTime = 1.0;
    }

    // Apply the touch: reduce ball speed and redirect
    const controlDir = facingDir; // Player tries to push ball in facing direction
    const retainedSpeed = ballSpeed * (1 - quality) * 0.3;
    
    ball.velocity.x = controlDir.x * retainedSpeed;
    ball.velocity.y = controlDir.y * retainedSpeed;
    ball.height = 0;
    ball.verticalVelocity = 0;
    ball.spin = 0;

    return {
      success: quality > 0.3,
      deflectionDist,
      controlTime,
      quality,
    };
  }

  /**
   * Process dribble touch - player pushes ball forward while running
   * @param {Object} player - Player entity
   * @param {Object} ball - Ball entity
   * @param {Object} rng - Random number generator
   */
  processDribbleTouch(player, ball, rng) {
    const dribbling = player.getEffectiveAttr('dribbling');
    const speed = player.currentSpeed;
    const maxSpeed = 10; // approximate max
    
    // Distance ball is pushed ahead depends on speed
    // Slow dribble: 0.3-0.6m, Sprint: 3-5m ahead
    const speedRatio = speed / maxSpeed;
    const baseDist = 0.3 + speedRatio * 1.2;
    
    // Deviation from intended direction (lower dribbling = more deviation)
    const maxDeviation = (1 - dribbling / ATTR_MAX) * 0.35; // 0-20° max
    const deviation = rng.range(-maxDeviation, maxDeviation);
    
    // Push ball in player's facing direction + deviation
    const pushDir = Vector2.fromAngle(player.facing + deviation);
    const pushSpeed = speed * 1.05; // Ball slightly faster than player
    
    ball.velocity.x = pushDir.x * pushSpeed;
    ball.velocity.y = pushDir.y * pushSpeed;
    ball.height = 0;
    ball.verticalVelocity = 0;
    
    // Position ball ahead of player
    ball.position.x = player.position.x + pushDir.x * baseDist;
    ball.position.y = player.position.y + pushDir.y * baseDist;
    ball.isHeld = false; // Ball is rolling, not glued
    ball.holder = null;
  }

  /**
   * Process tackle attempt
   * @param {Object} tackler - Player attempting tackle
   * @param {Object} ballHolder - Player with the ball
   * @param {Object} ball - Ball entity
   * @param {Object} rng - Random number generator
   * @returns {Object} { success, foul, ballWon, deflection }
   */
  processTackle(tackler, ballHolder, ball, rng) {
    const tackling = tackler.getEffectiveAttr('tackling');
    const strength = tackler.getEffectiveAttr('strength');
    const dribbling = ballHolder.getEffectiveAttr('dribbling');
    const agility = ballHolder.getEffectiveAttr('agility');
    const balance = ballHolder.getEffectiveAttr('strength');
    
    // Distance factor: closer = better chance
    const dist = tackler.position.distance(ballHolder.position);
    const distFactor = Math.max(0, 1 - (dist / PLAYER_TACKLE_RANGE));
    
    // Angle factor: tackling from behind is harder and more likely foul
    const approachDir = ballHolder.position.sub(tackler.position).normalize();
    const holderFacing = Vector2.fromAngle(ballHolder.facing);
    const angleDot = approachDir.dot(holderFacing);
    const fromBehind = angleDot > 0.5; // Approaching from behind
    
    // Success probability
    const attackPower = (tackling * 0.6 + strength * 0.4) / ATTR_MAX;
    const defendPower = (dribbling * 0.4 + agility * 0.3 + balance * 0.3) / ATTR_MAX;
    let successChance = (attackPower - defendPower * 0.7) * distFactor + 0.3;
    
    if (fromBehind) successChance *= 0.6; // Harder from behind
    successChance = Math.max(0.05, Math.min(0.95, successChance));
    
    // Foul probability
    let foulChance = 0.15 + (1 - tackling / ATTR_MAX) * 0.25;
    if (fromBehind) foulChance += 0.25;
    if (dist > PLAYER_TACKLE_RANGE * 0.8) foulChance += 0.15;
    foulChance = Math.min(0.8, foulChance);
    
    const success = rng.chance(successChance);
    const foul = !success && rng.chance(foulChance);
    
    let deflection = null;
    if (success) {
      // Ball deflects away from holder
      const deflectDir = ball.position.sub(tackler.position).normalize();
      const deflectSpeed = rng.range(3, 8);
      deflection = deflectDir.mul(deflectSpeed);
      
      ball.velocity.x = deflection.x;
      ball.velocity.y = deflection.y;
      ball.isHeld = false;
      ball.holder = null;
      ball.lastTouchedBy = tackler;
      ball.lastTouchedTeam = tackler.teamSide;
    }
    
    return {
      success,
      foul,
      fromBehind,
      ballWon: success,
      deflection,
      severity: foul ? (fromBehind ? 'serious' : 'normal') : null,
    };
  }

  /**
   * Process slide tackle
   * More range but more risk of foul, player goes to ground
   */
  processSlideTackle(tackler, ballHolder, ball, rng) {
    const result = this.processTackle(tackler, ballHolder, ball, rng);
    
    // Slide tackle has more range but higher foul chance
    result.foul = result.foul || rng.chance(0.2);
    result.tacklerDown = true; // Player is on ground after slide
    result.recoveryTime = rng.range(0.5, 1.0); // Time to get up
    
    return result;
  }

  /**
   * Determine who wins a 50/50 ball contest
   * @param {Object} playerA - First player
   * @param {Object} playerB - Second player
   * @param {Object} ball - Ball entity
   * @param {Object} rng - Random number generator
   * @returns {Object} { winner, loserFalls }
   */
  process5050(playerA, playerB, ball, rng) {
    // Time to reach ball
    const distA = playerA.position.distance(ball.position);
    const distB = playerB.position.distance(ball.position);
    const speedA = Math.max(1, playerA.currentSpeed);
    const speedB = Math.max(1, playerB.currentSpeed);
    
    const timeA = distA / (speedA * (playerA.getEffectiveAttr('acceleration') / ATTR_MAX));
    const timeB = distB / (speedB * (playerB.getEffectiveAttr('acceleration') / ATTR_MAX));
    
    // If one clearly arrives first (>0.05s difference), they win
    if (Math.abs(timeA - timeB) > 0.05) {
      const winner = timeA < timeB ? playerA : playerB;
      return { winner, loserFalls: false };
    }
    
    // Simultaneous arrival: strength + balance contest
    const powerA = playerA.getEffectiveAttr('strength') * 0.6 + 
                   playerA.getEffectiveAttr('agility') * 0.4 +
                   rng.range(-2, 2);
    const powerB = playerB.getEffectiveAttr('strength') * 0.6 + 
                   playerB.getEffectiveAttr('agility') * 0.4 +
                   rng.range(-2, 2);
    
    const winner = powerA >= powerB ? playerA : playerB;
    const loser = winner === playerA ? playerB : playerA;
    
    // Loser might fall if big strength difference
    const strengthDiff = Math.abs(powerA - powerB);
    const loserFalls = strengthDiff > 5 && rng.chance(0.4);
    
    return { winner, loser, loserFalls };
  }

  /**
   * Check if player can reach the ball
   */
  canReachBall(player, ball) {
    const dist = player.position.distance(ball.position);
    return dist <= PLAYER_CONTROL_RADIUS;
  }

  /**
   * Check if player can tackle
   */
  canTackle(tackler, target) {
    const dist = tackler.position.distance(target.position);
    return dist <= PLAYER_TACKLE_RANGE;
  }
}
