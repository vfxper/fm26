/**
 * TelegramAuth.js - Handles initData authentication and user ID extraction
 * Provides methods to access Telegram user data and the raw initData string
 * for backend authentication.
 */

/**
 * @typedef {Object} TelegramUser
 * @property {number} id - Telegram user ID
 * @property {string} [first_name] - User's first name
 * @property {string} [last_name] - User's last name
 * @property {string} [username] - User's username
 * @property {string} [language_code] - User's language code (e.g., 'en', 'ru')
 * @property {boolean} [is_premium] - Whether the user has Telegram Premium
 * @property {string} [photo_url] - URL of the user's profile photo
 */

export class TelegramAuth {
  /**
   * @param {object|null} webApp - The Telegram WebApp instance
   * @param {boolean} isInsideTelegram - Whether running inside Telegram
   */
  constructor(webApp, isInsideTelegram) {
    this._webApp = webApp;
    this._isInsideTelegram = isInsideTelegram;
  }

  /**
   * Get the raw initData string for backend validation.
   * The backend should validate this using HMAC-SHA256 with the bot token.
   * @returns {string} The initData query string, or empty string in dev mode
   */
  getInitData() {
    if (this._isInsideTelegram && this._webApp) {
      return this._webApp.initData || '';
    }
    return '';
  }

  /**
   * Get the parsed (unsafe/unvalidated) init data object.
   * WARNING: This data is NOT validated on the client side.
   * Always validate initData on the backend before trusting it.
   * @returns {object} Parsed initData or empty object
   */
  getInitDataUnsafe() {
    if (this._isInsideTelegram && this._webApp) {
      return this._webApp.initDataUnsafe || {};
    }
    return this._getDevFallback();
  }

  /**
   * Extract the Telegram user ID from initData.
   * @returns {number|null} The user's Telegram ID, or null if unavailable
   */
  getUserId() {
    const data = this.getInitDataUnsafe();
    return data?.user?.id || null;
  }

  /**
   * Get the full Telegram user object from initData.
   * @returns {TelegramUser|null} User object or null
   */
  getUser() {
    const data = this.getInitDataUnsafe();
    return data?.user || null;
  }

  /**
   * Get the user's first name.
   * @returns {string} First name or 'Player' as fallback
   */
  getFirstName() {
    const user = this.getUser();
    return user?.first_name || 'Player';
  }

  /**
   * Get the user's full name.
   * @returns {string} Full name or 'Player' as fallback
   */
  getFullName() {
    const user = this.getUser();
    if (!user) return 'Player';
    return [user.first_name, user.last_name].filter(Boolean).join(' ') || 'Player';
  }

  /**
   * Get the user's language code.
   * @returns {string} Language code (e.g., 'en', 'ru') or 'en' as default
   */
  getLanguageCode() {
    const user = this.getUser();
    return user?.language_code || 'en';
  }

  /**
   * Get the user's username (without @).
   * @returns {string|null} Username or null
   */
  getUsername() {
    const user = this.getUser();
    return user?.username || null;
  }

  /**
   * Check if the user has Telegram Premium.
   * @returns {boolean}
   */
  isPremium() {
    const user = this.getUser();
    return !!user?.is_premium;
  }

  /**
   * Get the user's profile photo URL.
   * @returns {string|null} Photo URL or null
   */
  getPhotoUrl() {
    const user = this.getUser();
    return user?.photo_url || null;
  }

  /**
   * Get the chat instance identifier (for inline mode).
   * @returns {string|null}
   */
  getChatInstance() {
    const data = this.getInitDataUnsafe();
    return data?.chat_instance || null;
  }

  /**
   * Get the start_param passed via the bot link.
   * @returns {string|null}
   */
  getStartParam() {
    const data = this.getInitDataUnsafe();
    return data?.start_param || null;
  }

  /**
   * Get the auth_date timestamp from initData.
   * @returns {number|null} Unix timestamp or null
   */
  getAuthDate() {
    const data = this.getInitDataUnsafe();
    return data?.auth_date || null;
  }

  /**
   * Check if authentication data is available.
   * @returns {boolean}
   */
  isAuthenticated() {
    return this.getUserId() !== null;
  }

  /**
   * Build an authorization header value for API requests.
   * @returns {string} Header value in format "tma <initData>"
   */
  getAuthHeader() {
    const initData = this.getInitData();
    if (!initData) return '';
    return `tma ${initData}`;
  }

  /**
   * Development fallback data for testing outside Telegram.
   * @returns {object}
   * @private
   */
  _getDevFallback() {
    return {
      user: {
        id: 12345678,
        first_name: 'Dev',
        last_name: 'Player',
        username: 'dev_player',
        language_code: 'en',
        is_premium: false,
      },
      auth_date: Math.floor(Date.now() / 1000),
      hash: 'dev_mode_hash',
    };
  }
}
