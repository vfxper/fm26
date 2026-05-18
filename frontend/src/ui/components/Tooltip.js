/**
 * Tooltip.js - Contextual help tooltips
 * Provides accessible tooltips for non-obvious UI elements
 */

export class Tooltip {
  /**
   * @param {Object} options
   * @param {string} options.text - Tooltip text content
   * @param {string} [options.position='top'] - Position: top, bottom, left, right
   * @param {number} [options.showDelay=400] - Delay before showing (ms)
   * @param {number} [options.hideDelay=200] - Delay before hiding (ms)
   */
  constructor(options = {}) {
    this.text = options.text || '';
    this.position = options.position || 'top';
    this.showDelay = options.showDelay ?? 400;
    this.hideDelay = options.hideDelay ?? 200;
    this._tooltipEl = null;
    this._showTimer = null;
    this._hideTimer = null;
    this._target = null;
  }

  /**
   * Attach tooltip to a target element
   * @param {HTMLElement} target
   */
  attach(target) {
    this._target = target;
    target.setAttribute('aria-describedby', '');

    // Touch: long press to show
    let touchTimer = null;
    target.addEventListener('touchstart', (e) => {
      touchTimer = setTimeout(() => {
        this.show(target);
      }, 600);
    }, { passive: true });

    target.addEventListener('touchend', () => {
      if (touchTimer) clearTimeout(touchTimer);
      this.hide();
    }, { passive: true });

    target.addEventListener('touchcancel', () => {
      if (touchTimer) clearTimeout(touchTimer);
      this.hide();
    }, { passive: true });

    // Mouse: hover
    target.addEventListener('mouseenter', () => {
      this._showTimer = setTimeout(() => this.show(target), this.showDelay);
    });

    target.addEventListener('mouseleave', () => {
      if (this._showTimer) clearTimeout(this._showTimer);
      this._hideTimer = setTimeout(() => this.hide(), this.hideDelay);
    });

    // Keyboard: focus
    target.addEventListener('focus', () => {
      this._showTimer = setTimeout(() => this.show(target), this.showDelay);
    });

    target.addEventListener('blur', () => {
      if (this._showTimer) clearTimeout(this._showTimer);
      this.hide();
    });
  }

  /**
   * Show the tooltip near the target
   * @param {HTMLElement} target
   */
  show(target) {
    this.hide(); // Remove any existing

    const tooltip = document.createElement('div');
    tooltip.className = `tooltip tooltip--${this.position}`;
    tooltip.setAttribute('role', 'tooltip');
    tooltip.textContent = this.text;

    document.body.appendChild(tooltip);
    this._tooltipEl = tooltip;

    // Position relative to target
    const rect = target.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();

    let top, left;

    switch (this.position) {
      case 'top':
        top = rect.top - tooltipRect.height - 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        break;
      case 'bottom':
        top = rect.bottom + 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
        break;
      case 'left':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.left - tooltipRect.width - 8;
        break;
      case 'right':
        top = rect.top + (rect.height - tooltipRect.height) / 2;
        left = rect.right + 8;
        break;
      default:
        top = rect.top - tooltipRect.height - 8;
        left = rect.left + (rect.width - tooltipRect.width) / 2;
    }

    // Keep within viewport
    left = Math.max(8, Math.min(left, window.innerWidth - tooltipRect.width - 8));
    top = Math.max(8, Math.min(top, window.innerHeight - tooltipRect.height - 8));

    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;

    // Animate in
    requestAnimationFrame(() => {
      tooltip.classList.add('tooltip--visible');
    });

    // Update aria
    if (target) {
      const id = `tooltip-${Date.now()}`;
      tooltip.id = id;
      target.setAttribute('aria-describedby', id);
    }
  }

  /**
   * Hide the tooltip
   */
  hide() {
    if (this._showTimer) {
      clearTimeout(this._showTimer);
      this._showTimer = null;
    }

    if (this._tooltipEl) {
      this._tooltipEl.classList.remove('tooltip--visible');
      const el = this._tooltipEl;
      setTimeout(() => {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 150);
      this._tooltipEl = null;
    }

    if (this._target) {
      this._target.removeAttribute('aria-describedby');
    }
  }

  /**
   * Update tooltip text
   * @param {string} text
   */
  setText(text) {
    this.text = text;
    if (this._tooltipEl) {
      this._tooltipEl.textContent = text;
    }
  }
}

/**
 * Utility: attach tooltips to all elements with data-tooltip attribute
 * @param {HTMLElement} [root=document.body]
 */
export function initTooltips(root = document.body) {
  const elements = root.querySelectorAll('[data-tooltip]');
  elements.forEach((el) => {
    const tooltip = new Tooltip({
      text: el.dataset.tooltip,
      position: el.dataset.tooltipPosition || 'top',
    });
    tooltip.attach(el);
  });
}
