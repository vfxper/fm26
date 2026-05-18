/**
 * BottomNav.js - Bottom navigation bar with 5 tabs
 * Touch-friendly (44x44px minimum), notification badges, SVG icons
 */

import { hapticFeedback } from '../telegram-init.js';

/** SVG icon paths for each tab */
const ICONS = {
  home: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
  squad: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
  tactics: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>`,
  transfers: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
  match: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>`,
};

const TAB_CONFIG = [
  { id: 'home', label: 'Home', icon: ICONS.home },
  { id: 'squad', label: 'Squad', icon: ICONS.squad },
  { id: 'tactics', label: 'Tactics', icon: ICONS.tactics },
  { id: 'transfers', label: 'Transfers', icon: ICONS.transfers },
  { id: 'match', label: 'Match', icon: ICONS.match },
];

export class BottomNav {
  /**
   * @param {Object} options
   * @param {Function} options.onTabChange - Callback when tab changes
   */
  constructor(options = {}) {
    this.onTabChange = options.onTabChange || null;
    this.activeTab = 'home';
    this.badges = new Map();
    this.element = null;
    this._tabElements = new Map();
  }

  /**
   * Render the bottom navigation bar
   * @returns {HTMLElement}
   */
  render() {
    const nav = document.createElement('nav');
    nav.id = 'bottom-nav';
    nav.className = 'bottom-nav';
    nav.setAttribute('role', 'tablist');
    nav.setAttribute('aria-label', 'Main navigation');

    TAB_CONFIG.forEach((tab) => {
      const button = document.createElement('button');
      button.className = `bottom-nav__tab${tab.id === this.activeTab ? ' bottom-nav__tab--active' : ''}`;
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-selected', tab.id === this.activeTab ? 'true' : 'false');
      button.setAttribute('aria-label', tab.label);
      button.setAttribute('data-tab', tab.id);
      button.type = 'button';

      button.innerHTML = `
        <span class="bottom-nav__icon" aria-hidden="true">${tab.icon}</span>
        <span class="bottom-nav__label">${tab.label}</span>
        <span class="bottom-nav__badge hidden" aria-live="polite"></span>
      `;

      button.addEventListener('click', () => this._handleTabClick(tab.id));

      this._tabElements.set(tab.id, button);
      nav.appendChild(button);
    });

    this.element = nav;

    // Restore any pending badges
    this.badges.forEach((count, tabId) => {
      this._updateBadgeDOM(tabId, count);
    });

    return nav;
  }

  /**
   * Set the active tab
   * @param {string} tabId
   */
  setActive(tabId) {
    if (this.activeTab === tabId) return;
    this.activeTab = tabId;

    this._tabElements.forEach((el, id) => {
      const isActive = id === tabId;
      el.classList.toggle('bottom-nav__tab--active', isActive);
      el.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
  }

  /**
   * Set notification badge count
   * @param {string} tabId
   * @param {number} count - 0 to hide
   */
  setBadge(tabId, count) {
    this.badges.set(tabId, count);
    this._updateBadgeDOM(tabId, count);
  }

  /**
   * Clear all badges
   */
  clearBadges() {
    this.badges.clear();
    this._tabElements.forEach((_, id) => this._updateBadgeDOM(id, 0));
  }

  /**
   * Destroy and clean up
   */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this._tabElements.clear();
    this.element = null;
  }

  // --- Private ---

  _handleTabClick(tabId) {
    if (tabId === this.activeTab) return;
    hapticFeedback('selection');
    this.setActive(tabId);
    if (this.onTabChange) {
      this.onTabChange(tabId);
    }
  }

  _updateBadgeDOM(tabId, count) {
    const tabEl = this._tabElements.get(tabId);
    if (!tabEl) return;

    const badge = tabEl.querySelector('.bottom-nav__badge');
    if (!badge) return;

    if (count > 0) {
      badge.textContent = count > 99 ? '99+' : String(count);
      badge.classList.remove('hidden');
      badge.setAttribute('aria-label', `${count} notifications`);
    } else {
      badge.textContent = '';
      badge.classList.add('hidden');
      badge.removeAttribute('aria-label');
    }
  }
}
