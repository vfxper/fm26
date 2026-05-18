/**
 * TelegramWebApp.js - Main wrapper class for Telegram Web App SDK
 * Initializes the SDK and provides a clean API for all Telegram features.
 * Gracefully falls back to mock behavior when running outside Telegram (development).
 */

import { TelegramAuth } from './TelegramAuth.js';
import { TelegramUI } from './TelegramUI.js';
import { TelegramStorage } from './TelegramStorage.js';
import { TelegramTheme } from './TelegramTheme.js';
import { TelegramViewport } from './TelegramViewport.js';

/**
 * @typedef {Object} TelegramWebAppOptions
 * @property {boolean} [expandOnInit=true] - Whether to expand the app on initialization
 * @property {boolean} [enableClosingConfirmation=false] - Whether to enable closing confirmation
 * @property {boolean} [disableVerticalSwipes=true] - Whether to disable vertical swipes
 * @property {string} [headerColor] - Custom header color
 * @property {string} [backgroundColor] - Custom background color
 */

export class TelegramWebApp {
  /**
   * @param {TelegramWebAppOptions} [options]
   */
  constructor(options = {}) {
    this._options = {
      expandOnInit: true,
      enableClosingConfirmation: false,
      disableVerticalSwipes: true,
      headerColor: null,
      backgroundColor: null,
      ...options,
    };

    /** @type {object|null} */
    this._webApp = null;

    /** @type {boolean} */
    this._isInsideTelegram = false;

    /** @type {TelegramAuth} */
    this.auth = null;

    /** @type {TelegramUI} */
    this.ui = null;

    /** @type {TelegramStorage} */
    this.storage = null;

    /** @type {TelegramTheme} */
    this.theme = null;

    /** @type {TelegramViewport} */
    this.viewport = null;

    /** @type {boolean} */
    this._ready = false;
  }

  /**
   * Check if running inside Telegram Web App environment
   * @returns {boolean}
   */
  get isInsideTelegram() {
    return this._isInsideTelegram;
  }

  /**
   * Get the raw Telegram WebApp object (or null in dev mode)
   * @returns {object|null}
   */
  get raw() {
    return this._webApp;
  }

  /**
   * Get the platform string
   * @returns {string}
   */
  get platform() {
    return this._webApp?.platform || 'unknown';
  }

  /**
   * Get the SDK version
   * @returns {string}
   */
  get version() {
    return this._webApp?.version || '0.0';
  }

  /**
   * Whether the app has been initialized
   * @returns {boolean}
   */
  get isReady() {
    return this._ready;
  }

  /**
   * Initialize the Telegram Web App SDK and all sub-modules.
   * Must be called before using any other methods.
   * @returns {TelegramWebApp} this instance for chaining
   */
  init() {
    // Detect Telegram environment
    this._isInsideTelegram = !!(window.Telegram && window.Telegram.WebApp);

    if (this._isInsideTelegram) {
      this._webApp = window.Telegram.WebApp;
    } else {
      console.warn(
        '[TelegramWebApp] Not running inside Telegram. Using fallback/mock mode for development.'
      );
    }

    // Initialize sub-modules
    this.auth = new TelegramAuth(this._webApp, this._isInsideTelegram);
    this.ui = new TelegramUI(this._webApp, this._isInsideTelegram);
    this.storage = new TelegramStorage(this._webApp, this._isInsideTelegram);
    this.theme = new TelegramTheme(this._webApp, this._isInsideTelegram);
    this.viewport = new TelegramViewport(this._webApp, this._isInsideTelegram);

    // Apply initial configuration
    if (this._isInsideTelegram) {
      if (this._options.expandOnInit) {
        this._webApp.expand();
      }

      if (this._options.disableVerticalSwipes && this._webApp.disableVerticalSwipes) {
        this._webApp.disableVerticalSwipes();
      }

      if (this._options.headerColor) {
        this._webApp.setHeaderColor(this._options.headerColor);
      }

      if (this._options.backgroundColor) {
        this._webApp.setBackgroundColor(this._options.backgroundColor);
      }

      if (this._options.enableClosingConfirmation) {
        this.ui.enableClosingConfirmation();
      }
    }

    // Initialize sub-modules
    this.theme.init();
    this.viewport.init();

    // Signal ready
    this._signalReady();

    this._ready = true;

    console.log('[TelegramWebApp] Initialized', {
      insideTelegram: this._isInsideTelegram,
      platform: this.platform,
      version: this.version,
    });

    return this;
  }

  /**
   * Signal to Telegram that the app is ready to be displayed
   */
  _signalReady() {
    if (this._isInsideTelegram && this._webApp.ready) {
      this._webApp.ready();
    }
  }

  /**
   * Close the Web App
   */
  close() {
    if (this._isInsideTelegram) {
      this._webApp.close();
    } else {
      console.log('[TelegramWebApp] close() called in dev mode - no-op');
    }
  }

  /**
   * Destroy the instance and clean up event listeners
   */
  destroy() {
    if (this.theme) this.theme.destroy();
    if (this.viewport) this.viewport.destroy();
    if (this.ui) this.ui.destroy();
    this._ready = false;
  }
}
