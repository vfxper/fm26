/**
 * NotificationBadge.js - Badge component for nav items and other elements
 */

export class NotificationBadge {
  /**
   * @param {Object} [options]
   * @param {number} [options.count=0] - Initial count
   * @param {number} [options.max=99] - Maximum displayed number
   * @param {string} [options.color] - Badge background color
   */
  constructor(options = {}) {
    this.count = options.count || 0;
    this.max = options.max ?? 99;
    this.color = options.color || null;
    this.element = null;
  }

  /**
   * Render the badge
   * @returns {HTMLElement}
   */
  render() {
    const badge = document.createElement('span');
    badge.className = 'notification-badge';
    badge.setAttribute('role', 'status');
    badge.setAttribute('aria-live', 'polite');

    if (this.color) {
      badge.style.backgroundColor = this.color;
    }

    this._update(badge);
    this.element = badge;
    return badge;
  }

  /**
   * Set the badge count
   * @param {number} count
   */
  setCount(count) {
    this.count = count;
    if (this.element) {
      this._update(this.element);
    }
  }

  /**
   * Increment the count
   * @param {number} [amount=1]
   */
  increment(amount = 1) {
    this.setCount(this.count + amount);
  }

  /**
   * Clear the badge (set to 0)
   */
  clear() {
    this.setCount(0);
  }

  _update(el) {
    if (this.count <= 0) {
      el.classList.add('hidden');
      el.textContent = '';
      el.setAttribute('aria-label', '');
    } else {
      el.classList.remove('hidden');
      const display = this.count > this.max ? `${this.max}+` : String(this.count);
      el.textContent = display;
      el.setAttribute('aria-label', `${this.count} notification${this.count !== 1 ? 's' : ''}`);
    }
  }
}
