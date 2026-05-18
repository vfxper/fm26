/**
 * PlayerRenderer - Renders player sprites as colored circles with squad numbers
 * 
 * Home team = blue circles, Away team = red circles.
 * Each player has a white number displayed in the center.
 * 
 * Task 19.4: Create player sprite rendering (colored circles with numbers)
 */

export class PlayerRenderer {
  /**
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D context
   * @param {import('./PitchRenderer.js').PitchRenderer} pitchRenderer - For coordinate conversion
   */
  constructor(ctx, pitchRenderer) {
    /** @type {CanvasRenderingContext2D} */
    this.ctx = ctx;

    /** @type {import('./PitchRenderer.js').PitchRenderer} */
    this.pitchRenderer = pitchRenderer;

    // Player appearance settings
    /** @type {number} Player circle radius in pixels */
    this.playerRadius = 12;

    /** @type {string} Home team primary color */
    this.homeColor = '#2563eb'; // Blue

    /** @type {string} Away team primary color */
    this.awayColor = '#dc2626'; // Red

    /** @type {string} Home team outline color */
    this.homeOutlineColor = '#1d4ed8';

    /** @type {string} Away team outline color */
    this.awayOutlineColor = '#b91c1c';

    /** @type {string} Number text color */
    this.numberColor = '#ffffff';

    /** @type {string} Font for player numbers */
    this.numberFont = 'bold 10px Arial, sans-serif';

    /** @type {string} Font for player names (shown below) */
    this.nameFont = '8px Arial, sans-serif';

    /** @type {boolean} Whether to show player names */
    this.showNames = false;

    /** @type {Map<number, Object>} Player state map: id -> {x, y, team, number, name, highlighted} */
    this.players = new Map();

    /** @type {Set<number>} Set of highlighted player IDs (for active events) */
    this.highlightedPlayers = new Set();
  }

  /**
   * Set team colors
   * @param {string} homeColor - Home team color (hex)
   * @param {string} awayColor - Away team color (hex)
   */
  setTeamColors(homeColor, awayColor) {
    this.homeColor = homeColor || '#2563eb';
    this.awayColor = awayColor || '#dc2626';
  }

  /**
   * Initialize players from match data
   * @param {Array} homePlayers - Array of {id, number, name, x, y}
   * @param {Array} awayPlayers - Array of {id, number, name, x, y}
   */
  initializePlayers(homePlayers, awayPlayers) {
    this.players.clear();

    for (const p of homePlayers) {
      this.players.set(p.id, {
        x: p.x,
        y: p.y,
        team: 'home',
        number: p.number,
        name: p.name || '',
        targetX: p.x,
        targetY: p.y,
      });
    }

    for (const p of awayPlayers) {
      this.players.set(p.id, {
        x: p.x,
        y: p.y,
        team: 'away',
        number: p.number,
        name: p.name || '',
        targetX: p.x,
        targetY: p.y,
      });
    }
  }

  /**
   * Update a player's position
   * @param {number} playerId - Player ID
   * @param {number} x - New X position (pitch coords)
   * @param {number} y - New Y position (pitch coords)
   */
  setPlayerPosition(playerId, x, y) {
    const player = this.players.get(playerId);
    if (player) {
      player.x = x;
      player.y = y;
    }
  }

  /**
   * Set a player's target position for interpolation
   * @param {number} playerId - Player ID
   * @param {number} targetX - Target X position
   * @param {number} targetY - Target Y position
   */
  setPlayerTarget(playerId, targetX, targetY) {
    const player = this.players.get(playerId);
    if (player) {
      player.targetX = targetX;
      player.targetY = targetY;
    }
  }

  /**
   * Highlight a player (e.g., during an event)
   * @param {number} playerId - Player ID to highlight
   */
  highlightPlayer(playerId) {
    this.highlightedPlayers.add(playerId);
  }

  /**
   * Remove highlight from a player
   * @param {number} playerId - Player ID
   */
  unhighlightPlayer(playerId) {
    this.highlightedPlayers.delete(playerId);
  }

  /**
   * Clear all highlights
   */
  clearHighlights() {
    this.highlightedPlayers.clear();
  }

  /**
   * Get a player's current position
   * @param {number} playerId
   * @returns {{x: number, y: number}|null}
   */
  getPlayerPosition(playerId) {
    const player = this.players.get(playerId);
    if (!player) return null;
    return { x: player.x, y: player.y };
  }

  /**
   * Draw all players on the canvas
   */
  draw() {
    const ctx = this.ctx;

    this.players.forEach((player, playerId) => {
      const { x, y } = this.pitchRenderer.pitchToCanvas(player.x, player.y);
      const isHighlighted = this.highlightedPlayers.has(playerId);
      const radius = isHighlighted ? this.playerRadius + 3 : this.playerRadius;

      // Draw highlight glow
      if (isHighlighted) {
        ctx.save();
        ctx.shadowColor = player.team === 'home' ? this.homeColor : this.awayColor;
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(x, y, radius + 2, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.fill();
        ctx.restore();
      }

      // Draw player circle with gradient
      const gradient = ctx.createRadialGradient(
        x - radius * 0.3, y - radius * 0.3, 0,
        x, y, radius
      );
      if (player.team === 'home') {
        gradient.addColorStop(0, this._lightenColor(this.homeColor, 30));
        gradient.addColorStop(1, this.homeColor);
      } else {
        gradient.addColorStop(0, this._lightenColor(this.awayColor, 30));
        gradient.addColorStop(1, this.awayColor);
      }

      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = gradient;
      ctx.fill();

      // Draw outline
      ctx.strokeStyle = player.team === 'home' ? this.homeOutlineColor : this.awayOutlineColor;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw squad number
      ctx.fillStyle = this.numberColor;
      ctx.font = this.numberFont;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(player.number), x, y);

      // Draw player name below (if enabled)
      if (this.showNames && player.name) {
        ctx.font = this.nameFont;
        ctx.fillStyle = '#ffffff';
        ctx.fillText(player.name, x, y + radius + 10);
      }
    });
  }

  /**
   * Lighten a hex color by a percentage
   * @param {string} color - Hex color string
   * @param {number} percent - Percentage to lighten (0-100)
   * @returns {string} Lightened hex color
   * @private
   */
  _lightenColor(color, percent) {
    const num = parseInt(color.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.min(255, (num >> 16) + amt);
    const G = Math.min(255, ((num >> 8) & 0x00ff) + amt);
    const B = Math.min(255, (num & 0x0000ff) + amt);
    return `#${(0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)}`;
  }
}
