/**
 * Goalkeeper - GK specialization: diving, rushing, positioning
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT, GOAL_WIDTH, GOAL_Y_MIN, GOAL_Y_MAX } from '../core/Constants.js';

export class Goalkeeper {
  constructor(eventBus) {
    this.eventBus = eventBus;
  }

  /**
   * Update goalkeeper positioning
   * @param {Object} gk - Goalkeeper player entity
   * @param {Object} ball - Ball entity
   * @param {string} side - 'home' or 'away'
   * @param {boolean} isSecondHalf
   */
  updatePositioning(gk, ball, side, isSecondHalf) {
    if (!gk || !gk.isActive) return;

    const goalX = this._getGoalX(side, isSecondHalf);
    const goalCenter = new Vector2(goalX, PITCH_HEIGHT / 2);

    // Position between ball and center of goal
    const ballToGoal = goalCenter.sub(ball.position);
    const distBallToGoal = ballToGoal.length();

    // GK stays on goal line but shifts to cover angle
    let gkX, gkY;

    if (distBallToGoal < 30) {
      // Ball is close - come off line slightly
      const advanceDist = Math.max(1, Math.min(8, (30 - distBallToGoal) * 0.3));
      const dirToBall = ball.position.sub(goalCenter).normalize();
      gkX = goalX + dirToBall.x * advanceDist;
      gkY = PITCH_HEIGHT / 2 + dirToBall.y * advanceDist;
    } else {
      // Ball is far - stay near goal line, cover angle
      gkX = goalX + (side === 'home' ? 2 : -2) * (isSecondHalf ? -1 : 1);
      // Shift laterally based on ball position
      const lateralShift = ((ball.position.y - PITCH_HEIGHT / 2) / PITCH_HEIGHT) * 4;
      gkY = PITCH_HEIGHT / 2 + lateralShift;
    }

    // Clamp GK position
    gkY = Math.max(GOAL_Y_MIN - 2, Math.min(GOAL_Y_MAX + 2, gkY));

    gk.moveTo(new Vector2(gkX, gkY), 'jog');
  }

  /**
   * Attempt to save a shot
   * @param {Object} gk - Goalkeeper entity
   * @param {Object} ball - Ball entity
   * @param {Object} rng - Random number generator
   * @returns {Object} {saved, direction}
   */
  attemptSave(gk, ball, rng) {
    const attrs = gk.attributes;
    const reflexes = attrs.reflexes || 10;
    const handling = attrs.handling || 10;
    const positioning = attrs.positioning || 10;

    // Distance from GK to ball trajectory
    const distToBall = gk.position.distance(ball.position);
    
    // Base save probability
    let saveChance = 0.2;

    // Reflexes help with close-range shots
    saveChance += (reflexes / 20) * 0.3;

    // Positioning helps if GK is well-placed
    if (distToBall < 3) {
      saveChance += (positioning / 20) * 0.2;
    }

    // Harder to save if ball is far from GK
    if (distToBall > 4) {
      saveChance -= (distToBall - 4) * 0.05;
    }

    // Ball speed makes it harder
    const ballSpeed = ball.velocity.length();
    if (ballSpeed > 20) {
      saveChance -= (ballSpeed - 20) * 0.015;
    }

    // Ball height factor
    if (ball.height > 2) {
      saveChance -= 0.1; // High shots are harder
    }

    saveChance = Math.max(0.05, Math.min(0.9, saveChance));

    const saved = rng.next() < saveChance;

    // Determine dive direction
    const ballDir = ball.position.sub(gk.position).normalize();
    const diveDirection = ballDir;

    if (saved) {
      // Determine if caught or parried
      const catchChance = (handling / 20) * 0.6;
      const caught = rng.next() < catchChance;

      return {
        saved: true,
        caught,
        diveDirection,
        deflectionAngle: caught ? 0 : (rng.next() - 0.5) * Math.PI * 0.5
      };
    }

    return { saved: false, diveDirection };
  }

  /**
   * Decide whether to rush out for 1-on-1
   * @param {Object} gk - Goalkeeper entity
   * @param {Object} attacker - Attacking player
   * @param {Object} ball - Ball entity
   * @param {Object} rng
   * @returns {boolean} Should rush
   */
  shouldRush(gk, attacker, ball, rng) {
    const oneOnOnes = gk.attributes.oneOnOnes || 10;
    const distToAttacker = gk.position.distance(attacker.position);

    // Rush if attacker is close and GK has good 1v1 ability
    if (distToAttacker < 15 && distToAttacker > 5) {
      const rushChance = (oneOnOnes / 20) * 0.6;
      return rng.next() < rushChance;
    }
    return false;
  }

  /**
   * Handle distribution (kick/throw after save)
   * @param {Object} gk - Goalkeeper entity
   * @param {Object} ball - Ball entity
   * @param {Array} teammates - Teammate players
   * @param {Object} rng
   * @returns {Object} {target, type} - Where to distribute and how
   */
  distribute(gk, ball, teammates, rng) {
    const kicking = gk.attributes.passing || 10;
    
    // Find best distribution target
    const outfieldTeammates = teammates.filter(p => !p.isGoalkeeper());
    
    // Prefer short distribution to defenders if they're open
    const defenders = outfieldTeammates.filter(p => p.isDefender());
    const midfielders = outfieldTeammates.filter(p => p.isMidfielder());

    let target;
    let type;

    if (defenders.length > 0 && rng.next() < 0.6) {
      target = rng.pick(defenders);
      type = 'short';
    } else if (midfielders.length > 0 && rng.next() < 0.5) {
      target = rng.pick(midfielders);
      type = 'throw';
    } else {
      target = rng.pick(outfieldTeammates);
      type = kicking > 12 ? 'long_kick' : 'throw';
    }

    return { target, type };
  }

  /**
   * Get goal x position for a team
   */
  _getGoalX(side, isSecondHalf) {
    if (side === 'home') {
      return isSecondHalf ? PITCH_WIDTH : 0;
    } else {
      return isSecondHalf ? 0 : PITCH_WIDTH;
    }
  }
}
