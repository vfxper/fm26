/**
 * RadarChart.js - Canvas-based radar chart for attribute visualization
 */

export class RadarChart {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {Object} data
   * @param {string[]} data.labels - Axis labels
   * @param {number[]} data.values - Values for each axis
   * @param {number} [data.max=20] - Maximum value
   * @param {Object} [options]
   * @param {string} [options.fillColor] - Fill color
   * @param {string} [options.strokeColor] - Stroke color
   * @param {string} [options.gridColor] - Grid line color
   * @param {string} [options.labelColor] - Label text color
   * @param {number[]} [options.compareValues] - Optional comparison values
   */
  constructor(canvas, data, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.labels = data.labels || [];
    this.values = data.values || [];
    this.max = data.max || 20;
    this.fillColor = options.fillColor || 'rgba(34, 197, 94, 0.3)';
    this.strokeColor = options.strokeColor || 'rgba(34, 197, 94, 0.8)';
    this.gridColor = options.gridColor || 'rgba(255, 255, 255, 0.15)';
    this.labelColor = options.labelColor || 'rgba(255, 255, 255, 0.8)';
    this.compareValues = options.compareValues || null;
    this.compareFillColor = options.compareFillColor || 'rgba(239, 68, 68, 0.2)';
    this.compareStrokeColor = options.compareStrokeColor || 'rgba(239, 68, 68, 0.6)';
  }

  /**
   * Draw the radar chart
   */
  draw() {
    const { ctx, canvas } = this;
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(cx, cy) - 40;
    const sides = this.labels.length;

    if (sides < 3) return;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Draw grid rings
    const rings = 4;
    for (let r = 1; r <= rings; r++) {
      const ringRadius = (radius / rings) * r;
      ctx.beginPath();
      for (let i = 0; i <= sides; i++) {
        const angle = (Math.PI * 2 * i) / sides - Math.PI / 2;
        const x = cx + ringRadius * Math.cos(angle);
        const y = cy + ringRadius * Math.sin(angle);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = this.gridColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw axis lines
    for (let i = 0; i < sides; i++) {
      const angle = (Math.PI * 2 * i) / sides - Math.PI / 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + radius * Math.cos(angle), cy + radius * Math.sin(angle));
      ctx.strokeStyle = this.gridColor;
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Draw comparison values (if present)
    if (this.compareValues && this.compareValues.length === sides) {
      this._drawPolygon(cx, cy, radius, sides, this.compareValues, this.compareFillColor, this.compareStrokeColor);
    }

    // Draw main values
    this._drawPolygon(cx, cy, radius, sides, this.values, this.fillColor, this.strokeColor);

    // Draw value dots
    for (let i = 0; i < sides; i++) {
      const angle = (Math.PI * 2 * i) / sides - Math.PI / 2;
      const val = Math.min(this.values[i] || 0, this.max);
      const r = (val / this.max) * radius;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = this.strokeColor;
      ctx.fill();
    }

    // Draw labels
    ctx.font = '11px -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = this.labelColor;

    for (let i = 0; i < sides; i++) {
      const angle = (Math.PI * 2 * i) / sides - Math.PI / 2;
      const labelRadius = radius + 24;
      const x = cx + labelRadius * Math.cos(angle);
      const y = cy + labelRadius * Math.sin(angle);

      ctx.fillText(this.labels[i], x, y);

      // Draw value below label
      const val = this.values[i] ?? 0;
      ctx.fillStyle = this._getValueColor(val);
      ctx.fillText(String(val), x, y + 13);
      ctx.fillStyle = this.labelColor;
    }
  }

  /**
   * Update values and redraw
   * @param {number[]} values
   */
  update(values) {
    this.values = values;
    this.draw();
  }

  /**
   * Set comparison values and redraw
   * @param {number[]} values
   */
  setComparison(values) {
    this.compareValues = values;
    this.draw();
  }

  _drawPolygon(cx, cy, radius, sides, values, fillColor, strokeColor) {
    const { ctx } = this;
    ctx.beginPath();
    for (let i = 0; i < sides; i++) {
      const angle = (Math.PI * 2 * i) / sides - Math.PI / 2;
      const val = Math.min(values[i] || 0, this.max);
      const r = (val / this.max) * radius;
      const x = cx + r * Math.cos(angle);
      const y = cy + r * Math.sin(angle);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  _getValueColor(value) {
    if (value >= 18) return '#22c55e';
    if (value >= 15) return '#84cc16';
    if (value >= 11) return '#eab308';
    if (value >= 6) return '#f97316';
    return '#ef4444';
  }
}
