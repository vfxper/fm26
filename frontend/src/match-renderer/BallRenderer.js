/**
 * BallRenderer - Renders the ball with position tracking and shadow
 * 
 * The ball is rendered as a small white circle with a dark outline
 * and a subtle shadow for depth.
 * 
 * Task 19.5: Implement ball rendering
 */

export class BallRenderer {
  /**
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D context
   * @param {import('./PitchRenderer.js').PitchRenderer} pitchRenderer - For coordinate conversion
   */
  constructor(ctx, pitchRenderer) {
    /** @type {CanvasRenderingContext2D} */
    this.ctx = ctx;

    /** @type {import('./PitchRenderer.js').PitchRenderer} */
    this.pitchRenderer = pitchRenderer;

    // Ball state
    /** @type {number} Ball X position (pitch coordinates) */
    this.x = 52.5;

    /** @type {number} Ball Y position (pitch coordinates) */
    this.y = 34;

    /** @type {number} Ball target X for animation */
    this.targetX = 52.5;

    /** @type {number} Ball target Y for animation */
    this.targetY = 34;

    // Ball appearance
    /** @type {number} Ball radius in pixels */
    this.radius = 5;

    /** @type {string} Ball fill color */
    this.color = '#ffffff';

    /** @type {string} Ball outline color */
    this.outlineColor = '#333333';

    /** @type {number} Ball outline width */
    this.outlineWidth = 1.5;

    /** @type {string} Shadow color */
    this.shadowColor = 'rgba(0, 0, 0, 0.4)';

    /** @type {number} Shadow offset X */
    this.shadowOffsetX = 2;

    /** @type {number} Shadow offset Y */
    this.shadowOffsetY = 2;

    /** @type {number} Shadow blur radius */
    this.shadowBlur = 4;

    /** @type {boolean} Whether ball is visible */
    this.visible = true;

    /** @type {boolean} Whether ball is in motion (for trail effect) */
    this.inMotion = false;

    /** @type {Array<{x: number, y: number, alpha: number}>} Trail positions */
    this._trail = [];

    /** @type {number} Maximum trail length */
    this._maxTrailLength = 5;
  }

  /**
   * Set ball position immediately
   * @param {number} x - Pitch X coordinate
   * @param {number} y - Pitch Y coordinate
   */
  setPosition(x, y) {
    // Add to trail if moving
    if (this.inMotion && (this.x !== x || this.y !== y)) {
      this._trail.push({ x: this.x, y: this.y, alpha: 0.6 });
      if (this._trail.length > this._maxTrailLength) {
        this._trail.shift();
      }
    }

    this.x = x;
    this.y = y;
  }

  /**
   * Set ball target position for animated movement
   * @param {number} targetX - Target pitch X coordinate
   * @param {number} targetY - Target pitch Y coordinate
   */
  setTarget(targetX, targetY) {
    this.targetX = targetX;
    this.targetY = targetY;
    this.inMotion = true;
  }

  /**
   * Mark ball as stopped (no more trail)
   */
  stop() {
    this.inMotion = false;
    this._trail = [];
  }

  /**
   * Show or hide the ball
   * @param {boolean} visible
   */
  setVisible(visible) {
    this.visible = visible;
  }

  /**
   * Draw the ball on the canvas
   */
  draw() {
    if (!this.visible) return;

    const ctx = this.ctx;
    const { x, y } = this.pitchRenderer.pitchToCanvas(this.x, this.y);

    // Draw trail (motion blur effect)
    if (this.inMotion && this._trail.length > 0) {
      for (let i = 0; i < this._trail.length; i++) {
        const trail = this._trail[i];
        const trailPos = this.pitchRenderer.pitchToCanvas(trail.x, trail.y);
        const alpha = (i / this._trail.length) * 0.3;
        const trailRadius = this.radius * (0.5 + (i / this._trail.length) * 0.5);

        ctx.beginPath();
        ctx.arc(trailPos.x, trailPos.y, trailRadius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
        ctx.fill();
      }
    }

    // Draw shadow
    ctx.beginPath();
    ctx.arc(
      x + this.shadowOffsetX,
      y + this.shadowOffsetY,
      this.radius,
      0,
      Math.PI * 2
    );
    ctx.fillStyle = this.shadowColor;
    ctx.fill();

    // Draw ball body
    const gradient = ctx.createRadialGradient(
      x - this.radius * 0.3,
      y - this.radius * 0.3,
      0,
      x,
      y,
      this.radius
    );
    gradient.addColorStop(0, '#ffffff');
    gradient.addColorStop(1, '#e0e0e0');

    ctx.beginPath();
    ctx.arc(x, y, this.radius, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();

    // Draw outline
    ctx.strokeStyle = this.outlineColor;
    ctx.lineWidth = this.outlineWidth;
    ctx.stroke();

    // Draw simple pentagon pattern for ball texture
    this._drawBallPattern(x, y);
  }

  /**
   * Draw a simple ball pattern (pentagon shapes)
   * @param {number} x - Canvas X
   * @param {number} y - Canvas Y
   * @private
   */
  _drawBallPattern(x, y) {
    const ctx = this.ctx;
    const r = this.radius * 0.4;

    ctx.fillStyle = '#333333';
    ctx.beginPath();
    // Simple hexagon in center
    for (let i = 0; i < 5; i++) {
      const angle = (i * 2 * Math.PI) / 5 - Math.PI / 2;
      const px = x + r * Math.cos(angle);
      const py = y + r * Math.sin(angle);
      if (i === 0) {
        ctx.moveTo(px, py);
      } else {
        ctx.lineTo(px, py);
      }
    }
    ctx.closePath();
    ctx.fill();
  }

  /**
   * Fade trail over time (call each frame)
   */
  updateTrail() {
    // Fade out trail entries
    for (let i = this._trail.length - 1; i >= 0; i--) {
      this._trail[i].alpha -= 0.05;
      if (this._trail[i].alpha <= 0) {
        this._trail.splice(i, 1);
      }
    }
  }
}
