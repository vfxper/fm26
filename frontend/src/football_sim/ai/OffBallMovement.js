/**
 * OffBallMovement - Intelligent off-ball runs, support play, defensive positioning
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT } from '../core/Constants.js';

export class OffBallMovement {
  constructor(eventBus) {
    this.eventBus = eventBus;
  }

  /**
   * Calculate off-ball movement for a player
   * @param {Object} player - Player entity
   * @param {Object} team - Player's team
   * @param {Object} opposingTeam - Opposing team
   * @param {Object} ball - Ball entity
   * @param {Object} rng - Random number generator
   * @param {boolean} isSecondHalf
   * @returns {Vector2|null} Target position or null
   */
  calculateMovement(player, team, opposingTeam, ball, rng, isSecondHalf) {
    if (player.hasBall || player.isGoalkeeper()) return null;

    if (team.hasPossession) {
      return this._attackingMovement(player, team, opposingTeam, ball, rng, isSecondHalf);
    } else {
      return this._defensiveMovement(player, team, opposingTeam, ball, rng, isSecondHalf);
    }
  }

  /**
   * Attacking off-ball movement
   */
  _attackingMovement(player, team, opposingTeam, ball, rng, isSecondHalf) {
    const targetGoal = team.getTargetGoal(isSecondHalf);
    const attackDir = team.getAttackingDirection(isSecondHalf);
    const ballHolder = team.getPlayerWithBall();

    if (!ballHolder) {
      return this._moveToHomePosition(player);
    }

    // Different movement based on position
    if (player.isAttacker()) {
      return this._attackerRun(player, team, opposingTeam, ball, ballHolder, targetGoal, attackDir, rng);
    } else if (player.isMidfielder()) {
      return this._midfielderSupport(player, team, opposingTeam, ball, ballHolder, targetGoal, attackDir, rng);
    } else {
      return this._defenderPushUp(player, team, ball, attackDir, rng);
    }
  }

  /**
   * Attacker runs: diagonal, through-the-middle, pulling wide
   */
  _attackerRun(player, team, opposingTeam, ball, ballHolder, targetGoal, attackDir, rng) {
    const distToGoal = player.position.distance(targetGoal);
    const workRate = player.attributes.workRate || 10;
    const offTheBall = player.attributes.anticipation || 10;

    // Decide run type based on attributes and situation
    const runDecision = rng.next();

    if (runDecision < 0.3 && distToGoal > 20) {
      // Diagonal run behind defense
      return this._diagonalRun(player, targetGoal, attackDir, opposingTeam, rng, isSecondHalf);
    } else if (runDecision < 0.5 && distToGoal > 15) {
      // Central run
      return this._centralRun(player, targetGoal, attackDir, rng);
    } else if (runDecision < 0.7) {
      // Pull wide to create space
      return this._pullWide(player, targetGoal, attackDir, rng);
    } else {
      // Drop deep to receive
      return this._dropDeep(player, ballHolder, attackDir, rng);
    }
  }

  /**
   * Diagonal run behind the defensive line
   */
  _diagonalRun(player, targetGoal, attackDir, opposingTeam, rng) {
    const lastDefenderX = this._getLastDefenderX(opposingTeam, attackDir);
    
    // Run diagonally past the last defender
    const runDepth = 8 + rng.next() * 10;
    const lateralShift = (rng.next() - 0.5) * 15;

    const target = new Vector2(
      lastDefenderX + attackDir * runDepth,
      player.position.y + lateralShift
    );

    target.x = Math.max(3, Math.min(PITCH_WIDTH - 3, target.x));
    target.y = Math.max(5, Math.min(PITCH_HEIGHT - 5, target.y));

    return target;
  }

  /**
   * Central run towards goal
   */
  _centralRun(player, targetGoal, attackDir, rng) {
    const target = new Vector2(
      player.position.x + attackDir * (10 + rng.next() * 8),
      PITCH_HEIGHT / 2 + (rng.next() - 0.5) * 10
    );

    target.x = Math.max(3, Math.min(PITCH_WIDTH - 3, target.x));
    target.y = Math.max(5, Math.min(PITCH_HEIGHT - 5, target.y));

    return target;
  }

  /**
   * Pull wide to stretch defense
   */
  _pullWide(player, targetGoal, attackDir, rng) {
    const isLeftSide = player.position.y < PITCH_HEIGHT / 2;
    const wideY = isLeftSide ? 5 + rng.next() * 8 : PITCH_HEIGHT - 5 - rng.next() * 8;

    const target = new Vector2(
      player.position.x + attackDir * (5 + rng.next() * 10),
      wideY
    );

    target.x = Math.max(3, Math.min(PITCH_WIDTH - 3, target.x));

    return target;
  }

  /**
   * Drop deep to receive ball
   */
  _dropDeep(player, ballHolder, attackDir, rng) {
    if (!ballHolder) return player.homePosition;

    const target = new Vector2(
      ballHolder.position.x - attackDir * (5 + rng.next() * 5),
      ballHolder.position.y + (rng.next() - 0.5) * 15
    );

    target.x = Math.max(3, Math.min(PITCH_WIDTH - 3, target.x));
    target.y = Math.max(5, Math.min(PITCH_HEIGHT - 5, target.y));

    return target;
  }

  /**
   * Midfielder support play
   */
  _midfielderSupport(player, team, opposingTeam, ball, ballHolder, targetGoal, attackDir, rng) {
    const distToBallHolder = player.position.distance(ballHolder.position);

    if (distToBallHolder < 10) {
      // Already close - create angle
      const angle = player.position.angleTo(ballHolder.position) + (rng.next() - 0.5) * Math.PI * 0.5;
      const dist = 8 + rng.next() * 5;
      const target = new Vector2(
        ballHolder.position.x + Math.cos(angle) * dist,
        ballHolder.position.y + Math.sin(angle) * dist
      );
      target.x = Math.max(3, Math.min(PITCH_WIDTH - 3, target.x));
      target.y = Math.max(3, Math.min(PITCH_HEIGHT - 3, target.y));
      return target;
    }

    // Move towards ball holder to offer support
    const supportPos = ballHolder.position.add(
      new Vector2(-attackDir * 8, (rng.next() - 0.5) * 12)
    );
    supportPos.x = Math.max(3, Math.min(PITCH_WIDTH - 3, supportPos.x));
    supportPos.y = Math.max(3, Math.min(PITCH_HEIGHT - 3, supportPos.y));

    return supportPos;
  }

  /**
   * Defender push up when team has possession
   */
  _defenderPushUp(player, team, ball, attackDir, rng) {
    // Push up from home position
    const pushDist = team.tactics.lineHeight * 10;
    const target = new Vector2(
      player.homePosition.x + attackDir * pushDist,
      player.homePosition.y + (rng.next() - 0.5) * 3
    );

    target.x = Math.max(3, Math.min(PITCH_WIDTH - 3, target.x));
    target.y = Math.max(3, Math.min(PITCH_HEIGHT - 3, target.y));

    return target;
  }

  /**
   * Defensive off-ball movement
   */
  _defensiveMovement(player, team, opposingTeam, ball, rng, isSecondHalf) {
    const ownGoal = team.getOwnGoal(isSecondHalf);
    const distToBall = player.position.distance(ball.position);

    if (player.isDefender()) {
      return this._defensivePositioning(player, team, opposingTeam, ball, ownGoal, rng);
    } else if (player.isMidfielder()) {
      return this._midfielderDefending(player, team, ball, ownGoal, rng);
    } else {
      // Attackers stay higher but track back somewhat
      return this._attackerDefending(player, team, ball, ownGoal, rng);
    }
  }

  /**
   * Defensive positioning - mark opponents, cover space
   */
  _defensivePositioning(player, team, opposingTeam, ball, ownGoal, rng) {
    const marking = player.attributes.marking || 10;
    const positioning = player.attributes.positioning || 10;

    // Find nearest opponent to mark
    const nearestAttacker = this._findNearestOpponent(player, opposingTeam, ball);

    if (nearestAttacker && marking > 10) {
      // Man-mark: position between attacker and goal
      const markPos = nearestAttacker.position.lerp(ownGoal, 0.25);
      return markPos;
    }

    // Zonal: position between ball and goal
    const zonalPos = ball.position.lerp(ownGoal, 0.4);
    // Shift to cover own zone
    const zoneOffset = (player.homePosition.y - PITCH_HEIGHT / 2) * 0.5;
    zonalPos.y += zoneOffset;
    zonalPos.y = Math.max(5, Math.min(PITCH_HEIGHT - 5, zonalPos.y));

    return zonalPos;
  }

  /**
   * Midfielder defensive positioning
   */
  _midfielderDefending(player, team, ball, ownGoal, rng) {
    // Position between ball and goal, maintaining shape
    const shapePos = player.homePosition.lerp(ownGoal, 0.2);
    const ballInfluence = ball.position.sub(shapePos).mul(0.15);
    const target = shapePos.add(ballInfluence);

    target.x = Math.max(3, Math.min(PITCH_WIDTH - 3, target.x));
    target.y = Math.max(3, Math.min(PITCH_HEIGHT - 3, target.y));

    return target;
  }

  /**
   * Attacker defensive contribution
   */
  _attackerDefending(player, team, ball, ownGoal, rng) {
    const workRate = player.attributes.workRate || 10;

    if (workRate > 12) {
      // High work rate - track back
      const trackPos = player.homePosition.lerp(ball.position, 0.3);
      return trackPos;
    }

    // Low work rate - stay high
    return player.homePosition;
  }

  /**
   * Find nearest opponent (for marking)
   */
  _findNearestOpponent(player, opposingTeam, ball) {
    let nearest = null;
    let minDist = 20; // Only mark if within 20m

    for (const opp of opposingTeam.players) {
      if (opp.isGoalkeeper()) continue;
      const dist = player.position.distance(opp.position);
      if (dist < minDist) {
        minDist = dist;
        nearest = opp;
      }
    }

    return nearest;
  }

  /**
   * Get last defender x position
   */
  _getLastDefenderX(team, attackDir) {
    const defenders = team.getDefenders();
    if (defenders.length === 0) return PITCH_WIDTH / 2;

    if (attackDir > 0) {
      return Math.max(...defenders.map(d => d.position.x));
    } else {
      return Math.min(...defenders.map(d => d.position.x));
    }
  }

  /**
   * Move to home position
   */
  _moveToHomePosition(player) {
    return player.homePosition.clone();
  }
}
