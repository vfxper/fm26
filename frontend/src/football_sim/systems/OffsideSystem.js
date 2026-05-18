/**
 * OffsideSystem - Dedicated offside detection with linesman simulation
 * Tracks player positions at moment of pass, handles marginal calls
 */
import { PITCH_WIDTH, PITCH_HEIGHT, OFFSIDE_TOLERANCE } from '../core/Constants.js';

export class OffsideSystem {
  constructor(rng) {
    this.rng = rng;
    
    // Snapshot of positions at moment of last forward pass
    this.passSnapshot = null;
    
    // Linesman accuracy (can miss tight calls)
    this.linesmanAccuracy = 0.92; // 92% correct on tight calls
    
    // Delayed flag (linesman waits to see if pass is completed)
    this.pendingOffside = null;
    this.pendingTimer = 0;
  }

  /**
   * Take snapshot of all player positions at moment of pass
   * @param {Object} passer - Player making the pass
   * @param {Array} allPlayers - All active players
   * @param {Object} ball - Ball entity
   */
  snapshotAtPass(passer, allPlayers, ball) {
    this.passSnapshot = {
      passerTeam: passer.teamSide,
      passerPos: passer.position.clone(),
      ballPos: ball.position.clone(),
      players: allPlayers.map(p => ({
        id: p.id,
        team: p.teamSide,
        x: p.position.x,
        y: p.position.y,
        isGK: p.isGoalkeeper(),
      })),
    };
  }

  /**
   * Check if receiver was offside at moment of pass
   * @param {Object} receiver - Player receiving the ball
   * @param {string} attackingDirection - 'right' (home attacks right goal) or 'left'
   * @returns {Object} { offside, marginal, position }
   */
  checkReceiver(receiver, attackingDirection) {
    if (!this.passSnapshot) return { offside: false };
    if (receiver.teamSide !== this.passSnapshot.passerTeam) return { offside: false };
    if (receiver.isGoalkeeper()) return { offside: false };
    
    // Find receiver's position at moment of pass
    const receiverSnapshot = this.passSnapshot.players.find(p => p.id === receiver.id);
    if (!receiverSnapshot) return { offside: false };
    
    // Find defending team's players
    const defendingTeam = this.passSnapshot.passerTeam === 'home' ? 'away' : 'home';
    const defenders = this.passSnapshot.players
      .filter(p => p.team === defendingTeam)
      .map(p => p.x);
    
    // Can't be offside in own half
    const halfwayLine = PITCH_WIDTH / 2;
    
    if (attackingDirection === 'right') {
      // Attacking toward x = PITCH_WIDTH
      if (receiverSnapshot.x <= halfwayLine) return { offside: false };
      
      // Must be ahead of ball at moment of pass
      if (receiverSnapshot.x <= this.passSnapshot.ballPos.x) return { offside: false };
      
      // Find second-last defender (sorted by x descending)
      defenders.sort((a, b) => b - a);
      const offsideLine = defenders.length >= 2 ? defenders[1] : PITCH_WIDTH;
      
      const margin = receiverSnapshot.x - offsideLine;
      
      if (margin > OFFSIDE_TOLERANCE) {
        // Clear offside
        return { offside: true, marginal: false, margin, position: receiverSnapshot };
      } else if (margin > 0) {
        // Marginal - linesman might miss it
        const correct = this.rng.chance(this.linesmanAccuracy);
        return { offside: correct, marginal: true, margin, position: receiverSnapshot };
      }
      
      return { offside: false };
    } else {
      // Attacking toward x = 0
      if (receiverSnapshot.x >= halfwayLine) return { offside: false };
      if (receiverSnapshot.x >= this.passSnapshot.ballPos.x) return { offside: false };
      
      defenders.sort((a, b) => a - b);
      const offsideLine = defenders.length >= 2 ? defenders[1] : 0;
      
      const margin = offsideLine - receiverSnapshot.x;
      
      if (margin > OFFSIDE_TOLERANCE) {
        return { offside: true, marginal: false, margin, position: receiverSnapshot };
      } else if (margin > 0) {
        const correct = this.rng.chance(this.linesmanAccuracy);
        return { offside: correct, marginal: true, margin, position: receiverSnapshot };
      }
      
      return { offside: false };
    }
  }

  /**
   * Clear snapshot (ball changes possession, etc.)
   */
  clearSnapshot() {
    this.passSnapshot = null;
    this.pendingOffside = null;
  }
}
