/**
 * TelegramUI.js - MainButton, BackButton, HapticFeedback, and closing confirmation
 * Provides a clean interface for Telegram UI controls with dev fallbacks.
 */

/**
 * @typedef {Object} MainButtonParams
 * @property {string} text - Button text
 * @property {string} [color] - Button background color
 * @property {string} [textColor] - Button text color
 * @property {boolean} [isActive=true] - Whether the button is active
 * @property {boolean} [isVisible=true] - Whether the button is visible
 */

export class TelegramUI {
  /**
   * @param {object|null} webApp - The Telegram WebApp instance
   * @param {boolean} isInsideTelegram - Whether running inside Telegram
   */
  constructor(webApp, isInsideTelegram) {
    this._webApp = webApp;
    this._isInsideTelegram = isInsideTelegram;

    /** @type {Function|null} */
    this._mainButtonCallback = null;

    /** @type {Function|null} */
    this._backButtonCallback = null;

    /** @type {boolean} */
    this._closingConfirmationEnabled = false;
  }

  // ─── MainButton ───────────────────────────────────────────────────────────────

  /**
   * Show the MainButton with specified text and optional click handler.
   * @param {string} text - Button text
   * @param {Function} [onClick] - Click handler
   * @param {Object} [options] - Additional options
   * @param {string} [options.color] - Button background color
   * @param {string} [options.textColor] - Button text color
   */
  showMainButton(text, onClick, options = {}) {
    if (this._isInsideTelegram && this._webApp?.MainButton) {
      const btn = this._webApp.MainButton;

      btn.setText(text);

      if (options.color) btn.color = options.color;
      if (options.textColor) btn.textColor = options.textColor;

      // Remove previous handler if any
      if (this._mainButtonCallback) {
        btn.offClick(this._mainButtonCallback);
      }

      if (onClick) {
        this._mainButtonCallback = onClick;
        btn.onClick(onClick);
      }

      btn.show();
    } else {
      console.log(`[TelegramUI] MainButton.show("${text}")`);
      this._mainButtonCallback = onClick;
    }
  }

  /**
   * Hide the MainButton.
   */
  hideMainButton() {
    if (this._isInsideTelegram && this._webApp?.MainButton) {
      const btn = this._webApp.MainButton;
      if (this._mainButtonCallback) {
        btn.offClick(this._mainButtonCallback);
        this._mainButtonCallback = null;
      }
      btn.hide();
    } else {
      console.log('[TelegramUI] MainButton.hide()');
      this._mainButtonCallback = null;
    }
  }

  /**
   * Set the MainButton text without changing visibility.
   * @param {string} text
   */
  setMainButtonText(text) {
    if (this._isInsideTelegram && this._webApp?.MainButton) {
      this._webApp.MainButton.setText(text);
    }
  }

  /**
   * Set the MainButton color.
   * @param {string} color - CSS color value
   */
  setMainButtonColor(color) {
    if (this._isInsideTelegram && this._webApp?.MainButton) {
      this._webApp.MainButton.color = color;
    }
  }

  /**
   * Show loading indicator on MainButton.
   * @param {boolean} [leaveActive=false] - Whether to keep the button active while loading
   */
  showMainButtonProgress(leaveActive = false) {
    if (this._isInsideTelegram && this._webApp?.MainButton) {
      this._webApp.MainButton.showProgress(leaveActive);
    } else {
      console.log('[TelegramUI] MainButton.showProgress()');
    }
  }

  /**
   * Hide loading indicator on MainButton.
   */
  hideMainButtonProgress() {
    if (this._isInsideTelegram && this._webApp?.MainButton) {
      this._webApp.MainButton.hideProgress();
    } else {
      console.log('[TelegramUI] MainButton.hideProgress()');
    }
  }

  /**
   * Enable or disable the MainButton.
   * @param {boolean} enabled
   */
  setMainButtonEnabled(enabled) {
    if (this._isInsideTelegram && this._webApp?.MainButton) {
      if (enabled) {
        this._webApp.MainButton.enable();
      } else {
        this._webApp.MainButton.disable();
      }
    }
  }

  /**
   * Check if MainButton is currently visible.
   * @returns {boolean}
   */
  isMainButtonVisible() {
    if (this._isInsideTelegram && this._webApp?.MainButton) {
      return this._webApp.MainButton.isVisible;
    }
    return false;
  }

  // ─── BackButton ───────────────────────────────────────────────────────────────

  /**
   * Show the BackButton with a click handler.
   * @param {Function} onClick - Click handler
   */
  showBackButton(onClick) {
    if (this._isInsideTelegram && this._webApp?.BackButton) {
      const btn = this._webApp.BackButton;

      // Remove previous handler
      if (this._backButtonCallback) {
        btn.offClick(this._backButtonCallback);
      }

      this._backButtonCallback = onClick;
      btn.onClick(onClick);
      btn.show();
    } else {
      console.log('[TelegramUI] BackButton.show()');
      this._backButtonCallback = onClick;
    }
  }

  /**
   * Hide the BackButton.
   */
  hideBackButton() {
    if (this._isInsideTelegram && this._webApp?.BackButton) {
      const btn = this._webApp.BackButton;
      if (this._backButtonCallback) {
        btn.offClick(this._backButtonCallback);
        this._backButtonCallback = null;
      }
      btn.hide();
    } else {
      console.log('[TelegramUI] BackButton.hide()');
      this._backButtonCallback = null;
    }
  }

  /**
   * Check if BackButton is currently visible.
   * @returns {boolean}
   */
  isBackButtonVisible() {
    if (this._isInsideTelegram && this._webApp?.BackButton) {
      return this._webApp.BackButton.isVisible;
    }
    return false;
  }

  // ─── HapticFeedback ───────────────────────────────────────────────────────────

  /**
   * Trigger impact haptic feedback.
   * @param {'light'|'medium'|'heavy'|'rigid'|'soft'} [style='medium'] - Impact style
   */
  impactFeedback(style = 'medium') {
    if (this._isInsideTelegram && this._webApp?.HapticFeedback) {
      this._webApp.HapticFeedback.impactOccurred(style);
    }
  }

  /**
   * Trigger notification haptic feedback.
   * @param {'error'|'success'|'warning'} type - Notification type
   */
  notificationFeedback(type) {
    if (this._isInsideTelegram && this._webApp?.HapticFeedback) {
      this._webApp.HapticFeedback.notificationOccurred(type);
    }
  }

  /**
   * Trigger selection change haptic feedback.
   */
  selectionFeedback() {
    if (this._isInsideTelegram && this._webApp?.HapticFeedback) {
      this._webApp.HapticFeedback.selectionChanged();
    }
  }

  // ─── Closing Confirmation ─────────────────────────────────────────────────────

  /**
   * Enable closing confirmation dialog.
   * When enabled, the user will be asked to confirm before closing the app.
   */
  enableClosingConfirmation() {
    this._closingConfirmationEnabled = true;
    if (this._isInsideTelegram && this._webApp?.enableClosingConfirmation) {
      this._webApp.enableClosingConfirmation();
    }
  }

  /**
   * Disable closing confirmation dialog.
   */
  disableClosingConfirmation() {
    this._closingConfirmationEnabled = false;
    if (this._isInsideTelegram && this._webApp?.disableClosingConfirmation) {
      this._webApp.disableClosingConfirmation();
    }
  }

  /**
   * Check if closing confirmation is enabled.
   * @returns {boolean}
   */
  isClosingConfirmationEnabled() {
    if (this._isInsideTelegram && this._webApp) {
      return !!this._webApp.isClosingConfirmationEnabled;
    }
    return this._closingConfirmationEnabled;
  }

  // ─── Popups & Alerts ──────────────────────────────────────────────────────────

  /**
   * Show a native Telegram popup.
   * @param {Object} params
   * @param {string} [params.title] - Popup title (max 64 chars)
   * @param {string} params.message - Popup message (max 256 chars)
   * @param {Array<{id: string, type?: string, text?: string}>} [params.buttons] - Buttons
   * @returns {Promise<string>} The ID of the pressed button
   */
  showPopup(params) {
    if (this._isInsideTelegram && this._webApp?.showPopup) {
      return new Promise((resolve) => {
        this._webApp.showPopup(params, (buttonId) => {
          resolve(buttonId);
        });
      });
    }
    // Dev fallback: log and resolve with first button id
    console.log('[TelegramUI] showPopup:', params);
    const firstButtonId = params.buttons?.[0]?.id || 'ok';
    return Promise.resolve(firstButtonId);
  }

  /**
   * Show a native Telegram alert.
   * @param {string} message - Alert message
   * @returns {Promise<void>}
   */
  showAlert(message) {
    if (this._isInsideTelegram && this._webApp?.showAlert) {
      return new Promise((resolve) => {
        this._webApp.showAlert(message, resolve);
      });
    }
    console.log('[TelegramUI] alert:', message);
    return Promise.resolve();
  }

  /**
   * Show a native Telegram confirm dialog.
   * @param {string} message - Confirm message
   * @returns {Promise<boolean>}
   */
  showConfirm(message) {
    if (this._isInsideTelegram && this._webApp?.showConfirm) {
      return new Promise((resolve) => {
        this._webApp.showConfirm(message, (confirmed) => {
          resolve(confirmed);
        });
      });
    }
    console.log('[TelegramUI] confirm:', message);
    return Promise.resolve(true);
  }

  // ─── Cleanup ──────────────────────────────────────────────────────────────────

  /**
   * Clean up event listeners and handlers.
   */
  destroy() {
    this.hideMainButton();
    this.hideBackButton();
  }
}
