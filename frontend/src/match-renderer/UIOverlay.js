/**
 * UIOverlay - Score display, time, formation overlay
 * 
 * Renders the match HUD including scoreboard, match clock,
 * team names, and formation display.
 * 
 * Task 19.12: Create UI overlay (score, time, formation)
 */

export class UIOverlay {
  /**
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D context
   */
  constructor(ctx) {
    /** @type {CanvasRenderingContext2D} */
    this.ctx = ctx;

    // Match state
    /** @type {string} Home team name */
    this.homeTeamName = 'Home';

    /** @type {string} Away team name */
    this.awayTeamName = 'Away';

    /** @type {number} Home team score */
    this.homeScore = 0;

    /** @type {number} Away team score */
    this.awayScore = 0;

    /** @type {number} Current match minute */
    this.currentMinute = 0;

    /** @type {number} Current match second */
    this.currentSecond = 0;

    /** @type {string} Home team formation (e.g., "4-4-2") */
    this.homeFormation = '';

    /** @type {string} Away team formation (e.g., "4-3-3") */
    this.awayFormation = '';

    /** @type {string} Home team color */
    this.homeColor = '#2563eb';

    /** @type {string} Away team color */
    this.awayColor = '#dc2626';

    /** @type {boolean} Whether match is paused */
    this.isPaused = false;

    /** @type {number} Canvas width */
    this.canvasWidth = 0;

    /** @type {number} Canvas height */
    this.canvasHeight = 0;

    // Celebration overlay state
    /** @type {Object|null} Active celebration */
    this._celebration = null;

    // Event log (recent events shown on screen)
    /** @type {Array<{text: string, time: number, alpha: number}>} */
    this._eventLog = [];

    /** @type {number} Max events to show */
    this._maxEventLog = 3;

    /** @type {number} Event display duration in ms */
    this._eventDisplayDuration = 4000;
  }

  /**
   * Update canvas dimensions
   * @param {number} width
   * @param {number} height
   */
  setCanvasSize(width, height) {
    this.canvasWidth = width;
    this.canvasHeight = height;
  }

  /**
   * Set team information
   * @param {Object} homeTeam - {name, color, formation}
   * @param {Object} awayTeam - {name, color, formation}
   */
  setTeams(homeTeam, awayTeam) {
    this.homeTeamName = homeTeam.name || 'Home';
    this.homeColor = homeTeam.color || '#2563eb';
    this.homeFormation = homeTeam.formation || '';

    this.awayTeamName = awayTeam.name || 'Away';
    this.awayColor = awayTeam.color || '#dc2626';
    this.awayFormation = awayTeam.formation || '';
  }

  /**
   * Update the score
   * @param {number} homeScore
   * @param {number} awayScore
   */
  setScore(homeScore, awayScore) {
    this.homeScore = homeScore;
    this.awayScore = awayScore;
  }

  /**
   * Update match time
   * @param {number} minute
   * @param {number} second
   */
  setTime(minute, second) {
    this.currentMinute = minute;
    this.currentSecond = second;
  }

  /**
   * Set pause state
   * @param {boolean} paused
   */
  setPaused(paused) {
    this.isPaused = paused;
  }

  /**
   * Set celebration state
   * @param {Object|null} celebration - {active, team, progress}
   */
  setCelebration(celebration) {
    this._celebration = celebration;
  }

  /**
   * Add an event to the on-screen log
   * @param {string} text - Event description
   */
  addEvent(text) {
    this._eventLog.unshift({
      text,
      time: performance.now(),
      alpha: 1,
    });

    if (this._eventLog.length > this._maxEventLog) {
      this._eventLog.pop();
    }
  }

  /**
   * Draw the complete UI overlay
   */
  draw() {
    this._drawScoreboard();
    this._drawFormations();
    this._drawEventLog();

    if (this.isPaused) {
      this._drawPauseIndicator();
    }

    if (this._celebration && this._celebration.active) {
      this._drawCelebration();
    }
  }

  /**
   * Draw the scoreboard at the top center
   * @private
   */
  _drawScoreboard() {
    const ctx = this.ctx;
    const centerX = this.canvasWidth / 2;
    const y = 8;

    // Scoreboard dimensions
    const totalWidth = 280;
    const height = 50;
    const x = centerX - totalWidth / 2;

    // Background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.8)';
    this._roundRect(x, y, totalWidth, height, 6);
    ctx.fill();

    // Home team name (left)
    ctx.fillStyle = this.homeColor;
    ctx.font = 'bold 11px Arial, sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    const nameY = y + 18;
    ctx.fillText(this._truncateName(this.homeTeamName, 12), centerX - 40, nameY);

    // Away team name (right)
    ctx.fillStyle = this.awayColor;
    ctx.textAlign = 'left';
    ctx.fillText(this._truncateName(this.awayTeamName, 12), centerX + 40, nameY);

    // Score
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 20px Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${this.homeScore} - ${this.awayScore}`, centerX, nameY);

    // Match time
    ctx.font = '12px Arial, sans-serif';
    ctx.fillStyle = '#aaaaaa';
    const timeStr = `${this.currentMinute}'`;
    ctx.fillText(timeStr, centerX, y + 40);
  }

  /**
   * Draw formation labels
   * @private
   */
  _drawFormations() {
    if (!this.homeFormation && !this.awayFormation) return;

    const ctx = this.ctx;
    const y = 66;

    // Home formation (left side)
    if (this.homeFormation) {
      ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
      ctx.font = '10px Arial, sans-serif';
      ctx.textAlign = 'left';

      const padding = 4;
      const text = this.homeFormation;
      const metrics = ctx.measureText(text);
      const bgWidth = metrics.width + padding * 2;
      const bgHeight = 16;

      ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
      this._roundRect(8, y, bgWidth, bgHeight, 3);
      ctx.fill();

      ctx.fillStyle = this.homeColor;
      ctx.textBaseline = 'middle';
      ctx.fillText(text, 8 + padding, y + bgHeight / 2);
    }

    // Away formation (right side)
    if (this.awayFormation) {
      ctx.font = '10px Arial, sans-serif';
      ctx.textAlign = 'right';

      const padding = 4;
      const text = this.awayFormation;
      const metrics = ctx.measureText(text);
      const bgWidth = metrics.width + padding * 2;
      const bgHeight = 16;

      ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
      this._roundRect(this.canvasWidth - 8 - bgWidth, y, bgWidth, bgHeight, 3);
      ctx.fill();

      ctx.fillStyle = this.awayColor;
      ctx.textBaseline = 'middle';
      ctx.textAlign = 'left';
      ctx.fillText(text, this.canvasWidth - 8 - bgWidth + padding, y + bgHeight / 2);
    }
  }

  /**
   * Draw recent event log
   * @private
   */
  _drawEventLog() {
    const ctx = this.ctx;
    const now = performance.now();
    const x = 10;
    let y = this.canvasHeight - 20;

    for (let i = 0; i < this._eventLog.length; i++) {
      const event = this._eventLog[i];
      const elapsed = now - event.time;

      if (elapsed > this._eventDisplayDuration) {
        this._eventLog.splice(i, 1);
        i--;
        continue;
      }

      // Fade out in last second
      const fadeStart = this._eventDisplayDuration - 1000;
      if (elapsed > fadeStart) {
        event.alpha = 1 - (elapsed - fadeStart) / 1000;
      }

      ctx.globalAlpha = event.alpha;
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      ctx.font = '11px Arial, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'bottom';

      const metrics = ctx.measureText(event.text);
      const padding = 4;
      this._roundRect(x, y - 14, metrics.width + padding * 2, 18, 3);
      ctx.fill();

      ctx.fillStyle = '#ffffff';
      ctx.fillText(event.text, x + padding, y);

      y -= 22;
      ctx.globalAlpha = 1;
    }
  }

  /**
   * Draw pause indicator
   * @private
   */
  _drawPauseIndicator() {
    const ctx = this.ctx;
    const centerX = this.canvasWidth / 2;
    const centerY = this.canvasHeight / 2;

    // Semi-transparent overlay
    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);

    // Pause icon (two bars)
    const barWidth = 12;
    const barHeight = 40;
    const gap = 10;

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(centerX - gap - barWidth, centerY - barHeight / 2, barWidth, barHeight);
    ctx.fillRect(centerX + gap, centerY - barHeight / 2, barWidth, barHeight);

    // "PAUSED" text
    ctx.font = 'bold 18px Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText('PAUSED', centerX, centerY + barHeight / 2 + 10);
  }

  /**
   * Draw goal celebration overlay
   * @private
   */
  _drawCelebration() {
    const ctx = this.ctx;
    const celebration = this._celebration;
    const progress = celebration.progress || 0;
    const centerX = this.canvasWidth / 2;
    const centerY = this.canvasHeight / 2;

    // Flash effect (fades in then out)
    const flashAlpha = progress < 0.2
      ? progress / 0.2 * 0.3
      : Math.max(0, 0.3 * (1 - (progress - 0.2) / 0.8));

    const teamColor = celebration.team === 'home' ? this.homeColor : this.awayColor;

    ctx.fillStyle = teamColor;
    ctx.globalAlpha = flashAlpha;
    ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
    ctx.globalAlpha = 1;

    // "GOAL!" text with scale animation
    if (progress < 0.8) {
      const textProgress = Math.min(1, progress / 0.3);
      const scale = 0.5 + textProgress * 0.5;
      const alpha = progress < 0.6 ? 1 : 1 - (progress - 0.6) / 0.2;

      ctx.save();
      ctx.translate(centerX, centerY - 20);
      ctx.scale(scale, scale);
      ctx.globalAlpha = alpha;
      ctx.font = 'bold 48px Arial, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Text shadow
      ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
      ctx.fillText('GOAL!', 2, 2);

      // Text
      ctx.fillStyle = '#ffffff';
      ctx.fillText('GOAL!', 0, 0);

      ctx.restore();
      ctx.globalAlpha = 1;
    }
  }

  /**
   * Draw a rounded rectangle path
   * @param {number} x
   * @param {number} y
   * @param {number} width
   * @param {number} height
   * @param {number} radius
   * @private
   */
  _roundRect(x, y, width, height, radius) {
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
  }

  /**
   * Truncate a name to fit
   * @param {string} name
   * @param {number} maxLen
   * @returns {string}
   * @private
   */
  _truncateName(name, maxLen) {
    if (name.length <= maxLen) return name;
    return name.substring(0, maxLen - 1) + '…';
  }
}
