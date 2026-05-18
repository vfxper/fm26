/**
 * TelegramStorage.js - CloudStorage wrapper for settings persistence
 * Provides an async key-value storage API using Telegram's CloudStorage.
 * Falls back to localStorage when running outside Telegram.
 */

const STORAGE_PREFIX = 'tfm_';

export class TelegramStorage {
  /**
   * @param {object|null} webApp - The Telegram WebApp instance
   * @param {boolean} isInsideTelegram - Whether running inside Telegram
   */
  constructor(webApp, isInsideTelegram) {
    this._webApp = webApp;
    this._isInsideTelegram = isInsideTelegram;
  }

  /**
   * Check if CloudStorage is available.
   * @returns {boolean}
   */
  isAvailable() {
    return this._isInsideTelegram && !!this._webApp?.CloudStorage;
  }

  /**
   * Store a value by key.
   * @param {string} key - Storage key (max 128 chars after prefix)
   * @param {string} value - Value to store (max 4096 chars)
   * @returns {Promise<boolean>} Whether the operation succeeded
   */
  async setItem(key, value) {
    const prefixedKey = STORAGE_PREFIX + key;

    if (this.isAvailable()) {
      return new Promise((resolve) => {
        this._webApp.CloudStorage.setItem(prefixedKey, value, (error, success) => {
          if (error) {
            console.error('[TelegramStorage] setItem error:', error);
            resolve(false);
          } else {
            resolve(true);
          }
        });
      });
    }

    // Fallback to localStorage
    try {
      localStorage.setItem(prefixedKey, value);
      return true;
    } catch (e) {
      console.error('[TelegramStorage] localStorage setItem error:', e);
      return false;
    }
  }

  /**
   * Retrieve a value by key.
   * @param {string} key - Storage key
   * @returns {Promise<string|null>} The stored value, or null if not found
   */
  async getItem(key) {
    const prefixedKey = STORAGE_PREFIX + key;

    if (this.isAvailable()) {
      return new Promise((resolve) => {
        this._webApp.CloudStorage.getItem(prefixedKey, (error, value) => {
          if (error) {
            console.error('[TelegramStorage] getItem error:', error);
            resolve(null);
          } else {
            // CloudStorage returns empty string for non-existent keys
            resolve(value || null);
          }
        });
      });
    }

    // Fallback to localStorage
    try {
      return localStorage.getItem(prefixedKey);
    } catch (e) {
      console.error('[TelegramStorage] localStorage getItem error:', e);
      return null;
    }
  }

  /**
   * Retrieve multiple values by keys.
   * @param {string[]} keys - Array of storage keys
   * @returns {Promise<Object<string, string|null>>} Map of key -> value
   */
  async getItems(keys) {
    const prefixedKeys = keys.map((k) => STORAGE_PREFIX + k);

    if (this.isAvailable()) {
      return new Promise((resolve) => {
        this._webApp.CloudStorage.getItems(prefixedKeys, (error, values) => {
          if (error) {
            console.error('[TelegramStorage] getItems error:', error);
            // Return null for all keys on error
            const result = {};
            keys.forEach((k) => (result[k] = null));
            resolve(result);
          } else {
            // Map back to unprefixed keys
            const result = {};
            keys.forEach((k) => {
              const val = values[STORAGE_PREFIX + k];
              result[k] = val || null;
            });
            resolve(result);
          }
        });
      });
    }

    // Fallback to localStorage
    const result = {};
    keys.forEach((k) => {
      try {
        result[k] = localStorage.getItem(STORAGE_PREFIX + k);
      } catch (e) {
        result[k] = null;
      }
    });
    return result;
  }

  /**
   * Remove a value by key.
   * @param {string} key - Storage key
   * @returns {Promise<boolean>} Whether the operation succeeded
   */
  async removeItem(key) {
    const prefixedKey = STORAGE_PREFIX + key;

    if (this.isAvailable()) {
      return new Promise((resolve) => {
        this._webApp.CloudStorage.removeItem(prefixedKey, (error, success) => {
          if (error) {
            console.error('[TelegramStorage] removeItem error:', error);
            resolve(false);
          } else {
            resolve(true);
          }
        });
      });
    }

    // Fallback to localStorage
    try {
      localStorage.removeItem(prefixedKey);
      return true;
    } catch (e) {
      console.error('[TelegramStorage] localStorage removeItem error:', e);
      return false;
    }
  }

  /**
   * Remove multiple values by keys.
   * @param {string[]} keys - Array of storage keys
   * @returns {Promise<boolean>} Whether the operation succeeded
   */
  async removeItems(keys) {
    const prefixedKeys = keys.map((k) => STORAGE_PREFIX + k);

    if (this.isAvailable()) {
      return new Promise((resolve) => {
        this._webApp.CloudStorage.removeItems(prefixedKeys, (error, success) => {
          if (error) {
            console.error('[TelegramStorage] removeItems error:', error);
            resolve(false);
          } else {
            resolve(true);
          }
        });
      });
    }

    // Fallback to localStorage
    try {
      prefixedKeys.forEach((k) => localStorage.removeItem(k));
      return true;
    } catch (e) {
      console.error('[TelegramStorage] localStorage removeItems error:', e);
      return false;
    }
  }

  /**
   * Get all stored keys (without prefix).
   * @returns {Promise<string[]>} Array of keys
   */
  async getKeys() {
    if (this.isAvailable()) {
      return new Promise((resolve) => {
        this._webApp.CloudStorage.getKeys((error, keys) => {
          if (error) {
            console.error('[TelegramStorage] getKeys error:', error);
            resolve([]);
          } else {
            // Strip prefix from keys
            const unprefixed = (keys || [])
              .filter((k) => k.startsWith(STORAGE_PREFIX))
              .map((k) => k.slice(STORAGE_PREFIX.length));
            resolve(unprefixed);
          }
        });
      });
    }

    // Fallback to localStorage
    try {
      const allKeys = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(STORAGE_PREFIX)) {
          allKeys.push(key.slice(STORAGE_PREFIX.length));
        }
      }
      return allKeys;
    } catch (e) {
      console.error('[TelegramStorage] localStorage getKeys error:', e);
      return [];
    }
  }

  // ─── Convenience Methods for JSON data ────────────────────────────────────────

  /**
   * Store a JSON-serializable value.
   * @param {string} key - Storage key
   * @param {*} value - Value to serialize and store
   * @returns {Promise<boolean>}
   */
  async setJSON(key, value) {
    try {
      const serialized = JSON.stringify(value);
      return await this.setItem(key, serialized);
    } catch (e) {
      console.error('[TelegramStorage] setJSON serialization error:', e);
      return false;
    }
  }

  /**
   * Retrieve and parse a JSON value.
   * @param {string} key - Storage key
   * @param {*} [defaultValue=null] - Default value if key not found or parse fails
   * @returns {Promise<*>} Parsed value or defaultValue
   */
  async getJSON(key, defaultValue = null) {
    const raw = await this.getItem(key);
    if (raw === null) return defaultValue;

    try {
      return JSON.parse(raw);
    } catch (e) {
      console.error('[TelegramStorage] getJSON parse error:', e);
      return defaultValue;
    }
  }
}
