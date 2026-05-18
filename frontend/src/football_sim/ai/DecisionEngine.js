/**
 * DecisionEngine - 4-layer AI: Strategic → Tactical → Technical → Physical
 * Makes decisions every 0.5 seconds for each player
 */
import { Vector2 } from '../core/Vector2.js';
import { AI_DECISION_INTERVAL, PITCH_WIDTH, PITCH_HEIGHT, PLAYER_KICK_RANGE } from '../core/Constants.js';

export class DecisionEngine {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.decisionTimer = 0;
  }

  /**
   * Update AI decisions for all players on a team
   * @param {Object} team - Team entity
   * @param {Object} opposingTeam - Opposing team entity
   * @param {Object} ball - Ball entity
   * @param {Object} matchState - Current match state
   * @param {number} dt - Delta time
   * @param {Object} rng - Seeded random
   */
  update(team, opposingTeam, ball, matchState, dt, rng) {
    this.decisionTimer += dt;
    if (this.decisionTimer < AI_DECISION_INTERVAL) return;
    this.decisionTimer = 0;

    const context = {
      team,
      opposingTeam,
      ball,
      matchState,
      rng,
      isSecondHalf: matchState.isSecondHalf || false,
    };

    // Strategic layer - team-wide decisions
    const strategy = this._strategicLayer(context);

    for (const player of team.players) {
      if (!player.isActive || player.isGoalkeeper()) continue;

      // Tactical layer - zone/role decisions
      const tactical = this._tacticalLayer(player, context, strategy);

      // Technical layer - specific action
      const technical = this._technicalLayer(player, context, tactical);

      // Physical layer - movement mode
      const physical = this._physicalLayer(player, context, technical);

      // Apply decision
      player.aiState.decision = technical;
      player.movementMode = physical.mode;

      if (technical.target) {
        player.moveTo(technical.target, physical.mode);
      }
    }
  }

  /**
   * Strategic Layer - Team-wide decisions based on score, time, momentum
   */
  _strategicLayer(context) {
    const { team, opposingTeam, matchState, ball } = context;
    const scoreDiff = team.score - opposingTeam.score;
    const minute = matchState.minute || 0;

    let mentality = 'balanced';
    let pressIntensity = team.tactics.pressingIntensity;
    let lineHeight = team.tactics.lineHeight;

    // Adjust based on score and time
    if (scoreDiff < 0 && minute > 70) {
      mentality = 'ultra-attacking';
      pressIntensity = Math.min(1, pressIntensity + 0.3);
      lineHeight = Math.min(1, lineHeight + 0.2);
    } else if (scoreDiff < 0 && minute > 55) {
      mentality = 'attacking';
      pressIntensity = Math.min(1, pressIntensity + 0.15);
    } else if (scoreDiff > 0 && minute > 75) {
      mentality = 'defensive';
      pressIntensity = Math.max(0, pressIntensity - 0.2);
      lineHeight = Math.max(0, lineHeight - 0.2);
    } else if (scoreDiff > 1) {
      mentality = 'cautious';
      pressIntensity = Math.max(0, pressIntensity - 0.1);
    }

    // Possession state
    const hasPossession = team.hasPossession;
    const phase = hasPossession ? 'attacking' : 'defending';

    return { mentality, pressIntensity, lineHeight, phase, hasPossession };
  }

  /**
   * Tactical Layer - Individual role and zone decisions
   */
  _tacticalLayer(player, context, strategy) {
    const { team, opposingTeam, ball } = context;
    const hasBall = player.hasBall;
    const teamHasBall = team.hasPossession;

    if (hasBall) {
      return this._tacticalWithBall(player, context, strategy);
    } else if (teamHasBall) {
      return this._tacticalOffBallAttacking(player, context, strategy);
    } else {
      return this._tacticalDefending(player, context, strategy);
    }
  }

  /**
   * Tactical decisions when player has the ball
   */
  _tacticalWithBall(player, context, strategy) {
    const { team, opposingTeam, ball, rng, isSecondHalf } = context;
    const targetGoal = team.getTargetGoal(isSecondHalf);
    const distToGoal = player.position.distance(targetGoal);

    // Find nearby opponents
    const nearbyOpponents = opposingTeam.players.filter(
      p => p.position.distance(player.position) < 8
    );
    const underPressure = nearbyOpponents.length >= 2 || 
      (nearbyOpponents.length >= 1 && nearbyOpponents[0].position.distance(player.position) < 3);

    // Shooting zone
    if (distToGoal < 25 && !underPressure) {
      return { action: 'consider_shot', priority: 'high' };
    }

    // Final third - look for through ball or cross
    if (distToGoal < 35) {
      if (player.positionRole === 'RW' || player.positionRole === 'LW') {
        return { action: 'consider_cross', priority: 'medium' };
      }
      return { action: 'consider_through_ball', priority: 'medium' };
    }

    // Under pressure - pass quickly
    if (underPressure) {
      return { action: 'quick_pass', priority: 'high' };
    }

    // Build up - advance or pass
    if (strategy.mentality === 'attacking' || strategy.mentality === 'ultra-attacking') {
      return { action: 'advance', priority: 'medium' };
    }

    return { action: 'build_up', priority: 'low' };
  }

  /**
   * Tactical decisions when teammate has ball (off-ball attacking)
   */
  _tacticalOffBallAttacking(player, context, strategy) {
    const { team, ball, isSecondHalf } = context;
    const targetGoal = team.getTargetGoal(isSecondHalf);
    const distToGoal = player.position.distance(targetGoal);
    const ballHolder = team.getPlayerWithBall();

    if (!ballHolder) {
      return { action: 'support', priority: 'low' };
    }

    // Attackers make runs
    if (player.isAttacker() && distToGoal < 40) {
      return { action: 'make_run', priority: 'high' };
    }

    // Midfielders offer passing options
    if (player.isMidfielder()) {
      return { action: 'offer_support', priority: 'medium' };
    }

    // Defenders hold position but push up
    if (player.isDefender()) {
      return { action: 'hold_shape', priority: 'low' };
    }

    return { action: 'support', priority: 'low' };
  }

  /**
   * Tactical decisions when defending
   */
  _tacticalDefending(player, context, strategy) {
    const { team, opposingTeam, ball, isSecondHalf } = context;
    const ownGoal = team.getOwnGoal(isSecondHalf);
    const distToOwnGoal = player.position.distance(ownGoal);
    const distToBall = player.position.distance(ball.position);

    // Closest player presses
    const closestToBall = team.getClosestToBall(ball.position);
    if (closestToBall === player && distToBall < 15) {
      return { action: 'press_ball', priority: 'high' };
    }

    // Second closest provides cover
    const allDists = team.players
      .filter(p => !p.isGoalkeeper())
      .map(p => ({ player: p, dist: p.position.distance(ball.position) }))
      .sort((a, b) => a.dist - b.dist);

    if (allDists.length > 1 && allDists[1].player === player && distToBall < 20) {
      return { action: 'cover', priority: 'medium' };
    }

    // Defenders track back
    if (player.isDefender()) {
      return { action: 'track_back', priority: 'high' };
    }

    // Midfielders maintain shape
    return { action: 'defensive_shape', priority: 'medium' };
  }

  /**
   * Technical Layer - Specific action execution
   */
  _technicalLayer(player, context, tactical) {
    const { team, opposingTeam, ball, rng, isSecondHalf } = context;

    switch (tactical.action) {
      case 'consider_shot':
        return this._decideShot(player, context);
      case 'consider_cross':
        return this._decideCross(player, context);
      case 'consider_through_ball':
        return this._decideThroughBall(player, context);
      case 'quick_pass':
        return this._decidePass(player, context, true);
      case 'build_up':
      case 'advance':
        return this._decideBuildUp(player, context, tactical.action === 'advance');
      case 'make_run':
        return this._decideRun(player, context);
      case 'offer_support':
        return this._decideSupport(player, context);
      case 'hold_shape':
        return this._decideHoldShape(player, context);
      case 'press_ball':
        return this._decidePress(player, context);
      case 'cover':
        return this._decideCover(player, context);
      case 'track_back':
        return this._decideTrackBack(player, context);
      case 'defensive_shape':
        return this._decideDefensiveShape(player, context);
      default:
        return { action: 'move_to_home', target: player.homePosition };
    }
  }

  /**
   * Physical Layer - Determine movement intensity
   */
  _physicalLayer(player, context, technical) {
    const { ball } = context;
    const stamina = player.stamina;
    const distToBall = player.position.distance(ball.position);

    // Low stamina = can't sprint
    if (stamina < 0.3) {
      return { mode: distToBall < 10 ? 'jog' : 'walk' };
    }

    // Urgent actions = sprint
    if (technical.action === 'press' || technical.action === 'chase_ball') {
      return { mode: 'sprint' };
    }

    // Making runs = sprint
    if (technical.action === 'run' && technical.urgent) {
      return { mode: 'sprint' };
    }

    // With ball and advancing = jog/sprint
    if (player.hasBall && technical.action === 'dribble') {
      return { mode: 'jog' };
    }

    // Default
    if (distToBall < 15) {
      return { mode: 'jog' };
    }

    return { mode: stamina > 0.6 ? 'jog' : 'walk' };
  }

  // === Technical decision helpers ===

  _decideShot(player, context) {
    const { team, opposingTeam, ball, rng, isSecondHalf } = context;
    const targetGoal = team.getTargetGoal(isSecondHalf);
    const distToGoal = player.position.distance(targetGoal);
    const shooting = player.getEffectiveAttr('shooting');

    // Check if clear shot
    const opponentsInWay = opposingTeam.players.filter(p => {
      const distToLine = this._pointToLineDistance(p.position, player.position, targetGoal);
      return distToLine < 2 && p.position.distance(player.position) < distToGoal;
    });

    const shotChance = (shooting / 20) * 0.5 + (opponentsInWay.length === 0 ? 0.3 : 0);
    
    if (distToGoal < 20 && rng.next() < shotChance) {
      return { action: 'shoot', target: targetGoal, power: 0.7 + rng.next() * 0.3 };
    }

    // Otherwise pass
    return this._decidePass(player, context, false);
  }

  _decideCross(player, context) {
    const { team, rng, isSecondHalf } = context;
    const targetGoal = team.getTargetGoal(isSecondHalf);
    
    // Find attackers in the box
    const attackersInBox = team.players.filter(p => {
      return p !== player && p.position.distance(targetGoal) < 20;
    });

    if (attackersInBox.length > 0) {
      const target = rng.pick(attackersInBox);
      return { action: 'cross', target: target.position.clone(), targetPlayer: target };
    }

    return this._decidePass(player, context, false);
  }

  _decideThroughBall(player, context) {
    const { team, opposingTeam, rng, isSecondHalf } = context;
    const vision = player.getEffectiveAttr('vision');
    const targetGoal = team.getTargetGoal(isSecondHalf);

    // Find runners ahead
    const runners = team.players.filter(p => {
      if (p === player) return false;
      const pDistToGoal = p.position.distance(targetGoal);
      const myDistToGoal = player.position.distance(targetGoal);
      return pDistToGoal < myDistToGoal - 5 && p.isAttacker();
    });

    if (runners.length > 0 && rng.next() < vision / 25) {
      const target = rng.pick(runners);
      return { action: 'through_ball', target: target.position.clone(), targetPlayer: target };
    }

    return this._decidePass(player, context, false);
  }

  _decidePass(player, context, quick) {
    const { team, opposingTeam, rng, isSecondHalf } = context;
    const targetGoal = team.getTargetGoal(isSecondHalf);

    // Find best passing option
    const options = team.players
      .filter(p => p !== player && !p.isGoalkeeper())
      .map(p => {
        const dist = player.position.distance(p.position);
        const distToGoal = p.position.distance(targetGoal);
        const opponentsNear = opposingTeam.players.filter(
          opp => opp.position.distance(p.position) < 4
        ).length;
        
        // Score: prefer forward passes to open players
        let score = 50 - distToGoal * 0.3 - opponentsNear * 15;
        if (dist > 40) score -= 20; // Too far
        if (dist < 5) score -= 10; // Too close
        if (quick && dist < 15) score += 10; // Quick pass prefers nearby

        return { player: p, score, dist };
      })
      .sort((a, b) => b.score - a.score);

    if (options.length > 0) {
      // Pick from top 3 options with some randomness
      const topN = Math.min(3, options.length);
      const chosen = options[rng.int(0, topN - 1)];
      return { action: 'pass', target: chosen.player.position.clone(), targetPlayer: chosen.player };
    }

    // No good option - dribble
    const dribbleDir = targetGoal.sub(player.position).normalize().mul(5);
    return { action: 'dribble', target: player.position.add(dribbleDir) };
  }

  _decideBuildUp(player, context, advance) {
    const { team, opposingTeam, rng, isSecondHalf } = context;
    const targetGoal = team.getTargetGoal(isSecondHalf);

    if (advance) {
      // Dribble forward
      const dir = targetGoal.sub(player.position).normalize();
      const lateralVariation = new Vector2(dir.y, -dir.x).mul((rng.next() - 0.5) * 3);
      const target = player.position.add(dir.mul(8)).add(lateralVariation);
      return { action: 'dribble', target };
    }

    // Look for pass
    return this._decidePass(player, context, false);
  }

  _decideRun(player, context) {
    const { team, opposingTeam, rng, isSecondHalf } = context;
    const targetGoal = team.getTargetGoal(isSecondHalf);
    const dir = targetGoal.sub(player.position).normalize();

    // Diagonal run
    const lateral = (rng.next() - 0.5) * 15;
    const forward = 10 + rng.next() * 10;
    const runTarget = player.position.add(dir.mul(forward)).add(dir.perpendicular().mul(lateral));

    // Clamp to pitch
    runTarget.x = Math.max(2, Math.min(PITCH_WIDTH - 2, runTarget.x));
    runTarget.y = Math.max(2, Math.min(PITCH_HEIGHT - 2, runTarget.y));

    return { action: 'run', target: runTarget, urgent: true };
  }

  _decideSupport(player, context) {
    const { team, ball, rng } = context;
    const ballHolder = team.getPlayerWithBall();
    if (!ballHolder) {
      return { action: 'move_to_home', target: player.homePosition };
    }

    // Move to create passing angle
    const offset = new Vector2(
      (rng.next() - 0.5) * 15,
      (rng.next() - 0.5) * 10
    );
    const supportPos = ballHolder.position.add(offset);
    supportPos.x = Math.max(2, Math.min(PITCH_WIDTH - 2, supportPos.x));
    supportPos.y = Math.max(2, Math.min(PITCH_HEIGHT - 2, supportPos.y));

    return { action: 'support', target: supportPos };
  }

  _decideHoldShape(player, context) {
    const { team, ball, isSecondHalf } = context;
    const attackDir = team.getAttackingDirection(isSecondHalf);
    
    // Push up slightly from home position
    const pushUp = attackDir * 8 * team.tactics.lineHeight;
    const target = new Vector2(
      player.homePosition.x + pushUp,
      player.homePosition.y
    );
    target.x = Math.max(2, Math.min(PITCH_WIDTH - 2, target.x));

    return { action: 'hold', target };
  }

  _decidePress(player, context) {
    const { ball } = context;
    return { action: 'press', target: ball.position.clone(), urgent: true };
  }

  _decideCover(player, context) {
    const { team, ball, isSecondHalf } = context;
    const ownGoal = team.getOwnGoal(isSecondHalf);
    
    // Position between ball and goal
    const coverPos = ball.position.lerp(ownGoal, 0.3);
    return { action: 'cover', target: coverPos };
  }

  _decideTrackBack(player, context) {
    const { team, isSecondHalf } = context;
    const ownGoal = team.getOwnGoal(isSecondHalf);
    
    // Move towards home position but biased towards own goal
    const target = player.homePosition.lerp(ownGoal, 0.2);
    return { action: 'track_back', target };
  }

  _decideDefensiveShape(player, context) {
    const { team, ball, isSecondHalf } = context;
    const ownGoal = team.getOwnGoal(isSecondHalf);
    
    // Compact shape between ball and goal
    const shapePos = player.homePosition.lerp(ownGoal, 0.15);
    // Shift towards ball laterally
    const lateralShift = (ball.position.y - PITCH_HEIGHT / 2) * 0.2;
    shapePos.y += lateralShift;
    shapePos.y = Math.max(5, Math.min(PITCH_HEIGHT - 5, shapePos.y));

    return { action: 'defensive_shape', target: shapePos };
  }

  /**
   * Helper: distance from point to line segment
   */
  _pointToLineDistance(point, lineStart, lineEnd) {
    const dx = lineEnd.x - lineStart.x;
    const dy = lineEnd.y - lineStart.y;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return point.distance(lineStart);

    let t = ((point.x - lineStart.x) * dx + (point.y - lineStart.y) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));

    const projX = lineStart.x + t * dx;
    const projY = lineStart.y + t * dy;
    return Math.sqrt((point.x - projX) ** 2 + (point.y - projY) ** 2);
  }
}
