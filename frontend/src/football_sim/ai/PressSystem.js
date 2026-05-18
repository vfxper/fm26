/**
 * PressSystem - Pressing triggers, press traps, counter-press
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT } from '../core/Constants.js';

export class PressSystem {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.counterPressTimer = 0;
    this.isCounterPressing = false;
  }

  /**
   * Determine pressing actions for a team
   * @param {Object} team - Defending team
   * @param {Object} opposingTeam - Team with ball
   * @param {Object} ball - Ball entity
   * @param {Object} rng
   * @param {boolean} isSecondHalf
   * @returns {Array} Array of {player, target, intensity} press instructions
   */
  calculatePressing(team, opposingTeam, ball, rng, isSecondHalf) {
    const instructions = [];
    const tactics = team.tactics;
    const pressIntensity = tactics.pressingIntensity;

    // Counter-press: immediate press after losing ball
    if (this.isCounterPressing) {
      return this._counterPress(team, opposingTeam, ball, rng);
    }

    // Normal pressing based on trigger zones
    const ballHolder = opposingTeam.getPlayerWithBall();
    if (!ballHolder) return instructions;

    const ownGoal = team.getOwnGoal(isSecondHalf);
    const distBallToGoal = ball.position.distance(ownGoal);

    // Press trigger: ball in our half or high press setting
    const shouldPress = pressIntensity > 0.6 || distBallToGoal < 45;

    if (!shouldPress) return instructions;

    // Find pressing players
    const pressers = this._selectPressers(team, ball, pressIntensity);

    for (const presser of pressers) {
      const target = this._calculatePressTarget(presser, ballHolder, ball, team, rng);
      instructions.push({
        player: presser,
        target,
        intensity: pressIntensity
      });
    }

    return instructions;
  }

  /**
   * Trigger counter-press (called when possession is lost)
   */
  triggerCounterPress(duration = 3.0) {
    this.isCounterPressing = true;
    this.counterPressTimer = duration;
  }

  /**
   * Update counter-press timer
   */
  update(dt) {
    if (this.isCounterPressing) {
      this.counterPressTimer -= dt;
      if (this.counterPressTimer <= 0) {
        this.isCounterPressing = false;
      }
    }
  }

  /**
   * Counter-press: all nearby players press immediately
   */
  _counterPress(team, opposingTeam, ball, rng) {
    const instructions = [];
    const ballHolder = opposingTeam.getPlayerWithBall();
    if (!ballHolder) return instructions;

    // All players within 15m press
    for (const player of team.players) {
      if (player.isGoalkeeper()) continue;
      const dist = player.position.distance(ball.position);
      
      if (dist < 15) {
        instructions.push({
          player,
          target: ball.position.clone(),
          intensity: 1.0
        });
      }
    }

    return instructions;
  }

  /**
   * Select which players should press
   */
  _selectPressers(team, ball, intensity) {
    const pressers = [];
    const maxPressers = Math.ceil(intensity * 3); // 1-3 pressers

    // Sort by distance to ball
    const candidates = team.players
      .filter(p => !p.isGoalkeeper() && p.stamina > 0.3)
      .map(p => ({ player: p, dist: p.position.distance(ball.position) }))
      .sort((a, b) => a.dist - b.dist);

    for (let i = 0; i < Math.min(maxPressers, candidates.length); i++) {
      if (candidates[i].dist < 20) {
        pressers.push(candidates[i].player);
      }
    }

    return pressers;
  }

  /**
   * Calculate where a pressing player should move
   */
  _calculatePressTarget(presser, ballHolder, ball, team, rng) {
    // Don't just run at the ball - cut off passing lanes
    const distToBall = presser.position.distance(ball.position);

    if (distToBall < 5) {
      // Close enough - go directly for ball
      return ball.position.clone();
    }

    // Approach from an angle to cut off the most likely pass
    const approachAngle = presser.position.angleTo(ball.position);
    const offset = (rng.next() - 0.5) * 0.3; // Slight angle variation
    
    const target = new Vector2(
      ball.position.x + Math.cos(approachAngle + Math.PI + offset) * 2,
      ball.position.y + Math.sin(approachAngle + Math.PI + offset) * 2
    );

    return target;
  }

  /**
   * Check if a press trap should be triggered
   * (Multiple players converge on ball carrier in a specific zone)
   */
  checkPressTrap(team, opposingTeam, ball, rng) {
    const ballHolder = opposingTeam.getPlayerWithBall();
    if (!ballHolder) return false;

    // Press trap near touchlines
    const nearTouchline = ball.position.y < 10 || ball.position.y > PITCH_HEIGHT - 10;
    
    if (nearTouchline) {
      const nearbyTeammates = team.players.filter(
        p => p.position.distance(ball.position) < 10
      );
      return nearbyTeammates.length >= 2;
    }

    return false;
  }
}
