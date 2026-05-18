/**
 * TelegramTheme.js - Theme detection (dark/light mode) and color variables
 * Detects the current Telegram theme, applies CSS variables, and reacts to changes.
 */

/**
 * @typedef {'light'|'dark'} ColorScheme
 */

/**
 * @typedef {Object} ThemeParams
 * @property {string} [bg_color] - Background color
 * @property {string} [text_color] - Main text color
 * @property {string} [hint_color] - Hint/secondary text color
 * @property {string} [link_color] - Link color
 * @property {string} [button_color] - Button background color
 * @property {string} [button_text_color] - Button text color
 * @property {string} [secondary_bg_color] - Secondary background color
 * @property {string} [header_bg_color] - Header background color
 * @property {string} [accent_text_color] - Accent text color
 * @property {string} [section_bg_color] - Section background color
 * @property {string} [section_header_text_color] - Section header text color
 * @property {string} [subtitle_text_color] - Subtitle text color
 * @property {string} [destructive_text_color] - Destructive action text color
 */

export class TelegramTheme {
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
    this._themeChangedHandler = null;
  }

  /**
   * Initialize theme detection and apply initial theme.
   */
  init() {
    this._applyTheme();
    this._listenForChanges();
  }

  /**
   * Get the current color scheme.
   * @returns {ColorScheme}
   */
  getColorScheme() {
    if (this._isInsideTelegram && this._webApp) {
      return this._webApp.colorScheme || 'light';
    }

    // Dev fallback: check system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  /**
   * Check if the current theme is dark.
   * @returns {boolean}
   */
  isDark() {
    return this.getColorScheme() === 'dark';
  }

  /**
   * Check if the current theme is light.
   * @returns {boolean}
   */
  isLight() {
    return this.getColorScheme() === 'light';
  }

  /**
   * Get the Telegram theme parameters (colors).
   * @returns {ThemeParams}
   */
  getThemeParams() {
    if (this._isInsideTelegram && this._webApp?.themeParams) {
      return { ...this._webApp.themeParams };
    }

    // Dev fallback with sensible defaults
    if (this.isDark()) {
      return {
        bg_color: '#1c1c1e',
        text_color: '#ffffff',
        hint_color: '#98989e',
        link_color: '#007aff',
        button_color: '#007aff',
        button_text_color: '#ffffff',
        secondary_bg_color: '#2c2c2e',
        header_bg_color: '#1c1c1e',
        accent_text_color: '#007aff',
        section_bg_color: '#2c2c2e',
        section_header_text_color: '#98989e',
        subtitle_text_color: '#98989e',
        destructive_text_color: '#ff3b30',
      };
    }

    return {
      bg_color: '#ffffff',
      text_color: '#000000',
      hint_color: '#8e8e93',
      link_color: '#007aff',
      button_color: '#007aff',
      button_text_color: '#ffffff',
      secondary_bg_color: '#f2f2f7',
      header_bg_color: '#ffffff',
      accent_text_color: '#007aff',
      section_bg_color: '#ffffff',
      section_header_text_color: '#8e8e93',
      subtitle_text_color: '#8e8e93',
      destructive_text_color: '#ff3b30',
    };
  }

  /**
   * Get a specific theme color.
   * @param {string} key - Theme param key (e.g., 'bg_color', 'text_color')
   * @param {string} [fallback=''] - Fallback value
   * @returns {string}
   */
  getColor(key, fallback = '') {
    const params = this.getThemeParams();
    return params[key] || fallback;
  }

  /**
   * Register a listener for theme changes.
   * @param {Function} callback - Called with (colorScheme, themeParams) on change
   * @returns {Function} Unsubscribe function
   */
  onChange(callback) {
    this._listeners.push(callback);
    return () => {
      this._listeners = this._listeners.filter((cb) => cb !== callback);
    };
  }

  /**
   * Apply theme CSS variables to the document root.
   * @private
   */
  _applyTheme() {
    const scheme = this.getColorScheme();
    const params = this.getThemeParams();

    // Set data-theme attribute
    document.documentElement.setAttribute('data-theme', scheme);

    // Apply CSS custom properties from theme params
    const root = document.documentElement.style;
    root.setProperty('--tg-color-scheme', scheme);
    root.setProperty('--tg-bg-color', params.bg_color || '');
    root.setProperty('--tg-text-color', params.text_color || '');
    root.setProperty('--tg-hint-color', params.hint_color || '');
    root.setProperty('--tg-link-color', params.link_color || '');
    root.setProperty('--tg-button-color', params.button_color || '');
    root.setProperty('--tg-button-text-color', params.button_text_color || '');
    root.setProperty('--tg-secondary-bg-color', params.secondary_bg_color || '');
    root.setProperty('--tg-header-bg-color', params.header_bg_color || '');
    root.setProperty('--tg-accent-text-color', params.accent_text_color || '');
    root.setProperty('--tg-section-bg-color', params.section_bg_color || '');
    root.setProperty('--tg-section-header-text-color', params.section_header_text_color || '');
    root.setProperty('--tg-subtitle-text-color', params.subtitle_text_color || '');
    root.setProperty('--tg-destructive-text-color', params.destructive_text_color || '');

    // Update meta theme-color
    let metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (!metaThemeColor) {
      metaThemeColor = document.createElement('meta');
      metaThemeColor.setAttribute('name', 'theme-color');
      document.head.appendChild(metaThemeColor);
    }
    metaThemeColor.setAttribute('content', params.header_bg_color || params.bg_color || '#ffffff');
  }

  /**
   * Listen for Telegram theme change events.
   * @private
   */
  _listenForChanges() {
    if (this._isInsideTelegram && this._webApp) {
      this._themeChangedHandler = () => {
        this._applyTheme();
        const scheme = this.getColorScheme();
        const params = this.getThemeParams();
        this._listeners.forEach((cb) => cb(scheme, params));
      };
      this._webApp.onEvent('themeChanged', this._themeChangedHandler);
    } else {
      // Dev fallback: listen for system theme changes
      try {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        if (mediaQuery && mediaQuery.addEventListener) {
          this._mediaQueryHandler = () => {
            this._applyTheme();
            const scheme = this.getColorScheme();
            const params = this.getThemeParams();
            this._listeners.forEach((cb) => cb(scheme, params));
          };
          mediaQuery.addEventListener('change', this._mediaQueryHandler);
        }
      } catch (e) {
        // matchMedia not available in this environment
      }
    }
  }

  /**
   * Clean up event listeners.
   */
  destroy() {
    if (this._isInsideTelegram && this._webApp && this._themeChangedHandler) {
      this._webApp.offEvent('themeChanged', this._themeChangedHandler);
      this._themeChangedHandler = null;
    }

    if (this._mediaQueryHandler) {
      try {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.removeEventListener('change', this._mediaQueryHandler);
      } catch (e) {
        // matchMedia may not support removeEventListener in all environments
      }
      this._mediaQueryHandler = null;
    }

    this._listeners = [];
  }
}
