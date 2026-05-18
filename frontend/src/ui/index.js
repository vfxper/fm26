/**
 * UI Navigation System - Module Entry Point
 *
 * Provides a complete mobile-first UI framework for Telegram Football Manager.
 * Features:
 * - SPA router with scroll position restoration and swipe navigation
 * - Bottom navigation bar with 5 tabs and notification badges
 * - Full screen implementations (Home, Squad, Tactics, Transfers, Match, Player Profile)
 * - Reusable components (LoadingIndicator, SearchBar, Tooltip, AttributeBar, RadarChart)
 * - Touch-friendly (44x44px minimum targets)
 * - Portrait and landscape orientation support
 * - CSS custom properties for Telegram theme integration
 */

// Core navigation
export { Router } from './Router.js';
export { BottomNav } from './BottomNav.js';

// Screens
export { HomeScreen } from './screens/HomeScreen.js';
export { SquadScreen } from './screens/SquadScreen.js';
export { TacticsScreen } from './screens/TacticsScreen.js';
export { TransfersScreen } from './screens/TransfersScreen.js';
export { MatchScreen } from './screens/MatchScreen.js';
export { PlayerProfileScreen } from './screens/PlayerProfileScreen.js';

// Components
export { LoadingIndicator, withLoading } from './components/LoadingIndicator.js';
export { SearchBar } from './components/SearchBar.js';
export { Tooltip, initTooltips } from './components/Tooltip.js';
export { NotificationBadge } from './components/NotificationBadge.js';
export { AttributeBar } from './components/AttributeBar.js';
export { RadarChart } from './components/RadarChart.js';

// Styles (import for side effects)
import './styles/navigation.css';
import './styles/screens.css';
import './styles/components.css';

/**
 * Initialize the complete UI navigation system
 * @param {Object} options
 * @param {HTMLElement} options.container - Main content container
 * @param {Object} [options.apiClient] - API client instance
 * @param {Object} [options.matchRenderer] - Match renderer instance
 * @returns {Object} UI system instance with router, nav, and screens
 */
export function createUISystem(options = {}) {
  const { container, apiClient, matchRenderer } = options;

  if (!container) {
    throw new Error('[UI] Container element is required');
  }

  // Create router
  const router = new Router(container, {
    swipeEnabled: true,
    tabOrder: ['home', 'squad', 'tactics', 'transfers', 'match'],
  });

  // Create bottom nav
  const bottomNav = new BottomNav({
    onTabChange: (tabId) => {
      router.navigate(tabId);
    },
  });

  // Sync router navigation with bottom nav
  router.onNavigate = (routeName) => {
    const mainTabs = ['home', 'squad', 'tactics', 'transfers', 'match'];
    if (mainTabs.includes(routeName)) {
      bottomNav.setActive(routeName);
    }
  };

  // Create screens
  const homeScreen = new HomeScreen({ apiClient });
  const squadScreen = new SquadScreen({
    apiClient,
    onPlayerSelect: (playerId) => {
      router.navigate('player-profile', { playerId });
    },
  });
  const tacticsScreen = new TacticsScreen({ apiClient });
  const transfersScreen = new TransfersScreen({
    apiClient,
    onPlayerSelect: (playerId) => {
      router.navigate('player-profile', { playerId });
    },
  });
  const matchScreen = new MatchScreen({ apiClient, matchRenderer });
  const playerProfileScreen = new PlayerProfileScreen({
    apiClient,
    onBack: () => router.back(),
  });

  // Register routes
  router.register('home', (params) => homeScreen.render(params), () => homeScreen.destroy());
  router.register('squad', (params) => squadScreen.render(params), () => squadScreen.destroy());
  router.register('tactics', (params) => tacticsScreen.render(params), () => tacticsScreen.destroy());
  router.register('transfers', (params) => transfersScreen.render(params), () => transfersScreen.destroy());
  router.register('match', (params) => matchScreen.render(params), () => matchScreen.destroy());
  router.register('player-profile', (params) => playerProfileScreen.render(params), () => playerProfileScreen.destroy());

  // Create search bar
  const searchBar = new SearchBar({
    onSearch: async (query) => {
      if (apiClient) {
        try {
          const results = await apiClient.get(`/players/search?q=${encodeURIComponent(query)}&limit=10`);
          searchBar.setResults(
            (results || []).map((p) => ({
              id: p.id,
              text: p.name,
              subtitle: `${p.position} · ${p.club || 'Free'}`,
              icon: '⚽',
            }))
          );
        } catch (e) {
          searchBar.setResults([]);
        }
      }
    },
    onSelect: (result) => {
      router.navigate('player-profile', { playerId: result.id });
    },
  });

  return {
    router,
    bottomNav,
    searchBar,
    screens: {
      home: homeScreen,
      squad: squadScreen,
      tactics: tacticsScreen,
      transfers: transfersScreen,
      match: matchScreen,
      playerProfile: playerProfileScreen,
    },

    /**
     * Mount the UI system to the DOM
     * @param {HTMLElement} appRoot - Root app element
     */
    mount(appRoot) {
      // Clear existing content
      appRoot.innerHTML = '';

      // Create layout
      const layout = document.createElement('div');
      layout.className = 'app-layout';

      // Search bar area
      const searchArea = document.createElement('div');
      searchArea.className = 'app-layout__search';
      searchArea.style.padding = '8px 16px';
      searchArea.appendChild(searchBar.render());

      // Content area
      const contentArea = document.createElement('div');
      contentArea.className = 'app-layout__content';

      // Bottom nav
      const navEl = bottomNav.render();

      layout.appendChild(searchArea);
      layout.appendChild(contentArea);
      layout.appendChild(navEl);
      appRoot.appendChild(layout);

      // Update router container
      router.container = contentArea;

      // Navigate to home
      router.navigate('home', {}, false);
    },

    /**
     * Destroy the UI system
     */
    destroy() {
      bottomNav.destroy();
      searchBar.destroy();
    },
  };
}
