/**
 * SetPieceSystem - Handles corners, free kicks, throw-ins, goal kicks, penalties
 * Positions players, selects taker, executes set piece
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT, PENALTY_SPOT_DISTANCE, GOAL_Y_MIN, GOAL_Y_MAX, CENTER_CIRCLE_RADIUS } from '../core/Constants.js';
import { PlayState } from '../core/MatchState.js';

export class SetPieceSystem {
  constructor(eventBus, rng) {
    this.eventBus = eventBus;
    this.rng = rng;
    
    // Set piece state
    this.active = false;
    this.type = null;
    this.team = null; // 'home' or 'away'
    this.position = null;
    this.taker = null;
    this.phase = 'positioning'; // 'positioning', 'ready', 'executing'
    this.timer = 0;
    this.positioningTime = 2.0; // seconds for players to get in position
  }

  /**
   * Initiate a set piece
   * @param {string} type - PlayState type
   * @param {string} team - Team taking ('home' or 'away')
   * @param {Vector2} position - Position of set piece
   * @param {Array} homePlayers - Home team players
   * @param {Array} awayPlayers - Away team players
   */
  initiate(type, team, position, homePlayers, awayPlayers) {
    this.active = true;
    this.type = type;
    this.team = team;
    this.position = position.clone();
    this.phase = 'positioning';
    this.timer = this.positioningTime;
    
    const attackers = team === 'home' ? homePlayers : awayPlayers;
    const defenders = team === 'home' ? awayPlayers : homePlayers;
    
    // Select taker
    this.taker = this._selectTaker(type, attackers);
    
    // Position players
    this._positionPlayers(type, team, position, attackers, defenders);
  }

  /**
   * Update set piece state
   * @param {number} dt - Delta time
   * @returns {Object|null} Action to execute when ready
   */
  update(dt) {
    if (!this.active) return null;
    
    this.timer -= dt;
    
    if (this.phase === 'positioning' && this.timer <= 0) {
      this.phase = 'ready';
      this.timer = this.rng.range(0.5, 1.5); // Brief pause before taking
      return null;
    }
    
    if (this.phase === 'ready' && this.timer <= 0) {
      this.phase = 'executing';
      this.active = false;
      return this._execute();
    }
    
    return null;
  }

  /**
   * Select the best taker for this set piece type
   */
  _selectTaker(type, players) {
    const activePlayers = players.filter(p => p.isActive && !p.isGoalkeeper());
    if (activePlayers.length === 0) return players[0];
    
    switch (type) {
      case PlayState.CORNER:
        // Best crosser
        return activePlayers.reduce((best, p) => 
          p.getEffectiveAttr('crossing') > best.getEffectiveAttr('crossing') ? p : best
        );
        
      case PlayState.FREE_KICK:
        // Best free kick taker (technique + shooting)
        return activePlayers.reduce((best, p) => {
          const score = p.getEffectiveAttr('technique') + p.getEffectiveAttr('shooting');
          const bestScore = best.getEffectiveAttr('technique') + best.getEffectiveAttr('shooting');
          return score > bestScore ? p : best;
        });
        
      case PlayState.PENALTY:
        // Best penalty taker (composure + shooting)
        return activePlayers.reduce((best, p) => {
          const score = p.getEffectiveAttr('composure') + p.getEffectiveAttr('shooting');
          const bestScore = best.getEffectiveAttr('composure') + best.getEffectiveAttr('shooting');
          return score > bestScore ? p : best;
        });
        
      case PlayState.THROW_IN:
        // Nearest player (or one with best long throw)
        return activePlayers.reduce((best, p) => {
          const dist = p.position.distance(this.position);
          const bestDist = best.position.distance(this.position);
          return dist < bestDist ? p : best;
        });
        
      case PlayState.GOAL_KICK:
        // Goalkeeper takes it
        const gk = players.find(p => p.isGoalkeeper());
        return gk || activePlayers[0];
        
      default:
        return activePlayers[0];
    }
  }

  /**
   * Position players for set piece
   */
  _positionPlayers(type, team, position, attackers, defenders) {
    const attackDir = team === 'home' ? 1 : -1; // 1 = attacking right, -1 = attacking left
    
    switch (type) {
      case PlayState.CORNER:
        this._positionForCorner(position, attackers, defenders, attackDir);
        break;
      case PlayState.FREE_KICK:
        this._positionForFreeKick(position, attackers, defenders, attackDir);
        break;
      case PlayState.PENALTY:
        this._positionForPenalty(position, attackers, defenders, attackDir);
        break;
      case PlayState.GOAL_KICK:
        this._positionForGoalKick(position, attackers, defenders, attackDir);
        break;
      case PlayState.THROW_IN:
        // Players stay roughly in position for throw-ins
        break;
      case PlayState.KICK_OFF:
        this._positionForKickOff(attackers, defenders, attackDir);
        break;
    }
  }

  _positionForCorner(position, attackers, defenders, attackDir) {
    // Attackers: 4-5 in the box, 1-2 edge of box, rest midfield
    const active = attackers.filter(p => p.isActive && p !== this.taker);
    const goalY = PITCH_HEIGHT / 2;
    const goalX = attackDir > 0 ? PITCH_WIDTH : 0;
    
    // Put tall/heading players in box
    const inBox = active
      .sort((a, b) => b.getEffectiveAttr('heading') - a.getEffectiveAttr('heading'))
      .slice(0, 5);
    
    inBox.forEach((p, i) => {
      const targetX = goalX - attackDir * this.rng.range(3, 14);
      const targetY = goalY + (i - 2) * 4 + this.rng.range(-2, 2);
      p.targetPosition = new Vector2(targetX, Math.max(2, Math.min(PITCH_HEIGHT - 2, targetY)));
    });
  }

  _positionForFreeKick(position, attackers, defenders, attackDir) {
    const distToGoal = attackDir > 0 ? PITCH_WIDTH - position.x : position.x;
    
    if (distToGoal < 30) {
      // Shooting range - set up wall and attackers
      // Defenders form wall
      const wallDist = 9.15; // 10 yards
      const wallDir = attackDir > 0 ? -1 : 1;
      const wallX = position.x + wallDir * wallDist;
      
      const wallPlayers = defenders
        .filter(p => p.isActive && !p.isGoalkeeper())
        .slice(0, 4);
      
      wallPlayers.forEach((p, i) => {
        p.targetPosition = new Vector2(wallX, position.y + (i - 1.5) * 0.8);
      });
    }
  }

  _positionForPenalty(position, attackers, defenders, attackDir) {
    // Everyone outside the box except taker and GK
    const boxEdgeX = attackDir > 0 ? PITCH_WIDTH - 16.5 : 16.5;
    
    attackers.filter(p => p.isActive && p !== this.taker).forEach((p, i) => {
      const x = boxEdgeX - attackDir * 2;
      const y = PITCH_HEIGHT / 2 + (i - 4) * 3;
      p.targetPosition = new Vector2(x, Math.max(5, Math.min(PITCH_HEIGHT - 5, y)));
    });
    
    defenders.filter(p => p.isActive && !p.isGoalkeeper()).forEach((p, i) => {
      const x = boxEdgeX - attackDir * 2;
      const y = PITCH_HEIGHT / 2 + (i - 4) * 3;
      p.targetPosition = new Vector2(x, Math.max(5, Math.min(PITCH_HEIGHT - 5, y)));
    });
  }

  _positionForGoalKick(position, attackers, defenders, attackDir) {
    // Spread out for goal kick distribution
  }

  _positionForKickOff(attackers, defenders, attackDir) {
    // Reset to formation positions
    attackers.forEach(p => {
      if (p.isActive) p.targetPosition = p.homePosition.clone();
    });
    defenders.forEach(p => {
      if (p.isActive) p.targetPosition = p.homePosition.clone();
    });
  }

  /**
   * Execute the set piece (kick/throw)
   * @returns {Object} Execution data for ball physics
   */
  _execute() {
    switch (this.type) {
      case PlayState.CORNER:
        return this._executeCorner();
      case PlayState.FREE_KICK:
        return this._executeFreeKick();
      case PlayState.PENALTY:
        return this._executePenalty();
      case PlayState.GOAL_KICK:
        return this._executeGoalKick();
      case PlayState.THROW_IN:
        return this._executeThrowIn();
      case PlayState.KICK_OFF:
        return this._executeKickOff();
      default:
        return { type: 'pass', taker: this.taker, position: this.position };
    }
  }

  _executeCorner() {
    return {
      type: 'cross',
      taker: this.taker,
      position: this.position,
      targetArea: new Vector2(
        this.team === 'home' ? PITCH_WIDTH - 10 : 10,
        PITCH_HEIGHT / 2 + this.rng.range(-8, 8)
      ),
      power: this.rng.range(0.6, 0.85),
      loft: this.rng.range(0.4, 0.6),
      spin: this.rng.range(-0.5, 0.5),
    };
  }

  _executeFreeKick() {
    const attackDir = this.team === 'home' ? 1 : -1;
    const distToGoal = attackDir > 0 ? PITCH_WIDTH - this.position.x : this.position.x;
    
    if (distToGoal < 28) {
      // Direct shot
      const goalCenter = new Vector2(
        attackDir > 0 ? PITCH_WIDTH : 0,
        PITCH_HEIGHT / 2 + this.rng.range(-3, 3)
      );
      return {
        type: 'shot',
        taker: this.taker,
        position: this.position,
        target: goalCenter,
        power: this.rng.range(0.75, 0.95),
        spin: this.rng.range(-0.8, 0.8),
        loft: this.rng.range(0.1, 0.3),
      };
    } else {
      // Cross/pass
      return {
        type: 'pass',
        taker: this.taker,
        position: this.position,
        power: this.rng.range(0.5, 0.8),
      };
    }
  }

  _executePenalty() {
    const attackDir = this.team === 'home' ? 1 : -1;
    // Penalty: aim for corner
    const side = this.rng.chance(0.5) ? -1 : 1;
    const height = this.rng.range(0, 0.3); // Low or mid-height
    
    return {
      type: 'penalty',
      taker: this.taker,
      position: this.position,
      target: new Vector2(
        attackDir > 0 ? PITCH_WIDTH : 0,
        PITCH_HEIGHT / 2 + side * this.rng.range(1.5, 3.2)
      ),
      power: this.rng.range(0.8, 0.95),
      loft: height,
      side: side,
    };
  }

  _executeGoalKick() {
    return {
      type: 'goal_kick',
      taker: this.taker,
      position: this.position,
      power: this.rng.range(0.6, 0.9),
      loft: this.rng.range(0.3, 0.5),
    };
  }

  _executeThrowIn() {
    return {
      type: 'throw_in',
      taker: this.taker,
      position: this.position,
      power: this.rng.range(0.3, 0.6),
    };
  }

  _executeKickOff() {
    return {
      type: 'kick_off',
      taker: this.taker,
      position: this.position,
    };
  }

  /**
   * Is a set piece currently active?
   */
  isActive() {
    return this.active;
  }

  /**
   * Reset
   */
  reset() {
    this.active = false;
    this.type = null;
    this.team = null;
    this.taker = null;
    this.phase = 'positioning';
  }
}
