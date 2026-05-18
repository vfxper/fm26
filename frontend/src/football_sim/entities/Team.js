/**
 * Team - Team entity with formation, tactics, players array
 */
import { Vector2 } from '../core/Vector2.js';
import { Player } from './Player.js';
import { PITCH_WIDTH, PITCH_HEIGHT } from '../core/Constants.js';

export class Team {
  /**
   * @param {Object} data
   * @param {string} data.name - Team name
   * @param {string} data.color - Team color (hex)
   * @param {string} data.side - 'home' or 'away'
   * @param {string} data.formation - Formation string e.g. '4-3-3'
   * @param {Array} data.players - Array of player data objects
   * @param {Object} [data.tactics] - Tactical settings
   */
  constructor(data) {
    this.name = data.name || 'Team';
    this.color = data.color || '#ffffff';
    this.side = data.side || 'home'; // 'home' attacks right (positive x), 'away' attacks left
    this.formation = data.formation || '4-4-2';

    // Tactics
    this.tactics = {
      mentality: 'balanced', // 'defensive', 'cautious', 'balanced', 'attacking', 'ultra-attacking'
      pressingIntensity: 0.5, // 0-1
      lineHeight: 0.5, // 0-1 (0=deep, 1=high)
      width: 0.5, // 0-1 (0=narrow, 1=wide)
      tempo: 0.5, // 0-1 (0=slow, 1=fast)
      passLength: 0.5, // 0-1 (0=short, 1=long)
      ...data.tactics
    };

    // Create players
    this.players = [];
    if (data.players && data.players.length > 0) {
      for (const pData of data.players) {
        const player = new Player({ ...pData, teamSide: this.side });
        this.players.push(player);
      }
    }

    // State
    this.hasPossession = false;
    this.score = 0;
    this.isAttacking = false;

    // Formation positions (will be set by FormationAI)
    this.formationPositions = [];
  }

  /**
   * Get the goalkeeper
   */
  getGoalkeeper() {
    return this.players.find(p => p.isGoalkeeper());
  }

  /**
   * Get outfield players
   */
  getOutfieldPlayers() {
    return this.players.filter(p => !p.isGoalkeeper());
  }

  /**
   * Get defenders
   */
  getDefenders() {
    return this.players.filter(p => p.isDefender());
  }

  /**
   * Get midfielders
   */
  getMidfielders() {
    return this.players.filter(p => p.isMidfielder());
  }

  /**
   * Get attackers
   */
  getAttackers() {
    return this.players.filter(p => p.isAttacker());
  }

  /**
   * Get player closest to ball
   */
  getClosestToBall(ballPos) {
    let closest = null;
    let minDist = Infinity;
    for (const player of this.players) {
      const dist = player.position.distance(ballPos);
      if (dist < minDist) {
        minDist = dist;
        closest = player;
      }
    }
    return closest;
  }

  /**
   * Get player with ball
   */
  getPlayerWithBall() {
    return this.players.find(p => p.hasBall);
  }

  /**
   * Get the attacking direction x-component
   * Home attacks right (+x), Away attacks left (-x)
   * After half-time, directions swap
   */
  getAttackingDirection(isSecondHalf = false) {
    const baseDir = this.side === 'home' ? 1 : -1;
    return isSecondHalf ? -baseDir : baseDir;
  }

  /**
   * Get the goal position this team is attacking
   */
  getTargetGoal(isSecondHalf = false) {
    const dir = this.getAttackingDirection(isSecondHalf);
    const goalX = dir > 0 ? PITCH_WIDTH : 0;
    return new Vector2(goalX, PITCH_HEIGHT / 2);
  }

  /**
   * Get the goal position this team is defending
   */
  getOwnGoal(isSecondHalf = false) {
    const dir = this.getAttackingDirection(isSecondHalf);
    const goalX = dir > 0 ? 0 : PITCH_WIDTH;
    return new Vector2(goalX, PITCH_HEIGHT / 2);
  }

  /**
   * Get average position of all outfield players
   */
  getCentroid() {
    const outfield = this.getOutfieldPlayers();
    if (outfield.length === 0) return new Vector2(PITCH_WIDTH / 2, PITCH_HEIGHT / 2);
    
    let sumX = 0, sumY = 0;
    for (const p of outfield) {
      sumX += p.position.x;
      sumY += p.position.y;
    }
    return new Vector2(sumX / outfield.length, sumY / outfield.length);
  }

  /**
   * Get the last defender's x position (for offside)
   */
  getLastDefenderX(isSecondHalf = false) {
    const dir = this.getAttackingDirection(isSecondHalf);
    const defenders = this.getDefenders();
    if (defenders.length === 0) return dir > 0 ? 0 : PITCH_WIDTH;

    // Last defender is the one closest to own goal
    if (dir > 0) {
      // Attacking right, so last defender has smallest x
      return Math.min(...defenders.map(d => d.position.x));
    } else {
      // Attacking left, so last defender has largest x
      return Math.max(...defenders.map(d => d.position.x));
    }
  }

  /**
   * Reset all players to formation positions
   */
  resetToFormation() {
    for (let i = 0; i < this.players.length; i++) {
      if (this.formationPositions[i]) {
        this.players[i].position.copy(this.formationPositions[i]);
        this.players[i].homePosition.copy(this.formationPositions[i]);
        this.players[i].velocity.set(0, 0);
        this.players[i].currentSpeed = 0;
        this.players[i].targetPosition = null;
      }
    }
  }
}
