/**
 * Telegram Web App initialization module
 * Handles Telegram Web App SDK setup and configuration
 */

/**
 * Initialize Telegram Web App
 * @returns {Object} Telegram Web App instance
 */
export function initTelegramWebApp() {
  // Check if Telegram Web App is available
  if (!window.Telegram || !window.Telegram.WebApp) {
    console.warn('Telegram Web App SDK not available');
    return null;
  }

  const tg = window.Telegram.WebApp;

  // Expand the Web App to full height
  tg.expand();

  // Enable closing confirmation
  tg.enableClosingConfirmation();

  // Set header color to match pitch green
  tg.setHeaderColor('#2d5016');

  // Set background color
  tg.setBackgroundColor('#2d5016');

  // Ready signal
  tg.ready();

  console.log('Telegram Web App initialized:', {
    version: tg.version,
    platform: tg.platform,
    colorScheme: tg.colorScheme,
    viewportHeight: tg.viewportHeight,
    viewportStableHeight: tg.viewportStableHeight,
    isExpanded: tg.isExpanded,
    user: tg.initDataUnsafe?.user,
  });

  // Set up theme change listener
  tg.onEvent('themeChanged', () => {
    console.log('Theme changed:', tg.colorScheme);
    applyTheme(tg.colorScheme);
  });

  // Set up viewport change listener
  tg.onEvent('viewportChanged', ({ isStateStable }) => {
    console.log('Viewport changed:', {
      height: tg.viewportHeight,
      stableHeight: tg.viewportStableHeight,
      isStateStable,
    });
    
    // Trigger resize event for canvas
    if (isStateStable) {
      window.dispatchEvent(new Event('resize'));
    }
  });

  // Apply initial theme
  applyTheme(tg.colorScheme);

  return tg;
}

/**
 * Apply theme based on Telegram color scheme
 * @param {string} colorScheme - 'light' or 'dark'
 */
function applyTheme(colorScheme) {
  document.documentElement.setAttribute('data-theme', colorScheme);
  
  // Update meta theme-color
  const metaThemeColor = document.querySelector('meta[name="theme-color"]');
  if (metaThemeColor) {
    metaThemeColor.setAttribute('content', colorScheme === 'dark' ? '#1f3a0f' : '#2d5016');
  }
}

/**
 * Show Telegram main button
 * @param {string} text - Button text
 * @param {Function} onClick - Click handler
 */
export function showMainButton(text, onClick) {
  const tg = window.Telegram?.WebApp;
  if (!tg) return;

  tg.MainButton.setText(text);
  tg.MainButton.show();
  tg.MainButton.onClick(onClick);
}

/**
 * Hide Telegram main button
 */
export function hideMainButton() {
  const tg = window.Telegram?.WebApp;
  if (!tg) return;

  tg.MainButton.hide();
}

/**
 * Show Telegram back button
 * @param {Function} onClick - Click handler
 */
export function showBackButton(onClick) {
  const tg = window.Telegram?.WebApp;
  if (!tg) return;

  tg.BackButton.show();
  tg.BackButton.onClick(onClick);
}

/**
 * Hide Telegram back button
 */
export function hideBackButton() {
  const tg = window.Telegram?.WebApp;
  if (!tg) return;

  tg.BackButton.hide();
}

/**
 * Show Telegram popup
 * @param {Object} params - Popup parameters
 * @param {string} params.title - Popup title
 * @param {string} params.message - Popup message
 * @param {Array} params.buttons - Array of button objects
 * @returns {Promise<string>} Selected button id
 */
export function showPopup(params) {
  const tg = window.Telegram?.WebApp;
  if (!tg) {
    return Promise.reject(new Error('Telegram Web App not available'));
  }

  return new Promise((resolve) => {
    tg.showPopup(params, (buttonId) => {
      resolve(buttonId);
    });
  });
}

/**
 * Show Telegram alert
 * @param {string} message - Alert message
 * @returns {Promise<void>}
 */
export function showAlert(message) {
  const tg = window.Telegram?.WebApp;
  if (!tg) {
    alert(message);
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    tg.showAlert(message, () => {
      resolve();
    });
  });
}

/**
 * Show Telegram confirm dialog
 * @param {string} message - Confirm message
 * @returns {Promise<boolean>} True if confirmed, false otherwise
 */
export function showConfirm(message) {
  const tg = window.Telegram?.WebApp;
  if (!tg) {
    return Promise.resolve(confirm(message));
  }

  return new Promise((resolve) => {
    tg.showConfirm(message, (confirmed) => {
      resolve(confirmed);
    });
  });
}

/**
 * Trigger haptic feedback
 * @param {string} type - Feedback type: 'impact', 'notification', 'selection'
 * @param {string} style - Impact style: 'light', 'medium', 'heavy', 'rigid', 'soft'
 */
export function hapticFeedback(type = 'impact', style = 'medium') {
  const tg = window.Telegram?.WebApp;
  if (!tg || !tg.HapticFeedback) return;

  switch (type) {
    case 'impact':
      tg.HapticFeedback.impactOccurred(style);
      break;
    case 'notification':
      tg.HapticFeedback.notificationOccurred(style); // 'error', 'success', 'warning'
      break;
    case 'selection':
      tg.HapticFeedback.selectionChanged();
      break;
  }
}

/**
 * Close the Web App
 */
export function closeWebApp() {
  const tg = window.Telegram?.WebApp;
  if (!tg) return;

  tg.close();
}

/**
 * Get Telegram user data
 * @returns {Object|null} User data or null if not available
 */
export function getTelegramUser() {
  const tg = window.Telegram?.WebApp;
  if (!tg) return null;

  return tg.initDataUnsafe?.user || null;
}

/**
 * Get Telegram init data (for backend authentication)
 * @returns {string} Init data string
 */
export function getTelegramInitData() {
  const tg = window.Telegram?.WebApp;
  if (!tg) return '';

  return tg.initData || '';
}
