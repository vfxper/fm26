/**
 * Router.js - Simple SPA router with screen management
 * Handles navigation, scroll position restoration, swipe gestures, and history
 */

import { hapticFeedback } from '../telegram-init.js';

export class Router {
  constructor(container, options = {}) {
    /** @type {HTMLElement} */
    this.container = container;

    /** @type {Map<string, {render: Function, destroy?: Function}>} */
    this.routes = new Map();

    /** @type {string|null} */
    this.currentRoute = null;

    /** @type {Map<string, number>} scroll positions per route */
    this.scrollPositions = new Map();

    /** @type {string[]} navigation history stack */
    this.history = [];

    /** @type {boolean} */
    this.isTransitioning = false;

    // Swipe navigation
    this.swipeEnabled = options.swipeEnabled !== false;
    this.swipeThreshold = options.swipeThreshold || 50;
    this.tabOrder = options.tabOrder || [];

    // Touch tracking
    this._touchStartX = 0;
    this._touchStartY = 0;
    this._touchStartTime = 0;
    this._isSwiping = false;

    /** @type {Function|null} */
    this.onNavigate = options.onNavigate || null;

    if (this.swipeEnabled) {
      this._initSwipeGestures();
    }
  }

  /**
   * Register a route
   * @param {string} name - Route name
   * @param {Function} render - Render function returning HTMLElement or string
   * @param {Function} [destroy] - Cleanup function called when leaving route
   */
  register(name, render, destroy) {
    this.routes.set(name, { render, destroy });
  }

  /**
   * Navigate to a route
   * @param {string} name - Route name
   * @param {Object} [params] - Route parameters
   * @param {boolean} [pushHistory=true] - Whether to push to history
   * @returns {boolean} Whether navigation succeeded
   */
  navigate(name, params = {}, pushHistory = true) {
    if (this.isTransitioning) return false;
    if (this.currentRoute === name && !params._force) return false;

    const route = this.routes.get(name);
    if (!route) {
      console.warn(`[Router] Route not found: ${name}`);
      return false;
    }

    this.isTransitioning = true;

    // Save scroll position of current route
    if (this.currentRoute) {
      this._saveScrollPosition();
    }

    // Destroy current route
    if (this.currentRoute) {
      const currentRouteConfig = this.routes.get(this.currentRoute);
      if (currentRouteConfig && currentRouteConfig.destroy) {
        currentRouteConfig.destroy();
      }
    }

    // Push to history
    if (pushHistory && this.currentRoute) {
      this.history.push(this.currentRoute);
    }

    // Render new route
    const previousRoute = this.currentRoute;
    this.currentRoute = name;

    try {
      const content = route.render(params);

      // Clear container
      this.container.innerHTML = '';

      if (content instanceof HTMLElement) {
        this.container.appendChild(content);
      } else if (typeof content === 'string') {
        this.container.innerHTML = content;
      }

      // Restore scroll position
      this._restoreScrollPosition(name);

      // Notify listeners
      if (this.onNavigate) {
        this.onNavigate(name, previousRoute);
      }

      // Haptic feedback
      hapticFeedback('selection');
    } catch (error) {
      console.error(`[Router] Error rendering route ${name}:`, error);
    }

    this.isTransitioning = false;
    return true;
  }

  /**
   * Navigate back in history
   * @returns {boolean} Whether back navigation succeeded
   */
  back() {
    if (this.history.length === 0) return false;
    const previousRoute = this.history.pop();
    return this.navigate(previousRoute, {}, false);
  }

  /**
   * Check if can go back
   * @returns {boolean}
   */
  canGoBack() {
    return this.history.length > 0;
  }

  /**
   * Get current route name
   * @returns {string|null}
   */
  getCurrentRoute() {
    return this.currentRoute;
  }

  // --- Private methods ---

  _saveScrollPosition() {
    const scrollable = this.container.querySelector('[data-scrollable]') || this.container;
    this.scrollPositions.set(this.currentRoute, scrollable.scrollTop || 0);
  }

  _restoreScrollPosition(routeName) {
    const savedPosition = this.scrollPositions.get(routeName);
    if (savedPosition != null) {
      requestAnimationFrame(() => {
        const scrollable = this.container.querySelector('[data-scrollable]') || this.container;
        scrollable.scrollTop = savedPosition;
      });
    }
  }

  _initSwipeGestures() {
    this.container.addEventListener('touchstart', (e) => this._onTouchStart(e), { passive: true });
    this.container.addEventListener('touchmove', (e) => this._onTouchMove(e), { passive: false });
    this.container.addEventListener('touchend', (e) => this._onTouchEnd(e), { passive: true });
  }

  _onTouchStart(e) {
    if (e.touches.length !== 1) return;
    this._touchStartX = e.touches[0].clientX;
    this._touchStartY = e.touches[0].clientY;
    this._touchStartTime = Date.now();
    this._isSwiping = false;
  }

  _onTouchMove(e) {
    if (e.touches.length !== 1) return;
    const dx = e.touches[0].clientX - this._touchStartX;
    const dy = e.touches[0].clientY - this._touchStartY;

    // If horizontal movement is dominant, mark as swiping
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 10) {
      this._isSwiping = true;
      e.preventDefault();
    }
  }

  _onTouchEnd(e) {
    if (!this._isSwiping) return;

    const touch = e.changedTouches[0];
    const dx = touch.clientX - this._touchStartX;
    const elapsed = Date.now() - this._touchStartTime;

    // Must be fast enough and far enough
    if (Math.abs(dx) < this.swipeThreshold || elapsed > 500) return;

    const currentIndex = this.tabOrder.indexOf(this.currentRoute);
    if (currentIndex === -1) return;

    if (dx > 0 && currentIndex > 0) {
      // Swipe right -> previous tab
      this.navigate(this.tabOrder[currentIndex - 1]);
    } else if (dx < 0 && currentIndex < this.tabOrder.length - 1) {
      // Swipe left -> next tab
      this.navigate(this.tabOrder[currentIndex + 1]);
    }
  }
}
