/**
 * LoadingIndicator.js - Loading spinner shown after 500ms delay
 * Only displays if the operation takes longer than 500ms to avoid flicker
 */

export class LoadingIndicator {
  /**
   * @param {Object} [options]
   * @param {number} [options.delay=500] - Delay in ms before showing
   * @param {string} [options.message] - Optional loading message
   * @param {boolean} [options.fullscreen=false] - Whether to cover full viewport
   */
  constructor(options = {}) {
    this.delay = options.delay ?? 500;
    this.message = options.message || '';
    this.fullscreen = options.fullscreen || false;
    this.element = null;
    this._timer = null;
    this._visible = false;
  }

  /**
   * Show the loading indicator (after delay)
   * @param {HTMLElement} [container] - Container to append to (defaults to document.body)
   */
  show(container) {
    if (this._visible) return;

    const target = container || document.body;

    this._timer = setTimeout(() => {
      this._createDOM();
      target.appendChild(this.element);
      // Trigger reflow for animation
      void this.element.offsetHeight;
      this.element.classList.add('loading-indicator--visible');
      this._visible = true;
    }, this.delay);
  }

  /**
   * Hide and remove the loading indicator
   */
  hide() {
    if (this._timer) {
      clearTimeout(this._timer);
      this._timer = null;
    }

    if (this.element) {
      this.element.classList.remove('loading-indicator--visible');
      // Remove after transition
      setTimeout(() => {
        if (this.element && this.element.parentNode) {
          this.element.parentNode.removeChild(this.element);
        }
        this.element = null;
        this._visible = false;
      }, 200);
    }
  }

  /**
   * Check if currently visible
   * @returns {boolean}
   */
  isVisible() {
    return this._visible;
  }

  /**
   * Update the message text
   * @param {string} message
   */
  setMessage(message) {
    this.message = message;
    if (this.element) {
      const msgEl = this.element.querySelector('.loading-indicator__message');
      if (msgEl) msgEl.textContent = message;
    }
  }

  _createDOM() {
    const el = document.createElement('div');
    el.className = `loading-indicator${this.fullscreen ? ' loading-indicator--fullscreen' : ''}`;
    el.setAttribute('role', 'status');
    el.setAttribute('aria-live', 'polite');
    el.setAttribute('aria-label', 'Loading');

    el.innerHTML = `
      <div class="loading-indicator__spinner" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="32" height="32">
          <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-dasharray="31.4 31.4" />
        </svg>
      </div>
      ${this.message ? `<p class="loading-indicator__message">${this.message}</p>` : ''}
    `;

    this.element = el;
  }
}

/**
 * Utility: wrap an async operation with a loading indicator
 * @param {Function} asyncFn - Async function to execute
 * @param {Object} [options] - LoadingIndicator options
 * @param {HTMLElement} [container] - Container element
 * @returns {Promise<*>} Result of asyncFn
 */
export async function withLoading(asyncFn, options = {}, container) {
  const loader = new LoadingIndicator(options);
  loader.show(container);
  try {
    return await asyncFn();
  } finally {
    loader.hide();
  }
}
