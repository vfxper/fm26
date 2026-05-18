/**
 * FormationAI - Formation shapes, defensive/attacking transitions
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT } from '../core/Constants.js';
import { FORMATIONS } from '../data/Formations.js';

export class FormationAI {
  constructor(eventBus) {
    this.eventBus = eventBus;
  }

  /**
   * Set up formation positions for a team
   * @param {Object} team - Team entity
   * @param {boolean} isSecondHalf - Whether it's second half (flip positions)
   */
  setupFormation(team, isSecondHalf = false) {
    const formationData = FORMATIONS[team.formation] || FORMATIONS['4-4-2'];
    const positions = formationData.positions;

    // Assign positions to players based on their role
    const assignedPositions = this._assignPositions(team.players, positions, team.side, isSecondHalf);

    team.formationPositions = assignedPositions;

    // Set home positions
    for (let i = 0; i < team.players.length; i++) {
      if (assignedPositions[i]) {
        team.players[i].setHomePosition(assignedPositions[i].x, assignedPositions[i].y);
        team.players[i].position.copy(assignedPositions[i]);
      }
    }
  }

  /**
   * Update formation positions based on game state (attacking/defending transitions)
   * @param {Object} team - Team entity
   * @param {Object} ball - Ball entity
   * @param {boolean} isSecondHalf
   */
  updateFormation(team, ball, isSecondHalf) {
    const formationData = FORMATIONS[team.formation] || FORMATIONS['4-4-2'];
    const basePositions = formationData.positions;
    const tactics = team.tactics;

    for (let i = 0; i < team.players.length; i++) {
      const player = team.players[i];
      if (player.isGoalkeeper()) continue;

      const basePos = this._getBasePosition(basePositions, i, team.side, isSecondHalf);
      if (!basePos) continue;

      // Apply tactical adjustments
      let adjustedPos = basePos.clone();

      // Line height adjustment
      const attackDir = team.getAttackingDirection(isSecondHalf);
      const lineShift = (tactics.lineHeight - 0.5) * 15 * attackDir;
      adjustedPos.x += lineShift;

      // Width adjustment
      const widthFactor = 0.7 + tactics.width * 0.6; // 0.7 to 1.3
      const centerY = PITCH_HEIGHT / 2;
      adjustedPos.y = centerY + (adjustedPos.y - centerY) * widthFactor;

      // Ball attraction - players shift towards ball
      const ballAttraction = 0.15;
      adjustedPos = adjustedPos.lerp(ball.position, ballAttraction * 0.3);

      // Possession-based shift
      if (team.hasPossession) {
        // Push up when attacking
        adjustedPos.x += attackDir * 8;
      } else {
        // Drop back when defending
        adjustedPos.x -= attackDir * 5;
      }

      // Clamp to pitch
      adjustedPos.x = Math.max(3, Math.min(PITCH_WIDTH - 3, adjustedPos.x));
      adjustedPos.y = Math.max(3, Math.min(PITCH_HEIGHT - 3, adjustedPos.y));

      // Update home position (players will move towards this)
      player.homePosition.copy(adjustedPos);
    }
  }

  /**
   * Assign formation positions to players
   */
  _assignPositions(players, positions, side, isSecondHalf) {
    const assigned = [];
    const positionOrder = ['GK', 'CB', 'RB', 'LB', 'RWB', 'LWB', 'DM', 'CM', 'AM', 'RM', 'LM', 'RW', 'LW', 'ST', 'CF'];

    // Sort players by position priority
    const sortedPlayers = [...players].sort((a, b) => {
      return positionOrder.indexOf(a.positionRole) - positionOrder.indexOf(b.positionRole);
    });

    for (let i = 0; i < sortedPlayers.length; i++) {
      const posData = positions[i] || positions[positions.length - 1];
      const worldPos = this._formationToWorld(posData, side, isSecondHalf);
      
      // Find original index
      const originalIdx = players.indexOf(sortedPlayers[i]);
      assigned[originalIdx] = worldPos;
    }

    return assigned;
  }

  /**
   * Convert formation coordinate (0-1 range) to world position
   */
  _formationToWorld(posData, side, isSecondHalf) {
    let x = posData.x; // 0 = own goal line, 1 = opponent goal line
    let y = posData.y; // 0 = left touchline, 1 = right touchline

    // Convert to world coordinates
    if (side === 'home') {
      if (!isSecondHalf) {
        // Home attacks right
        x = x * PITCH_WIDTH;
      } else {
        // Home attacks left in second half
        x = (1 - x) * PITCH_WIDTH;
      }
    } else {
      if (!isSecondHalf) {
        // Away attacks left
        x = (1 - x) * PITCH_WIDTH;
      } else {
        // Away attacks right in second half
        x = x * PITCH_WIDTH;
      }
    }

    y = y * PITCH_HEIGHT;

    return new Vector2(x, y);
  }

  /**
   * Get base position for a player index
   */
  _getBasePosition(positions, playerIdx, side, isSecondHalf) {
    if (playerIdx >= positions.length) return null;
    return this._formationToWorld(positions[playerIdx], side, isSecondHalf);
  }

  /**
   * Get compact defensive shape (for defending set pieces etc.)
   */
  getCompactDefensiveShape(team, isSecondHalf) {
    const ownGoal = team.getOwnGoal(isSecondHalf);
    const positions = [];

    for (const player of team.players) {
      if (player.isGoalkeeper()) {
        positions.push(ownGoal.clone());
        continue;
      }

      // Everyone drops deep
      const homePos = player.homePosition;
      const compactPos = homePos.lerp(ownGoal, 0.4);
      positions.push(compactPos);
    }

    return positions;
  }
}
