/**
 * TeamTemplates - Demo team data for standalone simulation
 * Used when no backend data is available (demo mode)
 */

export const TEAM_TEMPLATES = {
  real_madrid: {
    name: 'Real Madrid',
    shortName: 'RMA',
    color: '#e0e0ff',
    secondaryColor: '#febe10',
    formation: '4-3-3',
    players: [
      { name: 'Courtois', number: 1, position: 'GK', attributes: { reflexes: 18, handling: 17, positioning: 17, oneOnOnes: 16, commandOfArea: 15, pace: 10, passing: 12, technique: 10 } },
      { name: 'Carvajal', number: 2, position: 'RB', attributes: { pace: 15, acceleration: 14, stamina: 16, tackling: 15, marking: 14, crossing: 16, passing: 14, positioning: 15, workRate: 17, decisions: 15 } },
      { name: 'Rüdiger', number: 22, position: 'CB', attributes: { pace: 15, strength: 17, tackling: 16, marking: 16, heading: 15, positioning: 16, composure: 15, anticipation: 15, concentration: 15 } },
      { name: 'Militão', number: 3, position: 'CB', attributes: { pace: 16, strength: 16, tackling: 15, marking: 15, heading: 14, positioning: 14, composure: 14, anticipation: 14, agility: 15 } },
      { name: 'Mendy', number: 23, position: 'LB', attributes: { pace: 16, acceleration: 16, stamina: 15, tackling: 14, marking: 14, crossing: 12, passing: 12, positioning: 14, workRate: 15, strength: 15 } },
      { name: 'Tchouaméni', number: 18, position: 'DM', attributes: { pace: 14, stamina: 16, tackling: 16, passing: 15, vision: 14, positioning: 16, strength: 16, workRate: 16, decisions: 15, composure: 15 } },
      { name: 'Valverde', number: 15, position: 'CM', attributes: { pace: 17, acceleration: 16, stamina: 18, passing: 15, shooting: 14, dribbling: 14, tackling: 14, workRate: 19, decisions: 14, technique: 14 } },
      { name: 'Bellingham', number: 5, position: 'CM', attributes: { pace: 15, acceleration: 15, stamina: 16, passing: 16, shooting: 16, dribbling: 16, vision: 16, decisions: 16, composure: 17, technique: 16, flair: 15 } },
      { name: 'Rodrygo', number: 11, position: 'RW', attributes: { pace: 17, acceleration: 17, dribbling: 16, technique: 16, shooting: 15, passing: 14, flair: 16, composure: 15, agility: 17 } },
      { name: 'Vinícius Jr', number: 7, position: 'LW', attributes: { pace: 19, acceleration: 19, dribbling: 18, technique: 16, shooting: 15, flair: 19, agility: 18, composure: 14, crossing: 14 } },
      { name: 'Mbappé', number: 9, position: 'ST', attributes: { pace: 20, acceleration: 20, shooting: 18, dribbling: 17, technique: 16, composure: 17, flair: 17, positioning: 18, finishing: 19 } },
    ],
  },

  manchester_city: {
    name: 'Manchester City',
    shortName: 'MCI',
    color: '#5bb8f0',
    secondaryColor: '#1c2c5b',
    formation: '4-3-3',
    players: [
      { name: 'Ederson', number: 31, position: 'GK', attributes: { reflexes: 16, handling: 15, positioning: 16, oneOnOnes: 15, commandOfArea: 14, pace: 13, passing: 17, technique: 14 } },
      { name: 'Walker', number: 2, position: 'RB', attributes: { pace: 18, acceleration: 17, stamina: 16, tackling: 14, marking: 14, crossing: 13, passing: 13, positioning: 14, workRate: 15, strength: 15 } },
      { name: 'Dias', number: 3, position: 'CB', attributes: { pace: 13, strength: 16, tackling: 17, marking: 17, heading: 15, positioning: 17, composure: 17, anticipation: 17, concentration: 18 } },
      { name: 'Stones', number: 5, position: 'CB', attributes: { pace: 14, strength: 15, tackling: 15, marking: 15, heading: 14, positioning: 16, composure: 16, passing: 16, technique: 15 } },
      { name: 'Gvardiol', number: 24, position: 'LB', attributes: { pace: 15, acceleration: 15, stamina: 15, tackling: 16, marking: 15, crossing: 13, passing: 14, positioning: 15, strength: 16 } },
      { name: 'Rodri', number: 16, position: 'DM', attributes: { pace: 12, stamina: 16, tackling: 16, passing: 18, vision: 17, positioning: 18, strength: 16, workRate: 15, decisions: 18, composure: 18, technique: 16 } },
      { name: 'De Bruyne', number: 17, position: 'CM', attributes: { pace: 14, passing: 19, vision: 20, shooting: 17, crossing: 18, technique: 17, decisions: 18, composure: 17, flair: 17, dribbling: 15 } },
      { name: 'Foden', number: 47, position: 'CM', attributes: { pace: 16, acceleration: 16, dribbling: 17, technique: 17, shooting: 16, passing: 16, vision: 16, flair: 17, agility: 17, composure: 15 } },
      { name: 'Doku', number: 11, position: 'RW', attributes: { pace: 18, acceleration: 18, dribbling: 17, technique: 15, flair: 16, agility: 17, crossing: 14, shooting: 13 } },
      { name: 'Haaland', number: 9, position: 'ST', attributes: { pace: 17, acceleration: 16, shooting: 19, heading: 16, strength: 18, composure: 17, positioning: 18, finishing: 19, technique: 14 } },
      { name: 'Grealish', number: 10, position: 'LW', attributes: { pace: 15, dribbling: 17, technique: 17, flair: 17, agility: 16, passing: 15, vision: 14, composure: 15, crossing: 14 } },
    ],
  },
};

/**
 * Get team template by key
 */
export function getTeamTemplate(key) {
  return TEAM_TEMPLATES[key] || TEAM_TEMPLATES.real_madrid;
}

/**
 * Get all available team keys
 */
export function getTeamKeys() {
  return Object.keys(TEAM_TEMPLATES);
}
