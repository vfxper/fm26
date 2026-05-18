/**
 * AccessibilityManager - Reduced-motion accessibility support
 * 
 * Respects the prefers-reduced-motion media query and provides
 * fallback rendering modes for users who prefer reduced animations.
 * 
 * Task 19.16: Create reduced-motion accessibility support
 */

export class AccessibilityManager {
  constructor() {
    /** @type {boolean} Whether reduced motion is preferred */
    this.reducedMotion = false;

    /** @type {MediaQueryList|null} Media query listener reference */
    this._mediaQuery = null;

    /** @type {Function|null} Bound handler for cleanup */
    this._handleChange = null;

    this._init();
  }

  /**
   * Initialize media query detection for prefers-reduced-motion
   * @private
   */
  _init() {
    if (typeof window === 'undefined' || !window.matchMedia) {
      return;
    }

    this._mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    this.reducedMotion = this._mediaQuery.matches;

    this._handleChange = (event) => {
      this.reducedMotion = event.matches;
    };

    // Use addEventListener for modern browsers
    if (this._mediaQuery.addEventListener) {
      this._mediaQuery.addEventListener('change', this._handleChange);
    } else if (this._mediaQuery.addListener) {
      // Fallback for older browsers
      this._mediaQuery.addListener(this._handleChange);
    }
  }

  /**
   * Check if animations should be skipped
   * @returns {boolean} True if animations should be skipped or minimized
   */
  shouldSkipAnimations() {
    return this.reducedMotion;
  }

  /**
   * Get the appropriate animation duration based on accessibility settings
   * @param {number} normalDuration - Normal duration in ms
   * @returns {number} Adjusted duration (0 if reduced motion, normal otherwise)
   */
  getAnimationDuration(normalDuration) {
    if (this.reducedMotion) {
      return 0;
    }
    return normalDuration;
  }

  /**
   * Get the appropriate easing for current accessibility mode
   * @param {string} normalEasing - Normal easing function name
   * @returns {string} 'linear' if reduced motion, normal easing otherwise
   */
  getEasing(normalEasing) {
    if (this.reducedMotion) {
      return 'linear';
    }
    return normalEasing;
  }

  /**
   * Check if particle effects (weather, celebrations) should be shown
   * @returns {boolean} True if particle effects are allowed
   */
  shouldShowParticles() {
    return !this.reducedMotion;
  }

  /**
   * Manually override reduced motion setting
   * @param {boolean} enabled - Whether to force reduced motion
   */
  setReducedMotion(enabled) {
    this.reducedMotion = enabled;
  }

  /**
   * Clean up event listeners
   */
  destroy() {
    if (this._mediaQuery && this._handleChange) {
      if (this._mediaQuery.removeEventListener) {
        this._mediaQuery.removeEventListener('change', this._handleChange);
      } else if (this._mediaQuery.removeListener) {
        this._mediaQuery.removeListener(this._handleChange);
      }
    }
    this._mediaQuery = null;
    this._handleChange = null;
  }
}
