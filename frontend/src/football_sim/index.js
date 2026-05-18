/**
 * Football Simulation - Main entry point
 * Ties together all systems: physics, AI, animation, rendering
 * 
 * Usage:
 *   const sim = new FootballSimulation(canvasElement, { homeTeam, awayTeam, weather, seed });
 *   sim.start();
 */
export { FootballSimulation } from './FootballSimulation.js';
export { Engine, SeededRandom } from './core/Engine.js';
export { Vector2 } from './core/Vector2.js';
export { MatchState, MatchPhase, BallOwnership, PlayState } from './core/MatchState.js';
export { FORMATIONS, getFormation, mirrorFormation } from './data/Formations.js';
export { TEAM_TEMPLATES, getTeamTemplate } from './data/TeamTemplates.js';
export { WeatherType, TimeOfDay } from './systems/WeatherSystem.js';
