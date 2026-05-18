/**
 * Main application entry point
 * Initializes Telegram Web App and application modules
 */

import './style.css';
import { initTelegramWebApp } from './telegram-init.js';
import { MatchRenderer } from './match-renderer.js';
import { NavigationManager } from './navigation.js';
import { APIClient } from './api-client.js';

// Application state
const app = {
  telegram: null,
  apiClient: null,
  matchRenderer: null,
  navigationManager: null,
  currentUser: null,
  currentCareer: null,
};

/**
 * Initialize the application
 */
async function init() {
  try {
    console.log('Initializing Telegram Football Manager...');

    // Initialize Telegram Web App
    app.telegram = initTelegramWebApp();
    console.log('Telegram Web App initialized:', app.telegram);

    // Initialize API client
    app.apiClient = new APIClient('/api');

    // Initialize navigation
    app.navigationManager = new NavigationManager();

    // Initialize match renderer
    const canvas = document.getElementById('match-canvas');
    app.matchRenderer = new MatchRenderer(canvas);

    // Set up canvas resize handler
    window.addEventListener('resize', () => {
      app.matchRenderer.resize();
    });

    // Set up orientation change handler
    window.addEventListener('orientationchange', () => {
      setTimeout(() => {
        app.matchRenderer.resize();
      }, 100);
    });

    // Load user data
    await loadUserData();

    // Hide loading screen
    hideLoadingScreen();

    console.log('Application initialized successfully');
  } catch (error) {
    console.error('Failed to initialize application:', error);
    showError('Failed to load application. Please try again.');
  }
}

/**
 * Load user data from backend
 */
async function loadUserData() {
  try {
    // Get Telegram user data
    const telegramUser = app.telegram?.initDataUnsafe?.user;
    
    if (!telegramUser) {
      console.warn('No Telegram user data available');
      return;
    }

    console.log('Loading user data for:', telegramUser.id);

    // Fetch or create user in backend
    app.currentUser = await app.apiClient.get(`/users/${telegramUser.id}`);
    
    // Load active career if exists
    if (app.currentUser.active_career_id) {
      app.currentCareer = await app.apiClient.get(`/careers/${app.currentUser.active_career_id}`);
      console.log('Loaded career:', app.currentCareer);
    }
  } catch (error) {
    console.error('Failed to load user data:', error);
    // Continue with limited functionality
  }
}

/**
 * Hide loading screen with animation
 */
function hideLoadingScreen() {
  const loadingScreen = document.getElementById('loading-screen');
  loadingScreen.classList.add('hidden');
  
  // Remove from DOM after animation
  setTimeout(() => {
    loadingScreen.remove();
  }, 300);
}

/**
 * Show error message to user
 */
function showError(message) {
  const loadingScreen = document.getElementById('loading-screen');
  const loadingText = loadingScreen.querySelector('.loading-text');
  const spinner = loadingScreen.querySelector('.loading-spinner');
  
  spinner.style.display = 'none';
  loadingText.textContent = message;
  loadingText.style.color = '#ff4444';
}

// Start application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export app instance for debugging
window.TFM = app;
