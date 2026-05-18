/**
 * InjurySystem - Handles match injuries from tackles, collisions, fatigue
 */

export const InjuryType = {
  MUSCLE_STRAIN: 'muscle_strain',
  HAMSTRING: 'hamstring',
  ANKLE_SPRAIN: 'ankle_sprain',
  KNEE_LIGAMENT: 'knee_ligament',
  CONCUSSION: 'concussion',
  BRUISE: 'bruise',
  CRAMP: 'cramp',
};

export const InjurySeverity = {
  MINOR: 'minor',       // Can continue, slight penalty
  MODERATE: 'moderate', // Should be substituted
  SEVERE: 'severe',     // Must be substituted, long recovery
};

export class InjurySystem {
  constructor(eventBus, rng) {
    this.eventBus = eventBus;
    this.rng = rng;
    
    // Injury events this match
    this.injuries = [];
    
    // Base injury probability per minute
    this.baseInjuryRate = 0.001; // ~0.1% per minute per player
  }

  /**
   * Check for random injury during play
   * @param {Object} player - Player entity
   * @param {number} matchMinute - Current minute
   * @returns {Object|null} Injury event or null
   */
  checkRandomInjury(player, matchMinute) {
    if (!player.isActive) return null;
    
    // Factors that increase injury risk
    let risk = this.baseInjuryRate;
    
    // Fatigue increases risk significantly
    if (player.stamina < 0.3) risk *= 3;
    else if (player.stamina < 0.5) risk *= 1.5;
    
    // Sprinting increases risk
    if (player.state === 'sprinting') risk *= 2;
    
    // Late in match = higher risk
    if (matchMinute > 75) risk *= 1.5;
    
    // Low natural fitness increases risk
    const naturalFitness = player.attributes.stamina;
    if (naturalFitness < 10) risk *= 1.5;
    
    if (this.rng.chance(risk)) {
      return this._generateInjury(player, 'random', matchMinute);
    }
    
    return null;
  }

  /**
   * Check for injury from tackle/collision
   * @param {Object} player - Injured player
   * @param {number} impactForce - Force of impact (0-1)
   * @param {string} cause - 'tackle', 'collision', 'landing'
   * @param {number} matchMinute - Current minute
   * @returns {Object|null} Injury event or null
   */
  checkContactInjury(player, impactForce, cause, matchMinute) {
    // Higher impact = higher chance
    let chance = impactForce * 0.3;
    
    // Fatigue makes injuries more likely
    if (player.stamina < 0.4) chance *= 1.5;
    
    if (this.rng.chance(chance)) {
      return this._generateInjury(player, cause, matchMinute);
    }
    
    return null;
  }

  /**
   * Generate an injury
   */
  _generateInjury(player, cause, matchMinute) {
    // Determine type based on cause
    let type, severity;
    const roll = this.rng.next();
    
    if (cause === 'tackle') {
      if (roll < 0.3) { type = InjuryType.ANKLE_SPRAIN; severity = InjurySeverity.MODERATE; }
      else if (roll < 0.5) { type = InjuryType.BRUISE; severity = InjurySeverity.MINOR; }
      else if (roll < 0.7) { type = InjuryType.MUSCLE_STRAIN; severity = InjurySeverity.MINOR; }
      else if (roll < 0.9) { type = InjuryType.HAMSTRING; severity = InjurySeverity.MODERATE; }
      else { type = InjuryType.KNEE_LIGAMENT; severity = InjurySeverity.SEVERE; }
    } else if (cause === 'random') {
      if (roll < 0.4) { type = InjuryType.CRAMP; severity = InjurySeverity.MINOR; }
      else if (roll < 0.7) { type = InjuryType.MUSCLE_STRAIN; severity = InjurySeverity.MINOR; }
      else if (roll < 0.9) { type = InjuryType.HAMSTRING; severity = InjurySeverity.MODERATE; }
      else { type = InjuryType.MUSCLE_STRAIN; severity = InjurySeverity.MODERATE; }
    } else {
      if (roll < 0.5) { type = InjuryType.BRUISE; severity = InjurySeverity.MINOR; }
      else if (roll < 0.8) { type = InjuryType.MUSCLE_STRAIN; severity = InjurySeverity.MODERATE; }
      else { type = InjuryType.CONCUSSION; severity = InjurySeverity.SEVERE; }
    }
    
    const injury = {
      player,
      playerId: player.id,
      type,
      severity,
      cause,
      minute: matchMinute,
      canContinue: severity === InjurySeverity.MINOR,
      speedPenalty: severity === InjurySeverity.MINOR ? 0.1 : 0.3,
    };
    
    this.injuries.push(injury);
    
    // Apply immediate effects
    if (severity === InjurySeverity.MINOR) {
      // Player can continue but with reduced speed
      player.stamina = Math.max(0.2, player.stamina - 0.1);
    } else {
      // Player should be substituted
      player.state = 'injured';
    }
    
    return injury;
  }

  /**
   * Get all injuries this match
   */
  getInjuries() {
    return this.injuries;
  }

  /**
   * Reset for new match
   */
  reset() {
    this.injuries = [];
  }
}
