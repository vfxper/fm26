/**
 * FatigueSystem - Calculates player fatigue based on movement, sprints, weather
 */
import {
  FATIGUE_WALK_RATE, FATIGUE_JOG_RATE, FATIGUE_SPRINT_RATE,
  FATIGUE_RECOVERY_RATE, PLAYER_WALK_SPEED, PLAYER_JOG_SPEED,
  ATTR_MAX
} from '../core/Constants.js';
import { PlayerState } from '../entities/Player.js';

export class FatigueSystem {
  constructor() {
    this.heatFactor = 1.0;    // 1.0 normal, 1.3 hot weather
    this.altitudeFactor = 1.0; // 1.0 sea level, 1.2 high altitude
  }

  /**
   * Set environmental factors
   */
  setEnvironment(options = {}) {
    this.heatFactor = options.heat || 1.0;
    this.altitudeFactor = options.altitude || 1.0;
  }

  /**
   * Update fatigue for all players
   * @param {Array} players - All player entities
   * @param {number} dt - Delta time in seconds
   * @param {number} matchMinute - Current match minute
   */
  update(players, dt, matchMinute) {
    const minuteFraction = dt / 60; // Convert dt to fraction of a minute
    
    for (const player of players) {
      if (!player.isActive) continue;
      
      const staminaAttr = player.attributes.stamina;
      const workRate = player.attributes.workRate;
      
      // Base recovery/drain rate modified by stamina attribute
      const staminaFactor = 1 - (staminaAttr / ATTR_MAX) * 0.5; // 0.5-1.0
      const workRateFactor = 0.7 + (workRate / ATTR_MAX) * 0.6; // 0.7-1.3
      
      let drainRate = 0;
      const speed = player.currentSpeed;
      
      if (speed < PLAYER_WALK_SPEED) {
        // Standing/walking: recover stamina
        const recoveryRate = FATIGUE_RECOVERY_RATE * (staminaAttr / ATTR_MAX);
        player.stamina = Math.min(1.0, player.stamina + recoveryRate * minuteFraction);
        continue;
      } else if (speed < PLAYER_JOG_SPEED) {
        drainRate = FATIGUE_JOG_RATE;
      } else {
        drainRate = FATIGUE_SPRINT_RATE;
        player.matchStats.sprints++;
      }
      
      // Apply modifiers
      drainRate *= staminaFactor;
      drainRate *= workRateFactor;
      drainRate *= this.heatFactor;
      drainRate *= this.altitudeFactor;
      
      // Second half fatigue increases
      if (matchMinute > 45) {
        drainRate *= 1.1;
      }
      if (matchMinute > 75) {
        drainRate *= 1.15;
      }
      
      // Apply drain
      player.stamina = Math.max(0, player.stamina - drainRate * minuteFraction);
      
      // Track distance covered
      player.matchStats.distanceCovered += speed * dt;
    }
  }

  /**
   * Get fatigue visual indicator for a player
   * @returns {string} 'fresh', 'normal', 'tired', 'exhausted'
   */
  getFatigueLevel(player) {
    if (player.stamina > 0.75) return 'fresh';
    if (player.stamina > 0.5) return 'normal';
    if (player.stamina > 0.25) return 'tired';
    return 'exhausted';
  }

  /**
   * Check if player should request substitution
   */
  shouldRequestSub(player) {
    return player.stamina < 0.15 && player.attributes.stamina < 12;
  }
}
