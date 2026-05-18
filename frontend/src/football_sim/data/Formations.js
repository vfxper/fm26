/**
 * Formations - Tactical formation templates with player positions
 * Positions are in meters on a 105x68 pitch, relative to attacking direction (left to right)
 */
import { PITCH_WIDTH, PITCH_HEIGHT } from '../core/Constants.js';

const H = PITCH_HEIGHT;
const W = PITCH_WIDTH;

// Position templates: [x, y] where x=0 is own goal line, x=105 is opponent goal
// y=0 is top touchline, y=68 is bottom touchline
export const FORMATIONS = {
  '4-4-2': {
    name: '4-4-2',
    positions: [
      { role: 'GK', x: 5, y: H/2 },
      { role: 'RB', x: 25, y: 8 },
      { role: 'CB', x: 22, y: H/2 - 8 },
      { role: 'CB', x: 22, y: H/2 + 8 },
      { role: 'LB', x: 25, y: H - 8 },
      { role: 'RM', x: 45, y: 10 },
      { role: 'CM', x: 42, y: H/2 - 6 },
      { role: 'CM', x: 42, y: H/2 + 6 },
      { role: 'LM', x: 45, y: H - 10 },
      { role: 'ST', x: 70, y: H/2 - 8 },
      { role: 'ST', x: 70, y: H/2 + 8 },
    ],
  },

  '4-3-3': {
    name: '4-3-3',
    positions: [
      { role: 'GK', x: 5, y: H/2 },
      { role: 'RB', x: 28, y: 8 },
      { role: 'CB', x: 22, y: H/2 - 8 },
      { role: 'CB', x: 22, y: H/2 + 8 },
      { role: 'LB', x: 28, y: H - 8 },
      { role: 'DM', x: 38, y: H/2 },
      { role: 'CM', x: 48, y: H/2 - 10 },
      { role: 'CM', x: 48, y: H/2 + 10 },
      { role: 'RW', x: 72, y: 12 },
      { role: 'ST', x: 75, y: H/2 },
      { role: 'LW', x: 72, y: H - 12 },
    ],
  },

  '4-2-3-1': {
    name: '4-2-3-1',
    positions: [
      { role: 'GK', x: 5, y: H/2 },
      { role: 'RB', x: 28, y: 8 },
      { role: 'CB', x: 22, y: H/2 - 8 },
      { role: 'CB', x: 22, y: H/2 + 8 },
      { role: 'LB', x: 28, y: H - 8 },
      { role: 'DM', x: 38, y: H/2 - 6 },
      { role: 'DM', x: 38, y: H/2 + 6 },
      { role: 'RW', x: 58, y: 12 },
      { role: 'AM', x: 58, y: H/2 },
      { role: 'LW', x: 58, y: H - 12 },
      { role: 'ST', x: 75, y: H/2 },
    ],
  },

  '3-5-2': {
    name: '3-5-2',
    positions: [
      { role: 'GK', x: 5, y: H/2 },
      { role: 'CB', x: 22, y: H/2 - 12 },
      { role: 'CB', x: 20, y: H/2 },
      { role: 'CB', x: 22, y: H/2 + 12 },
      { role: 'RWB', x: 40, y: 6 },
      { role: 'CM', x: 40, y: H/2 - 8 },
      { role: 'DM', x: 36, y: H/2 },
      { role: 'CM', x: 40, y: H/2 + 8 },
      { role: 'LWB', x: 40, y: H - 6 },
      { role: 'ST', x: 70, y: H/2 - 8 },
      { role: 'ST', x: 70, y: H/2 + 8 },
    ],
  },

  '4-1-4-1': {
    name: '4-1-4-1',
    positions: [
      { role: 'GK', x: 5, y: H/2 },
      { role: 'RB', x: 28, y: 8 },
      { role: 'CB', x: 22, y: H/2 - 8 },
      { role: 'CB', x: 22, y: H/2 + 8 },
      { role: 'LB', x: 28, y: H - 8 },
      { role: 'DM', x: 35, y: H/2 },
      { role: 'RM', x: 52, y: 10 },
      { role: 'CM', x: 50, y: H/2 - 6 },
      { role: 'CM', x: 50, y: H/2 + 6 },
      { role: 'LM', x: 52, y: H - 10 },
      { role: 'ST', x: 75, y: H/2 },
    ],
  },

  '5-3-2': {
    name: '5-3-2',
    positions: [
      { role: 'GK', x: 5, y: H/2 },
      { role: 'RWB', x: 30, y: 6 },
      { role: 'CB', x: 20, y: H/2 - 10 },
      { role: 'CB', x: 18, y: H/2 },
      { role: 'CB', x: 20, y: H/2 + 10 },
      { role: 'LWB', x: 30, y: H - 6 },
      { role: 'CM', x: 42, y: H/2 - 8 },
      { role: 'CM', x: 40, y: H/2 },
      { role: 'CM', x: 42, y: H/2 + 8 },
      { role: 'ST', x: 68, y: H/2 - 8 },
      { role: 'ST', x: 68, y: H/2 + 8 },
    ],
  },

  '4-3-2-1': {
    name: '4-3-2-1 (Christmas Tree)',
    positions: [
      { role: 'GK', x: 5, y: H/2 },
      { role: 'RB', x: 28, y: 8 },
      { role: 'CB', x: 22, y: H/2 - 8 },
      { role: 'CB', x: 22, y: H/2 + 8 },
      { role: 'LB', x: 28, y: H - 8 },
      { role: 'DM', x: 36, y: H/2 },
      { role: 'CM', x: 42, y: H/2 - 10 },
      { role: 'CM', x: 42, y: H/2 + 10 },
      { role: 'AM', x: 58, y: H/2 - 8 },
      { role: 'AM', x: 58, y: H/2 + 8 },
      { role: 'ST', x: 75, y: H/2 },
    ],
  },
};

/**
 * Mirror formation for away team (flip x-axis)
 */
export function mirrorFormation(formation) {
  return {
    ...formation,
    positions: formation.positions.map(p => ({
      ...p,
      x: PITCH_WIDTH - p.x,
    })),
  };
}

/**
 * Get formation by name
 */
export function getFormation(name) {
  return FORMATIONS[name] || FORMATIONS['4-4-2'];
}

/**
 * Get all available formation names
 */
export function getFormationNames() {
  return Object.keys(FORMATIONS);
}
