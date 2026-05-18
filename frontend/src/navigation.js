/**
 * Navigation Manager Module
 * Handles bottom navigation and page routing
 */

import { hapticFeedback } from './telegram-init.js';

export class NavigationManager {
  constructor() {
    this.currentPage = 'home';
    this.pages = new Map();
    this.navItems = [];
    
    this.init();
  }

  /**
   * Initialize navigation
   */
  init() {
    // Get navigation items
    this.navItems = Array.from(document.querySelectorAll('.nav-item'));
    
    // Set up click handlers
    this.navItems.forEach(item => {
      item.addEventListener('click', () => {
        const page = item.dataset.page;
        this.navigateTo(page);
      });
    });
    
    // Register default pages
    this.registerPage('home', () => this.renderHomePage());
    this.registerPage('squad', () => this.renderSquadPage());
    this.registerPage('tactics', () => this.renderTacticsPage());
    this.registerPage('transfers', () => this.renderTransfersPage());
    this.registerPage('match', () => this.renderMatchPage());
  }

  /**
   * Register a page renderer
   * @param {string} pageName - Page name
   * @param {Function} renderer - Page render function
   */
  registerPage(pageName, renderer) {
    this.pages.set(pageName, renderer);
  }

  /**
   * Navigate to a page
   * @param {string} pageName - Page name
   */
  navigateTo(pageName) {
    if (this.currentPage === pageName) return;
    
    // Haptic feedback
    hapticFeedback('selection');
    
    // Update active nav item
    this.navItems.forEach(item => {
      if (item.dataset.page === pageName) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
    
    // Render page
    const renderer = this.pages.get(pageName);
    if (renderer) {
      renderer();
      this.currentPage = pageName;
    } else {
      console.warn(`No renderer found for page: ${pageName}`);
    }
  }

  /**
   * Render home page
   */
  renderHomePage() {
    console.log('Rendering home page');
    // TODO: Implement home page UI
    this.showPlaceholder('Home', '🏠', 'Dashboard with club overview, upcoming matches, and notifications');
  }

  /**
   * Render squad page
   */
  renderSquadPage() {
    console.log('Rendering squad page');
    // TODO: Implement squad page UI
    this.showPlaceholder('Squad', '👥', 'View and manage your squad, player contracts, and morale');
  }

  /**
   * Render tactics page
   */
  renderTacticsPage() {
    console.log('Rendering tactics page');
    // TODO: Implement tactics page UI
    this.showPlaceholder('Tactics', '📋', 'Set up formations, tactics, and player roles');
  }

  /**
   * Render transfers page
   */
  renderTransfersPage() {
    console.log('Rendering transfers page');
    // TODO: Implement transfers page UI
    this.showPlaceholder('Transfers', '💰', 'Search for players, make bids, and manage transfers');
  }

  /**
   * Render match page
   */
  renderMatchPage() {
    console.log('Rendering match page');
    // TODO: Implement match page UI
    this.showPlaceholder('Match', '⚽', 'View upcoming matches and watch live 2D match simulations');
  }

  /**
   * Show placeholder content for unimplemented pages
   * @param {string} title - Page title
   * @param {string} icon - Page icon
   * @param {string} description - Page description
   */
  showPlaceholder(title, icon, description) {
    const overlay = document.getElementById('ui-overlay');
    
    overlay.innerHTML = `
      <div style="
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100%;
        padding: 20px;
        text-align: center;
        background-color: rgba(45, 80, 22, 0.95);
        color: white;
      ">
        <div style="font-size: 64px; margin-bottom: 20px;">${icon}</div>
        <h2 style="font-size: 24px; margin-bottom: 10px;">${title}</h2>
        <p style="font-size: 16px; opacity: 0.8; max-width: 300px;">${description}</p>
        <p style="font-size: 14px; opacity: 0.6; margin-top: 20px;">Coming soon...</p>
      </div>
    `;
  }

  /**
   * Clear overlay content
   */
  clearOverlay() {
    const overlay = document.getElementById('ui-overlay');
    overlay.innerHTML = '';
  }

  /**
   * Show notification badge on nav item
   * @param {string} pageName - Page name
   * @param {number} count - Notification count
   */
  showNotificationBadge(pageName, count) {
    const navItem = this.navItems.find(item => item.dataset.page === pageName);
    if (!navItem) return;
    
    // Remove existing badge
    const existingBadge = navItem.querySelector('.notification-badge');
    if (existingBadge) {
      existingBadge.remove();
    }
    
    // Add new badge if count > 0
    if (count > 0) {
      const badge = document.createElement('div');
      badge.className = 'notification-badge';
      badge.textContent = count > 99 ? '99+' : count;
      navItem.style.position = 'relative';
      navItem.appendChild(badge);
    }
  }

  /**
   * Hide notification badge on nav item
   * @param {string} pageName - Page name
   */
  hideNotificationBadge(pageName) {
    this.showNotificationBadge(pageName, 0);
  }
}
