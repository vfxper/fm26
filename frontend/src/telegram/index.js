/**
 * Telegram Web App Integration Module
 * Entry point that exports all Telegram-related classes and a convenience factory.
 *
 * Usage:
 *   import { createTelegramApp } from './telegram/index.js';
 *   const tg = createTelegramApp({ expandOnInit: true });
 *
 * Or import individual classes:
 *   import { TelegramWebApp, TelegramAuth, TelegramUI } from './telegram/index.js';
 */

export { TelegramWebApp } from './TelegramWebApp.js';
export { TelegramAuth } from './TelegramAuth.js';
export { TelegramUI } from './TelegramUI.js';
export { TelegramStorage } from './TelegramStorage.js';
export { TelegramTheme } from './TelegramTheme.js';
export { TelegramViewport } from './TelegramViewport.js';

import { TelegramWebApp } from './TelegramWebApp.js';

/**
 * Convenience factory to create and initialize a TelegramWebApp instance.
 * @param {import('./TelegramWebApp.js').TelegramWebAppOptions} [options]
 * @returns {TelegramWebApp} Initialized instance
 */
export function createTelegramApp(options = {}) {
  const app = new TelegramWebApp(options);
  app.init();
  return app;
}
