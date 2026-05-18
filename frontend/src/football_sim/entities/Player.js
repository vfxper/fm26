/**
 * Player - Player entity with position, state machine, attributes
 */
import { Vector2 } from '../core/Vector2.js';
import {
  FATIGUE_THRESHOLD_LOW, FATIGUE_THRESHOLD_CRITICAL,
  FATIGUE_SPEED_PENALTY_LOW, FATIGUE_SPEED_PENALTY_CRITICAL,
  FATIGUE_ATTR_PENALTY_LOW, FATIGUE_ATTR_PENALTY_CRITICAL
} from '../core/Constants.js';

// Player states
export const PlayerState = {
  IDLE: 'idle',
  WALKING: 'walking',
  JOGGING: 'jogging',
  SPRINTING: 'sprinting',
  WITH_BALL: 'with_ball',
  DRIBBLING: 'dribbling',
  PASSING: 'passing',
  SHOOTING: 'shooting',
  TACKLING: 'tackling',
  HEADING: 'heading',
  CELEBRATING: 'celebrating',
  INJURED: 'injured',
  GK_DIVING: 'gk_diving',
  GK_POSITIONING: 'gk_positioning',
};

export class Player {
  /**
   * @param {Object} data - Player data
   * @param {string} data.name - Player name
   * @param {number} data.number - Jersey number
   * @param {string} data.position - Position code (GK, CB, RB, LB, DM, CM, AM, RW, LW, ST)
   * @param {Object} data.attributes - Player attributes (1-20 scale)
   * @param {string} data.teamSide - 'home' or 'away'
   */
  constructor(data) {
    this.id = data.id || Math.random().toString(36).substr(2, 9);
    this.name = data.name || 'Unknown';
    this.number = data.number || 0;
    this.positionRole = data.position || 'CM';
    this.teamSide = data.teamSide || 'home';

    // Attributes (1-20 scale)
    this.attributes = {
      pace: 10,
      acceleration: 10,
      stamina: 10,
      strength: 10,
      agility: 10,
      jumping: 10,
      passing: 10,
      vision: 10,
      crossing: 10,
      dribbling: 10,
      technique: 10,
      shooting: 10,
      longShots: 10,
      heading: 10,
      tackling: 10,
      marking: 10,
      positioning: 10,
      workRate: 10,
      decisions: 10,
      composure: 10,
      anticipation: 10,
      concentration: 10,
      teamwork: 10,
      flair: 10,
      // GK specific
      handling: 10,
      reflexes: 10,
      oneOnOnes: 10,
      commandOfArea: 10,
      ...data.attributes
    };

    // Physics state
    this.position = new Vector2(0, 0);
    this.velocity = new Vector2(0, 0);
    this.facing = 0; // radians
    this.currentSpeed = 0;

    // Movement
    this.targetPosition = null;
    this.movementMode = 'jog'; // 'walk', 'jog', 'sprint'
    this.homePosition = new Vector2(0, 0); // Formation position

    // State
    this.state = PlayerState.IDLE;
    this.isActive = true;
    this.hasBall = false;

    // Ball interaction
    this.canReachBall = false;
    this.distToBall = Infinity;

    // Collision
    this.lastCollision = null;

    // Fatigue (0 = exhausted, 1 = full)
    this.stamina = 1.0;

    // AI state
    this.aiState = {
      role: 'default', // Current tactical role
      decision: null, // Current decision
      decisionTimer: 0, // Time until next decision
      targetPlayer: null, // Player being marked/passed to
      runType: null, // Type of run being made
    };

    // Animation state
    this.animState = {
      walkCycle: 0,
      kickPhase: 0,
      isKicking: false,
      celebrationType: null,
      celebrationTimer: 0,
    };

    // Stats
    this.matchStats = {
      passes: 0,
      passesCompleted: 0,
      shots: 0,
      shotsOnTarget: 0,
      goals: 0,
      assists: 0,
      tackles: 0,
      tacklesWon: 0,
      fouls: 0,
      yellowCards: 0,
      redCards: 0,
      distanceCovered: 0,
      sprints: 0,
    };

    // Previous position for interpolation
    this.prevPosition = this.position.clone();
  }

  /**
   * Get fatigue speed factor
   * @returns {number} Speed multiplier (0.7 - 1.0)
   */
  getFatigueFactor() {
    if (this.stamina < FATIGUE_THRESHOLD_CRITICAL) {
      return 1 - FATIGUE_SPEED_PENALTY_CRITICAL;
    } else if (this.stamina < FATIGUE_THRESHOLD_LOW) {
      return 1 - FATIGUE_SPEED_PENALTY_LOW;
    }
    return 1.0;
  }

  /**
   * Get effective attribute value (reduced by fatigue)
   * @param {string} attr - Attribute name
   * @returns {number} Effective value
   */
  getEffectiveAttr(attr) {
    let value = this.attributes[attr] || 10;
    if (this.stamina < FATIGUE_THRESHOLD_CRITICAL) {
      value *= (1 - FATIGUE_ATTR_PENALTY_CRITICAL);
    } else if (this.stamina < FATIGUE_THRESHOLD_LOW) {
      value *= (1 - FATIGUE_ATTR_PENALTY_LOW);
    }
    return value;
  }

  /**
   * Store previous position for interpolation
   */
  storePrevious() {
    this.prevPosition.copy(this.position);
  }

  /**
   * Get interpolated position
   */
  getInterpolatedPosition(alpha) {
    return this.prevPosition.lerp(this.position, alpha);
  }

  /**
   * Set home/formation position
   */
  setHomePosition(x, y) {
    this.homePosition.set(x, y);
  }

  /**
   * Move to target position
   * @param {Vector2} target
   * @param {string} mode - 'walk', 'jog', 'sprint'
   */
  moveTo(target, mode = 'jog') {
    this.targetPosition = target.clone();
    this.movementMode = mode;
  }

  /**
   * Stop moving
   */
  stop() {
    this.targetPosition = null;
    this.movementMode = 'walk';
  }

  /**
   * Is this player a goalkeeper?
   */
  isGoalkeeper() {
    return this.positionRole === 'GK';
  }

  /**
   * Is this player a defender?
   */
  isDefender() {
    return ['CB', 'RB', 'LB', 'RWB', 'LWB'].includes(this.positionRole);
  }

  /**
   * Is this player a midfielder?
   */
  isMidfielder() {
    return ['DM', 'CM', 'AM', 'RM', 'LM'].includes(this.positionRole);
  }

  /**
   * Is this player an attacker?
   */
  isAttacker() {
    return ['RW', 'LW', 'ST', 'CF', 'SS'].includes(this.positionRole);
  }

  /**
   * Get overall rating for quick comparisons
   */
  getOverall() {
    const a = this.attributes;
    if (this.isGoalkeeper()) {
      return Math.round((a.handling + a.reflexes + a.positioning + a.oneOnOnes + a.commandOfArea) / 5);
    }
    return Math.round((a.pace + a.passing + a.shooting + a.dribbling + a.tackling + a.positioning) / 6);
  }
}
