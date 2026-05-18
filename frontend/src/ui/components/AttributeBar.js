/**
 * AttributeBar.js - Visual attribute bar (1-20 scale with color coding)
 * Color coding:
 *   1-5:   Red (poor)
 *   6-10:  Orange (below average)
 *   11-14: Yellow (average)
 *   15-17: Light green (good)
 *   18-20: Green (excellent)
 */

export class AttributeBar {
  /**
   * @param {Object} options
   * @param {string} options.name - Attribute name
   * @param {number} options.value - Attribute value (1-20)
   * @param {number} [options.max=20] - Maximum value
   * @param {number} [options.compareValue] - Optional comparison value
   */
  constructor(options = {}) {
    this.name = options.name || '';
    this.value = options.value ?? 0;
    this.max = options.max || 20;
    this.compareValue = options.compareValue ?? null;
    this.element = null;
  }

  /**
   * Render the attribute bar
   * @returns {HTMLElement}
   */
  render() {
    const el = document.createElement('div');
    el.className = 'attribute-bar';
    el.setAttribute('role', 'meter');
    el.setAttribute('aria-label', `${this.name}: ${this.value} out of ${this.max}`);
    el.setAttribute('aria-valuenow', String(this.value));
    el.setAttribute('aria-valuemin', '1');
    el.setAttribute('aria-valuemax', String(this.max));

    const percentage = Math.min(100, Math.max(0, (this.value / this.max) * 100));
    const color = this._getColor(this.value);

    let compareHTML = '';
    if (this.compareValue != null) {
      const diff = this.value - this.compareValue;
      const diffClass = diff > 0 ? 'positive' : diff < 0 ? 'negative' : 'neutral';
      compareHTML = `<span class="attribute-bar__diff attribute-bar__diff--${diffClass}">${diff > 0 ? '+' : ''}${diff}</span>`;
    }

    el.innerHTML = `
      <span class="attribute-bar__name">${this.name}</span>
      <div class="attribute-bar__track">
        <div class="attribute-bar__fill" style="width:${percentage}%;background-color:${color}"></div>
      </div>
      <span class="attribute-bar__value" style="color:${color}">${this.value}</span>
      ${compareHTML}
    `;

    this.element = el;
    return el;
  }

  /**
   * Update the value
   * @param {number} value
   */
  setValue(value) {
    this.value = value;
    if (this.element) {
      const fill = this.element.querySelector('.attribute-bar__fill');
      const valueEl = this.element.querySelector('.attribute-bar__value');
      const percentage = Math.min(100, Math.max(0, (value / this.max) * 100));
      const color = this._getColor(value);

      fill.style.width = `${percentage}%`;
      fill.style.backgroundColor = color;
      valueEl.textContent = String(value);
      valueEl.style.color = color;

      this.element.setAttribute('aria-valuenow', String(value));
      this.element.setAttribute('aria-label', `${this.name}: ${value} out of ${this.max}`);
    }
  }

  /**
   * Get color based on attribute value
   * @param {number} value
   * @returns {string} CSS color
   */
  _getColor(value) {
    if (value >= 18) return '#22c55e'; // Green - excellent
    if (value >= 15) return '#84cc16'; // Light green - good
    if (value >= 11) return '#eab308'; // Yellow - average
    if (value >= 6) return '#f97316';  // Orange - below average
    return '#ef4444';                   // Red - poor
  }
}
