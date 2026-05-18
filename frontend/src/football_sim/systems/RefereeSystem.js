/**
 * RefereeSystem - Foul detection, cards, advantage, offside, VAR
 */
import { Vector2 } from '../core/Vector2.js';
import { ADVANTAGE_WINDOW, OFFSIDE_TOLERANCE, PITCH_WIDTH } from '../core/Constants.js';

export const FoulSeverity = {
  MINOR: 'minor',       // Free kick only
  YELLOW: 'yellow',     // Yellow card
  RED: 'red',           // Straight red
  SECOND_YELLOW: 'second_yellow', // Second yellow = red
};

export const CardType = {
  YELLOW: 'yellow',
  RED: 'red',
};

export class RefereeSystem {
  constructor(eventBus, rng) {
    this.eventBus = eventBus;
    this.rng = rng;
    
    // Referee personality (affects strictness)
    this.strictness = 0.5; // 0 = lenient, 1 = strict
    this.advantageBias = 0.6; // How likely to play advantage
    
    // Advantage tracking
    this.advantageActive = false;
    this.advantageTeam = null;
    this.advantageTimer = 0;
    this.pendingFoul = null;
    
    // Offside tracking
    this.lastPassMoment = null; // Snapshot of positions at moment of pass
    
    // Card tracking per player
    this.playerCards = new Map(); // playerId -> { yellows: 0, red: false }
    
    // VAR
    this.varCheckActive = false;
    this.varCheckTimer = 0;
    this.varDecision = null;
  }

  /**
   * Set referee personality
   */
  setPersonality(strictness = 0.5, advantageBias = 0.6) {
    this.strictness = strictness;
    this.advantageBias = advantageBias;
  }

  /**
   * Evaluate a tackle/contact for foul
   * @param {Object} tackleResult - From BallContact.processTackle
   * @param {Object} tackler - Player who tackled
   * @param {Object} victim - Player who was tackled
   * @param {Object} matchState - Current match state
   * @returns {Object|null} Foul decision or null
   */
  evaluateTackle(tackleResult, tackler, victim, matchState) {
    if (!tackleResult.foul) return null;
    
    const position = victim.position.clone();
    
    // Determine severity
    let severity = FoulSeverity.MINOR;
    
    // From behind = at least yellow
    if (tackleResult.fromBehind) {
      severity = FoulSeverity.YELLOW;
    }
    
    // Denial of obvious goal-scoring opportunity (DOGSO)
    if (this._isDOGSO(victim, matchState)) {
      severity = FoulSeverity.RED;
    }
    
    // Professional foul (stopping promising attack)
    if (this._isPromisingAttack(victim, matchState) && tackleResult.fromBehind) {
      severity = FoulSeverity.YELLOW;
    }
    
    // Strictness modifier
    if (severity === FoulSeverity.MINOR && this.rng.chance(this.strictness * 0.3)) {
      severity = FoulSeverity.YELLOW;
    }
    
    // Check for second yellow
    const cards = this._getPlayerCards(tackler.id);
    if (severity === FoulSeverity.YELLOW && cards.yellows >= 1) {
      severity = FoulSeverity.SECOND_YELLOW;
    }
    
    // Check advantage
    if (this._shouldPlayAdvantage(victim.teamSide, matchState)) {
      this.advantageActive = true;
      this.advantageTeam = victim.teamSide;
      this.advantageTimer = ADVANTAGE_WINDOW;
      this.pendingFoul = { tackler, victim, position, severity };
      return { advantage: true, team: victim.teamSide };
    }
    
    // Issue card
    this._issueCard(tackler, severity);
    
    return {
      advantage: false,
      foul: true,
      position,
      severity,
      tackler,
      victim,
      team: victim.teamSide, // Team that gets the free kick
    };
  }

  /**
   * Update advantage timer
   */
  updateAdvantage(dt, matchState) {
    if (!this.advantageActive) return null;
    
    this.advantageTimer -= dt;
    
    if (this.advantageTimer <= 0) {
      // Advantage expired - bring back foul
      this.advantageActive = false;
      const foul = this.pendingFoul;
      this.pendingFoul = null;
      
      if (foul) {
        this._issueCard(foul.tackler, foul.severity);
        return {
          foul: true,
          position: foul.position,
          severity: foul.severity,
          tackler: foul.tackler,
          victim: foul.victim,
          team: foul.victim.teamSide,
          advantageNotGained: true,
        };
      }
    }
    
    return null;
  }

  /**
   * Cancel advantage (team gained advantage)
   */
  cancelAdvantage() {
    if (this.advantageActive && this.pendingFoul) {
      // Still issue card if warranted
      if (this.pendingFoul.severity !== FoulSeverity.MINOR) {
        this._issueCard(this.pendingFoul.tackler, this.pendingFoul.severity);
      }
    }
    this.advantageActive = false;
    this.pendingFoul = null;
  }

  /**
   * Check offside at moment of pass
   * @param {Object} passer - Player making the pass
   * @param {Object} receiver - Intended receiver
   * @param {Array} allPlayers - All players on pitch
   * @param {string} attackingDirection - 'left' or 'right' (which goal attacking team attacks)
   * @returns {boolean} True if offside
   */
  checkOffside(passer, receiver, allPlayers, attackingDirection) {
    if (receiver.isGoalkeeper()) return false;
    
    // Get defending team players
    const defendingTeam = passer.teamSide === 'home' ? 'away' : 'home';
    const defenders = allPlayers.filter(p => p.teamSide === defendingTeam && p.isActive);
    
    // Find second-last defender position (last = goalkeeper usually)
    let defenderXPositions;
    if (attackingDirection === 'right') {
      // Attacking toward x = PITCH_WIDTH
      defenderXPositions = defenders.map(p => p.position.x).sort((a, b) => b - a);
      const offsideLine = defenderXPositions.length >= 2 ? defenderXPositions[1] : PITCH_WIDTH;
      
      // Receiver must be behind offside line at moment of pass
      const receiverX = receiver.position.x;
      const passerX = passer.position.x;
      
      // Can't be offside in own half
      if (receiverX <= PITCH_WIDTH / 2) return false;
      
      // Must be ahead of ball
      if (receiverX <= passerX) return false;
      
      // Check against offside line (with tolerance)
      return receiverX > offsideLine + OFFSIDE_TOLERANCE;
    } else {
      // Attacking toward x = 0
      defenderXPositions = defenders.map(p => p.position.x).sort((a, b) => a - b);
      const offsideLine = defenderXPositions.length >= 2 ? defenderXPositions[1] : 0;
      
      const receiverX = receiver.position.x;
      const passerX = passer.position.x;
      
      if (receiverX >= PITCH_WIDTH / 2) return false;
      if (receiverX >= passerX) return false;
      
      return receiverX < offsideLine - OFFSIDE_TOLERANCE;
    }
  }

  /**
   * Simulate VAR check
   * @param {string} reason - 'goal', 'penalty', 'red_card'
   * @returns {Object} { checking, duration }
   */
  initiateVAR(reason) {
    this.varCheckActive = true;
    this.varCheckTimer = this.rng.range(15, 45); // 15-45 seconds
    this.varDecision = null;
    
    return {
      checking: true,
      reason,
      duration: this.varCheckTimer,
    };
  }

  /**
   * Update VAR check
   */
  updateVAR(dt) {
    if (!this.varCheckActive) return null;
    
    this.varCheckTimer -= dt;
    if (this.varCheckTimer <= 0) {
      this.varCheckActive = false;
      // 85% chance VAR upholds original decision
      const upheld = this.rng.chance(0.85);
      return { complete: true, upheld };
    }
    return null;
  }

  /**
   * Check if situation is DOGSO (Denial of Obvious Goal-Scoring Opportunity)
   */
  _isDOGSO(victim, matchState) {
    // Simplified: player was through on goal with no defenders between them and goal
    const goalX = victim.teamSide === 'home' ? PITCH_WIDTH : 0;
    const distToGoal = Math.abs(victim.position.x - goalX);
    return distToGoal < 25 && !matchState.advantageActive;
  }

  /**
   * Check if attack was promising
   */
  _isPromisingAttack(victim, matchState) {
    const goalX = victim.teamSide === 'home' ? PITCH_WIDTH : 0;
    const distToGoal = Math.abs(victim.position.x - goalX);
    return distToGoal < 40;
  }

  /**
   * Should referee play advantage?
   */
  _shouldPlayAdvantage(fouledTeam, matchState) {
    if (!matchState.isInPlay()) return false;
    return this.rng.chance(this.advantageBias);
  }

  /**
   * Issue a card to a player
   */
  _issueCard(player, severity) {
    const cards = this._getPlayerCards(player.id);
    
    if (severity === FoulSeverity.YELLOW || severity === FoulSeverity.SECOND_YELLOW) {
      cards.yellows++;
      player.matchStats.yellowCards++;
      
      if (cards.yellows >= 2) {
        cards.red = true;
        player.matchStats.redCards++;
        player.isActive = false; // Sent off
      }
    } else if (severity === FoulSeverity.RED) {
      cards.red = true;
      player.matchStats.redCards++;
      player.isActive = false; // Sent off
    }
  }

  _getPlayerCards(playerId) {
    if (!this.playerCards.has(playerId)) {
      this.playerCards.set(playerId, { yellows: 0, red: false });
    }
    return this.playerCards.get(playerId);
  }
}
