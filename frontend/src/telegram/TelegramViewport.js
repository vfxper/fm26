/**
 * TelegramViewport.js - Viewport configuration and safe area handling
 * Manages viewport expansion, height tracking, and safe area insets.
 */

export class TelegramViewport {
  /**
   * @param {object|null} webApp - The Telegram WebApp instance
   * @param {boolean} isInsideTelegram - Whether running inside Telegram
   */
  constructor(webApp, isInsideTelegram) {
    this._webApp = webApp;
    this._isInsideTelegram = isInsideTelegram;

    /** @type {Function[]} */
    this._listeners = [];

    /** @type {Function|null} */
    this._viewportChangedHandler = null;
  }

  /**
   * Initialize viewport configuration and event listeners.
   */
  init() {
    this._applySafeAreaCSS();
    this._listenForChanges();
  }

  /**
   * Expand the Web App to maximum available height.
   */
  expand() {
    if (this._isInsideTelegram && this._webApp?.expand) {
      this._webApp.expand();
    }
  }

  /**
   * Check if the Web App is expanded to full height.
   * @returns {boolean}
   */
  isExpanded() {
    if (this._isInsideTelegram && this._webApp) {
      return !!this._webApp.isExpanded;
    }
    return true; // Always "expanded" in dev mode
  }

  /**
   * Get the current viewport height (may change during animations).
   * @returns {number} Height in pixels
   */
  getViewportHeight() {
    if (this._isInsideTelegram && this._webApp) {
      return this._webApp.viewportHeight || window.innerHeight;
    }
    return window.innerHeight;
  }

  /**
   * Get the stable viewport height (doesn't change during animations).
   * @returns {number} Height in pixels
   */
  getStableViewportHeight() {
    if (this._isInsideTelegram && this._webApp) {
      return this._webApp.viewportStableHeight || window.innerHeight;
    }
    return window.innerHeight;
  }

  /**
   * Get the content safe area insets (area not covered by Telegram UI).
   * @returns {{top: number, bottom: number, left: number, right: number}}
   */
  getContentSafeAreaInset() {
    if (this._isInsideTelegram && this._webApp?.contentSafeAreaInset) {
      return { ...this._webApp.contentSafeAreaInset };
    }
    return { top: 0, bottom: 0, left: 0, right: 0 };
  }

  /**
   * Get the device safe area insets (notch, home indicator, etc.).
   * @returns {{top: number, bottom: number, left: number, right: number}}
   */
  getSafeAreaInset() {
    if (this._isInsideTelegram && this._webApp?.safeAreaInset) {
      return { ...this._webApp.safeAreaInset };
    }
    return { top: 0, bottom: 0, left: 0, right: 0 };
  }

  /**
   * Disable vertical swipe-to-close gesture.
   * Useful for screens with vertical scrolling or drag interactions.
   */
  disableVerticalSwipes() {
    if (this._isInsideTelegram && this._webApp?.disableVerticalSwipes) {
      this._webApp.disableVerticalSwipes();
    }
  }

  /**
   * Enable vertical swipe-to-close gesture.
   */
  enableVerticalSwipes() {
    if (this._isInsideTelegram && this._webApp?.enableVerticalSwipes) {
      this._webApp.enableVerticalSwipes();
    }
  }

  /**
   * Check if vertical swipes are enabled.
   * @returns {boolean}
   */
  isVerticalSwipesEnabled() {
    if (this._isInsideTelegram && this._webApp) {
      return !!this._webApp.isVerticalSwipesEnabled;
    }
    return false;
  }

  /**
   * Request fullscreen mode (Telegram Web App v8.0+).
   */
  requestFullscreen() {
    if (this._isInsideTelegram && this._webApp?.requestFullscreen) {
      this._webApp.requestFullscreen();
    }
  }

  /**
   * Exit fullscreen mode.
   */
  exitFullscreen() {
    if (this._isInsideTelegram && this._webApp?.exitFullscreen) {
      this._webApp.exitFullscreen();
    }
  }

  /**
   * Check if the app is in fullscreen mode.
   * @returns {boolean}
   */
  isFullscreen() {
    if (this._isInsideTelegram && this._webApp) {
      return !!this._webApp.isFullscreen;
    }
    return false;
  }

  /**
   * Register a listener for viewport changes.
   * @param {Function} callback - Called with ({height, stableHeight, isStateStable})
   * @returns {Function} Unsubscribe function
   */
  onChange(callback) {
    this._listeners.push(callback);
    return () => {
      this._listeners = this._listeners.filter((cb) => cb !== callback);
    };
  }

  /**
   * Apply safe area CSS custom properties to the document.
   * @private
   */
  _applySafeAreaCSS() {
    const root = document.documentElement.style;
    const contentInset = this.getContentSafeAreaInset();
    const safeInset = this.getSafeAreaInset();

    root.setProperty('--tg-viewport-height', `${this.getViewportHeight()}px`);
    root.setProperty('--tg-viewport-stable-height', `${this.getStableViewportHeight()}px`);

    root.setProperty('--tg-content-safe-area-inset-top', `${contentInset.top}px`);
    root.setProperty('--tg-content-safe-area-inset-bottom', `${contentInset.bottom}px`);
    root.setProperty('--tg-content-safe-area-inset-left', `${contentInset.left}px`);
    root.setProperty('--tg-content-safe-area-inset-right', `${contentInset.right}px`);

    root.setProperty('--tg-safe-area-inset-top', `${safeInset.top}px`);
    root.setProperty('--tg-safe-area-inset-bottom', `${safeInset.bottom}px`);
    root.setProperty('--tg-safe-area-inset-left', `${safeInset.left}px`);
    root.setProperty('--tg-safe-area-inset-right', `${safeInset.right}px`);
  }

  /**
   * Listen for viewport change events.
   * @private
   */
  _listenForChanges() {
    if (this._isInsideTelegram && this._webApp) {
      this._viewportChangedHandler = (event) => {
        this._applySafeAreaCSS();

        const data = {
          height: this.getViewportHeight(),
          stableHeight: this.getStableViewportHeight(),
          isStateStable: event?.isStateStable ?? true,
        };

        this._listeners.forEach((cb) => cb(data));

        // Dispatch a resize event so canvas and other elements can adapt
        if (data.isStateStable) {
          window.dispatchEvent(new Event('resize'));
        }
      };
      this._webApp.onEvent('viewportChanged', this._viewportChangedHandler);
    } else {
      // Dev fallback: listen for window resize
      this._resizeHandler = () => {
        this._applySafeAreaCSS();
        const data = {
          height: window.innerHeight,
          stableHeight: window.innerHeight,
          isStateStable: true,
        };
        this._listeners.forEach((cb) => cb(data));
      };
      window.addEventListener('resize', this._resizeHandler);
    }
  }

  /**
   * Clean up event listeners.
   */
  destroy() {
    if (this._isInsideTelegram && this._webApp && this._viewportChangedHandler) {
      this._webApp.offEvent('viewportChanged', this._viewportChangedHandler);
      this._viewportChangedHandler = null;
    }

    if (this._resizeHandler) {
      window.removeEventListener('resize', this._resizeHandler);
      this._resizeHandler = null;
    }

    this._listeners = [];
  }
}
