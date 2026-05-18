/**
 * PlaybackControls - Speed controls and pause/resume functionality
 * 
 * Provides UI controls for match playback speed (1x, 2x, 4x, instant)
 * and pause/resume functionality.
 * 
 * Task 19.13: Implement playback speed controls (1x, 2x, 4x, instant)
 * Task 19.14: Create pause/resume functionality
 */

export class PlaybackControls {
  /**
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D context
   */
  constructor(ctx) {
    /** @type {CanvasRenderingContext2D} */
    this.ctx = ctx;

    /** @type {number} Current playback speed (1, 2, 4, or 0 for instant) */
    this.speed = 1;

    /** @type {boolean} Whether playback is paused */
    this.isPaused = false;

    /** @type {number} Canvas width */
    this.canvasWidth = 0;

    /** @type {number} Canvas height */
    this.canvasHeight = 0;

    // Available speed options
    /** @type {Array<{value: number, label: string}>} */
    this.speedOptions = [
      { value: 1, label: '1x' },
      { value: 2, label: '2x' },
      { value: 4, label: '4x' },
      { value: 0, label: '⏩' }, // Instant
    ];

    // Button layout
    /** @type {number} Button width */
    this._buttonWidth = 36;

    /** @type {number} Button height */
    this._buttonHeight = 28;

    /** @type {number} Gap between buttons */
    this._buttonGap = 4;

    /** @type {number} Pause button width */
    this._pauseButtonWidth = 36;

    // Callbacks
    /** @type {Function|null} Called when speed changes */
    this.onSpeedChange = null;

    /** @type {Function|null} Called when pause state changes */
    this.onPauseChange = null;

    // Hit areas for click detection
    /** @type {Array<{x: number, y: number, w: number, h: number, action: string, value: any}>} */
    this._hitAreas = [];
  }

  /**
   * Update canvas dimensions
   * @param {number} width
   * @param {number} height
   */
  setCanvasSize(width, height) {
    this.canvasWidth = width;
    this.canvasHeight = height;
    this._calculateHitAreas();
  }

  /**
   * Set playback speed
   * @param {number} speed - 1, 2, 4, or 0 for instant
   */
  setSpeed(speed) {
    this.speed = speed;
    if (this.onSpeedChange) {
      this.onSpeedChange(speed);
    }
  }

  /**
   * Toggle pause state
   */
  togglePause() {
    this.isPaused = !this.isPaused;
    if (this.onPauseChange) {
      this.onPauseChange(this.isPaused);
    }
  }

  /**
   * Set pause state directly
   * @param {boolean} paused
   */
  setPaused(paused) {
    this.isPaused = paused;
    if (this.onPauseChange) {
      this.onPauseChange(this.isPaused);
    }
  }

  /**
   * Handle a click/tap event on the canvas
   * @param {number} x - Click X position (canvas coordinates)
   * @param {number} y - Click Y position (canvas coordinates)
   * @returns {boolean} True if a control was clicked
   */
  handleClick(x, y) {
    for (const area of this._hitAreas) {
      if (
        x >= area.x &&
        x <= area.x + area.w &&
        y >= area.y &&
        y <= area.y + area.h
      ) {
        if (area.action === 'speed') {
          this.setSpeed(area.value);
        } else if (area.action === 'pause') {
          this.togglePause();
        }
        return true;
      }
    }
    return false;
  }

  /**
   * Calculate hit areas for buttons
   * @private
   */
  _calculateHitAreas() {
    this._hitAreas = [];

    const totalSpeedWidth =
      this.speedOptions.length * this._buttonWidth +
      (this.speedOptions.length - 1) * this._buttonGap;
    const totalWidth = totalSpeedWidth + this._buttonGap + this._pauseButtonWidth;
    const startX = (this.canvasWidth - totalWidth) / 2;
    const y = this.canvasHeight - this._buttonHeight - 12;

    // Speed buttons
    for (let i = 0; i < this.speedOptions.length; i++) {
      const x = startX + i * (this._buttonWidth + this._buttonGap);
      this._hitAreas.push({
        x,
        y,
        w: this._buttonWidth,
        h: this._buttonHeight,
        action: 'speed',
        value: this.speedOptions[i].value,
        label: this.speedOptions[i].label,
      });
    }

    // Pause button
    const pauseX = startX + totalSpeedWidth + this._buttonGap;
    this._hitAreas.push({
      x: pauseX,
      y,
      w: this._pauseButtonWidth,
      h: this._buttonHeight,
      action: 'pause',
      value: null,
      label: '⏸',
    });
  }

  /**
   * Draw the playback controls
   */
  draw() {
    const ctx = this.ctx;

    for (const area of this._hitAreas) {
      const isActive =
        (area.action === 'speed' && area.value === this.speed) ||
        (area.action === 'pause' && this.isPaused);

      // Button background
      ctx.fillStyle = isActive ? 'rgba(255, 255, 255, 0.9)' : 'rgba(0, 0, 0, 0.7)';
      this._roundRect(area.x, area.y, area.w, area.h, 4);
      ctx.fill();

      // Button border
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Button label
      ctx.fillStyle = isActive ? '#000000' : '#ffffff';
      ctx.font = 'bold 11px Arial, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      let label = area.label;
      if (area.action === 'pause') {
        label = this.isPaused ? '▶' : '⏸';
      }

      ctx.fillText(label, area.x + area.w / 2, area.y + area.h / 2);
    }
  }

  /**
   * Draw a rounded rectangle path
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
}
