/**
 * PitchRenderer - Draws the football pitch with markings and handles scaling
 * 
 * Renders a top-down 2D football pitch with all standard markings.
 * Handles responsive scaling to fit any container size.
 * 
 * Task 19.2: Create pitch scaling algorithm for responsive display
 * Task 19.3: Implement pitch drawing with markings
 */

export class PitchRenderer {
  /**
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D context
   */
  constructor(ctx) {
    /** @type {CanvasRenderingContext2D} */
    this.ctx = ctx;

    // Standard pitch dimensions in meters
    /** @type {number} Pitch width in meters */
    this.pitchWidth = 105;
    /** @type {number} Pitch height in meters */
    this.pitchHeight = 68;

    // Scaling state
    /** @type {number} Scale factor (pixels per meter) */
    this.scale = 1;
    /** @type {number} X offset to center pitch on canvas */
    this.offsetX = 0;
    /** @type {number} Y offset to center pitch on canvas */
    this.offsetY = 0;
    /** @type {number} Canvas width in pixels */
    this.canvasWidth = 0;
    /** @type {number} Canvas height in pixels */
    this.canvasHeight = 0;

    // Pitch colors
    /** @type {string} Main pitch color */
    this.pitchColor = '#2d8a2d';
    /** @type {string} Alternate stripe color for pitch pattern */
    this.pitchStripeColor = '#268a26';
    /** @type {string} Pitch marking line color */
    this.lineColor = '#ffffff';
    /** @type {number} Line width in pixels */
    this.lineWidth = 2;
  }

  /**
   * Calculate scale and offsets to fit pitch responsively in canvas
   * @param {number} canvasWidth - Canvas width in pixels
   * @param {number} canvasHeight - Canvas height in pixels
   */
  calculateScale(canvasWidth, canvasHeight) {
    this.canvasWidth = canvasWidth;
    this.canvasHeight = canvasHeight;

    // Calculate scale to fit pitch within canvas with margins
    const margin = 0.9; // Use 90% of available space
    const widthScale = (canvasWidth * margin) / this.pitchWidth;
    const heightScale = (canvasHeight * margin) / this.pitchHeight;

    // Use the smaller scale to maintain aspect ratio
    this.scale = Math.min(widthScale, heightScale);

    // Center the pitch on the canvas
    this.offsetX = (canvasWidth - this.pitchWidth * this.scale) / 2;
    this.offsetY = (canvasHeight - this.pitchHeight * this.scale) / 2;
  }

  /**
   * Convert pitch coordinates (0-105, 0-68) to canvas pixel coordinates
   * @param {number} pitchX - X position on pitch (0-105)
   * @param {number} pitchY - Y position on pitch (0-68)
   * @returns {{x: number, y: number}} Canvas pixel coordinates
   */
  pitchToCanvas(pitchX, pitchY) {
    return {
      x: this.offsetX + pitchX * this.scale,
      y: this.offsetY + pitchY * this.scale,
    };
  }

  /**
   * Convert canvas pixel coordinates to pitch coordinates
   * @param {number} canvasX - X pixel position on canvas
   * @param {number} canvasY - Y pixel position on canvas
   * @returns {{x: number, y: number}} Pitch coordinates (0-105, 0-68)
   */
  canvasToPitch(canvasX, canvasY) {
    return {
      x: (canvasX - this.offsetX) / this.scale,
      y: (canvasY - this.offsetY) / this.scale,
    };
  }

  /**
   * Convert a distance in meters to pixels
   * @param {number} meters - Distance in meters
   * @returns {number} Distance in pixels
   */
  metersToPixels(meters) {
    return meters * this.scale;
  }

  /**
   * Draw the complete pitch with all markings
   */
  draw() {
    const ctx = this.ctx;
    const s = this.scale;
    const ox = this.offsetX;
    const oy = this.offsetY;
    const pw = this.pitchWidth * s;
    const ph = this.pitchHeight * s;

    // Draw pitch background with stripe pattern
    this._drawPitchBackground(ox, oy, pw, ph, s);

    // Set line style for markings
    ctx.strokeStyle = this.lineColor;
    ctx.lineWidth = this.lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Outer boundary
    ctx.strokeRect(ox, oy, pw, ph);

    // Center line
    const centerX = ox + pw / 2;
    ctx.beginPath();
    ctx.moveTo(centerX, oy);
    ctx.lineTo(centerX, oy + ph);
    ctx.stroke();

    // Center circle (radius 9.15m)
    const centerY = oy + ph / 2;
    ctx.beginPath();
    ctx.arc(centerX, centerY, 9.15 * s, 0, Math.PI * 2);
    ctx.stroke();

    // Center spot
    ctx.fillStyle = this.lineColor;
    ctx.beginPath();
    ctx.arc(centerX, centerY, 0.3 * s, 0, Math.PI * 2);
    ctx.fill();

    // Penalty areas (16.5m x 40.3m)
    this._drawPenaltyArea(ox, oy, ph, s, 'left');
    this._drawPenaltyArea(ox + pw, oy, ph, s, 'right');

    // Goal areas (5.5m x 18.3m)
    this._drawGoalArea(ox, oy, ph, s, 'left');
    this._drawGoalArea(ox + pw, oy, ph, s, 'right');

    // Penalty spots (11m from goal line)
    this._drawPenaltySpot(ox + 11 * s, centerY);
    this._drawPenaltySpot(ox + pw - 11 * s, centerY);

    // Penalty arcs
    this._drawPenaltyArc(ox + 11 * s, centerY, s, 'left');
    this._drawPenaltyArc(ox + pw - 11 * s, centerY, s, 'right');

    // Corner arcs
    this._drawCornerArc(ox, oy, s);
    this._drawCornerArc(ox + pw, oy, s);
    this._drawCornerArc(ox, oy + ph, s);
    this._drawCornerArc(ox + pw, oy + ph, s);

    // Goals
    this._drawGoal(ox, centerY, s, 'left');
    this._drawGoal(ox + pw, centerY, s, 'right');
  }

  /**
   * Draw pitch background with alternating stripes
   * @private
   */
  _drawPitchBackground(ox, oy, pw, ph, scale) {
    const ctx = this.ctx;
    const stripeCount = 10;
    const stripeWidth = pw / stripeCount;

    for (let i = 0; i < stripeCount; i++) {
      ctx.fillStyle = i % 2 === 0 ? this.pitchColor : this.pitchStripeColor;
      ctx.fillRect(ox + i * stripeWidth, oy, stripeWidth, ph);
    }
  }

  /**
   * Draw penalty area
   * @private
   */
  _drawPenaltyArea(edgeX, oy, ph, scale, side) {
    const ctx = this.ctx;
    const width = 16.5 * scale;
    const height = 40.3 * scale;
    const topY = oy + (ph - height) / 2;

    if (side === 'left') {
      ctx.strokeRect(edgeX, topY, width, height);
    } else {
      ctx.strokeRect(edgeX - width, topY, width, height);
    }
  }

  /**
   * Draw goal area (6-yard box)
   * @private
   */
  _drawGoalArea(edgeX, oy, ph, scale, side) {
    const ctx = this.ctx;
    const width = 5.5 * scale;
    const height = 18.3 * scale;
    const topY = oy + (ph - height) / 2;

    if (side === 'left') {
      ctx.strokeRect(edgeX, topY, width, height);
    } else {
      ctx.strokeRect(edgeX - width, topY, width, height);
    }
  }

  /**
   * Draw penalty spot
   * @private
   */
  _drawPenaltySpot(x, y) {
    const ctx = this.ctx;
    ctx.fillStyle = this.lineColor;
    ctx.beginPath();
    ctx.arc(x, y, 0.3 * this.scale, 0, Math.PI * 2);
    ctx.fill();
  }

  /**
   * Draw penalty arc (the D outside the penalty area)
   * @private
   */
  _drawPenaltyArc(spotX, spotY, scale, side) {
    const ctx = this.ctx;
    const radius = 9.15 * scale;
    const penaltyBoxEdge = 16.5 * scale;

    // Calculate the angle where the arc intersects the penalty box edge
    const angle = Math.acos(penaltyBoxEdge / radius);

    ctx.beginPath();
    if (side === 'left') {
      ctx.arc(spotX, spotY, radius, -angle, angle);
    } else {
      ctx.arc(spotX, spotY, radius, Math.PI - angle, Math.PI + angle);
    }
    ctx.stroke();
  }

  /**
   * Draw corner arc
   * @private
   */
  _drawCornerArc(x, y, scale) {
    const ctx = this.ctx;
    const radius = 1 * scale; // 1 meter radius

    // Determine which quadrant
    const isLeft = x <= this.offsetX + (this.pitchWidth * scale) / 2;
    const isTop = y <= this.offsetY + (this.pitchHeight * scale) / 2;

    let startAngle, endAngle;
    if (isLeft && isTop) {
      startAngle = 0;
      endAngle = Math.PI / 2;
    } else if (!isLeft && isTop) {
      startAngle = Math.PI / 2;
      endAngle = Math.PI;
    } else if (isLeft && !isTop) {
      startAngle = -Math.PI / 2;
      endAngle = 0;
    } else {
      startAngle = Math.PI;
      endAngle = -Math.PI / 2;
    }

    ctx.beginPath();
    ctx.arc(x, y, radius, startAngle, endAngle);
    ctx.stroke();
  }

  /**
   * Draw goal posts
   * @private
   */
  _drawGoal(edgeX, centerY, scale, side) {
    const ctx = this.ctx;
    const goalWidth = 2.5 * scale; // Depth of goal
    const goalHeight = 7.32 * scale; // Width of goal (7.32m)
    const topY = centerY - goalHeight / 2;

    ctx.strokeStyle = '#cccccc';
    ctx.lineWidth = 3;

    if (side === 'left') {
      ctx.strokeRect(edgeX - goalWidth, topY, goalWidth, goalHeight);
    } else {
      ctx.strokeRect(edgeX, topY, goalWidth, goalHeight);
    }

    // Reset line style
    ctx.strokeStyle = this.lineColor;
    ctx.lineWidth = this.lineWidth;
  }
}
