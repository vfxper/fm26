/**
 * SetPieceAI - Corner routines, free kick positioning, penalty logic
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT, GOAL_Y_MIN, GOAL_Y_MAX, PENALTY_SPOT_DISTANCE } from '../core/Constants.js';

export class SetPieceAI {
  constructor(eventBus) {
    this.eventBus = eventBus;
  }

  /**
   * Set up corner kick positions
   * @param {Object} attackingTeam - Team taking the corner
   * @param {Object} defendingTeam - Defending team
   * @param {string} side - 'left' or 'right' (which side of pitch)
   * @param {boolean} isSecondHalf
   * @param {Object} rng
   * @returns {Object} {taker, positions, targetArea}
   */
  setupCorner(attackingTeam, defendingTeam, side, isSecondHalf, rng) {
    const attackDir = attackingTeam.getAttackingDirection(isSecondHalf);
    const goalX = attackDir > 0 ? PITCH_WIDTH : 0;
    const cornerY = side === 'left' ? 0 : PITCH_HEIGHT;

    // Select corner taker (best crossing)
    const taker = this._selectSetPieceTaker(attackingTeam, 'crossing');

    // Position attackers in the box
    const attackPositions = [];
    const attackers = attackingTeam.players.filter(p => p !== taker && !p.isGoalkeeper());
    
    // Near post, far post, edge of box, penalty spot
    const targetAreas = [
      new Vector2(goalX - attackDir * 5, PITCH_HEIGHT / 2 - 5),  // Near post
      new Vector2(goalX - attackDir * 5, PITCH_HEIGHT / 2 + 5),  // Far post
      new Vector2(goalX - attackDir * 11, PITCH_HEIGHT / 2),      // Penalty spot
      new Vector2(goalX - attackDir * 16, PITCH_HEIGHT / 2 - 3), // Edge of box
      new Vector2(goalX - attackDir * 16, PITCH_HEIGHT / 2 + 3), // Edge of box
    ];

    for (let i = 0; i < attackers.length && i < targetAreas.length; i++) {
      attackPositions.push({
        player: attackers[i],
        position: targetAreas[i].add(new Vector2((rng.next() - 0.5) * 2, (rng.next() - 0.5) * 2))
      });
    }

    // Remaining attackers stay back
    for (let i = targetAreas.length; i < attackers.length; i++) {
      attackPositions.push({
        player: attackers[i],
        position: new Vector2(PITCH_WIDTH / 2, PITCH_HEIGHT / 2 + (rng.next() - 0.5) * 20)
      });
    }

    // Defending positions
    const defPositions = this._setupCornerDefense(defendingTeam, goalX, attackDir, rng);

    // Target area for the cross
    const targetArea = targetAreas[rng.int(0, 2)]; // Near post, far post, or penalty spot

    return {
      taker,
      takerPosition: new Vector2(goalX + (attackDir > 0 ? -0.5 : 0.5), cornerY),
      attackPositions,
      defPositions,
      targetArea
    };
  }

  /**
   * Set up free kick positions
   * @param {Object} attackingTeam
   * @param {Object} defendingTeam
   * @param {Vector2} foulPosition - Where the foul occurred
   * @param {boolean} isSecondHalf
   * @param {Object} rng
   */
  setupFreeKick(attackingTeam, defendingTeam, foulPosition, isSecondHalf, rng) {
    const attackDir = attackingTeam.getAttackingDirection(isSecondHalf);
    const targetGoal = attackingTeam.getTargetGoal(isSecondHalf);
    const distToGoal = foulPosition.distance(targetGoal);

    const isDirect = distToGoal < 30; // Shooting range

    // Select taker
    const taker = isDirect
      ? this._selectSetPieceTaker(attackingTeam, 'longShots')
      : this._selectSetPieceTaker(attackingTeam, 'passing');

    // Wall
    const wallPlayers = Math.min(5, Math.max(2, Math.floor(distToGoal / 6)));
    const wallCenter = foulPosition.add(
      targetGoal.sub(foulPosition).normalize().mul(9.15) // 9.15m from ball
    );

    const wallPositions = [];
    for (let i = 0; i < wallPlayers; i++) {
      const offset = (i - (wallPlayers - 1) / 2) * 0.8;
      const perpDir = targetGoal.sub(foulPosition).normalize().perpendicular();
      wallPositions.push(wallCenter.add(perpDir.mul(offset)));
    }

    return {
      taker,
      takerPosition: foulPosition,
      isDirect,
      wallPositions,
      targetGoal,
      distToGoal
    };
  }

  /**
   * Set up penalty
   * @param {Object} attackingTeam
   * @param {Object} defendingTeam
   * @param {boolean} isSecondHalf
   * @param {Object} rng
   */
  setupPenalty(attackingTeam, defendingTeam, isSecondHalf, rng) {
    const attackDir = attackingTeam.getAttackingDirection(isSecondHalf);
    const goalX = attackDir > 0 ? PITCH_WIDTH : 0;
    const penaltySpot = new Vector2(
      goalX - attackDir * PENALTY_SPOT_DISTANCE,
      PITCH_HEIGHT / 2
    );

    // Select penalty taker (best composure + shooting)
    const taker = this._selectPenaltyTaker(attackingTeam);
    const gk = defendingTeam.getGoalkeeper();

    return {
      taker,
      takerPosition: penaltySpot,
      goalkeeper: gk,
      goalCenter: new Vector2(goalX, PITCH_HEIGHT / 2)
    };
  }

  /**
   * Execute penalty kick decision
   * @param {Object} taker - Penalty taker
   * @param {Object} rng
   * @returns {Object} {direction, power, height}
   */
  decidePenalty(taker, rng) {
    const composure = taker.attributes.composure || 10;
    const technique = taker.attributes.technique || 10;

    // Choose side: left, right, or center
    const sideChoice = rng.next();
    let targetY;
    if (sideChoice < 0.4) {
      targetY = GOAL_Y_MIN + 1; // Left side of goal
    } else if (sideChoice < 0.8) {
      targetY = GOAL_Y_MAX - 1; // Right side of goal
    } else {
      targetY = PITCH_HEIGHT / 2; // Down the middle
    }

    // Height: low, mid, high
    const heightChoice = rng.next();
    let height = 0;
    if (heightChoice < 0.5) height = 0.1; // Low
    else if (heightChoice < 0.8) height = 0.3; // Mid
    else height = 0.6; // High

    // Power (composure affects consistency)
    const power = 0.7 + (composure / 20) * 0.2 + rng.next() * 0.1;

    // Accuracy (can miss if low composure)
    const missChance = (1 - composure / 20) * 0.15;
    const missed = rng.next() < missChance;

    return { targetY, height, power, missed };
  }

  /**
   * Set up throw-in positions
   */
  setupThrowIn(attackingTeam, defendingTeam, throwPosition, isSecondHalf, rng) {
    const taker = this._findNearestPlayer(attackingTeam, throwPosition);
    
    // Nearby teammates offer short options
    const options = attackingTeam.players
      .filter(p => p !== taker && !p.isGoalkeeper())
      .sort((a, b) => a.position.distance(throwPosition) - b.position.distance(throwPosition))
      .slice(0, 3);

    return { taker, takerPosition: throwPosition, options };
  }

  /**
   * Set up goal kick
   */
  setupGoalKick(team, isSecondHalf, rng) {
    const gk = team.getGoalkeeper();
    const ownGoal = team.getOwnGoal(isSecondHalf);
    const kickPos = new Vector2(ownGoal.x + team.getAttackingDirection(isSecondHalf) * 6, PITCH_HEIGHT / 2);

    // Short or long?
    const goShort = team.tactics.passLength < 0.5 && rng.next() < 0.6;

    return { taker: gk, takerPosition: kickPos, goShort };
  }

  // === Helpers ===

  _selectSetPieceTaker(team, attribute) {
    return team.players
      .filter(p => !p.isGoalkeeper())
      .sort((a, b) => (b.attributes[attribute] || 10) - (a.attributes[attribute] || 10))[0];
  }

  _selectPenaltyTaker(team) {
    return team.players
      .filter(p => !p.isGoalkeeper())
      .sort((a, b) => {
        const scoreA = (a.attributes.composure || 10) + (a.attributes.shooting || 10);
        const scoreB = (b.attributes.composure || 10) + (b.attributes.shooting || 10);
        return scoreB - scoreA;
      })[0];
  }

  _findNearestPlayer(team, position) {
    return team.players
      .filter(p => !p.isGoalkeeper())
      .sort((a, b) => a.position.distance(position) - b.position.distance(position))[0];
  }

  _setupCornerDefense(team, goalX, attackDir, rng) {
    const positions = [];
    const outfield = team.getOutfieldPlayers();

    // Most players in the box
    for (let i = 0; i < outfield.length; i++) {
      const pos = new Vector2(
        goalX - attackDir * (3 + rng.next() * 12),
        PITCH_HEIGHT / 2 + (rng.next() - 0.5) * 14
      );
      positions.push({ player: outfield[i], position: pos });
    }

    return positions;
  }
}
