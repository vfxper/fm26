/**
 * API Client Module
 * Handles communication with FastAPI backend
 */

import { getTelegramInitData } from './telegram-init.js';

export class APIClient {
  constructor(baseURL = '/api') {
    this.baseURL = baseURL;
    this.wsConnection = null;
  }

  /**
   * Get authentication headers
   * @returns {Object} Headers object
   */
  getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };

    // Add Telegram init data for authentication
    const initData = getTelegramInitData();
    if (initData) {
      headers['X-Telegram-Init-Data'] = initData;
    }

    return headers;
  }

  /**
   * Make GET request
   * @param {string} endpoint - API endpoint
   * @param {Object} params - Query parameters
   * @returns {Promise<any>} Response data
   */
  async get(endpoint, params = {}) {
    const url = new URL(`${this.baseURL}${endpoint}`, window.location.origin);
    
    // Add query parameters
    Object.keys(params).forEach(key => {
      if (params[key] !== undefined && params[key] !== null) {
        url.searchParams.append(key, params[key]);
      }
    });

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.getHeaders(),
    });

    return this.handleResponse(response);
  }

  /**
   * Make POST request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request body
   * @returns {Promise<any>} Response data
   */
  async post(endpoint, data = {}) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });

    return this.handleResponse(response);
  }

  /**
   * Make PUT request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request body
   * @returns {Promise<any>} Response data
   */
  async put(endpoint, data = {}) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });

    return this.handleResponse(response);
  }

  /**
   * Make PATCH request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request body
   * @returns {Promise<any>} Response data
   */
  async patch(endpoint, data = {}) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });

    return this.handleResponse(response);
  }

  /**
   * Make DELETE request
   * @param {string} endpoint - API endpoint
   * @returns {Promise<any>} Response data
   */
  async delete(endpoint) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    return this.handleResponse(response);
  }

  /**
   * Handle API response
   * @param {Response} response - Fetch response
   * @returns {Promise<any>} Response data
   * @throws {Error} API error
   */
  async handleResponse(response) {
    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: `HTTP ${response.status}: ${response.statusText}`,
      }));
      
      throw new APIError(
        error.detail || 'An error occurred',
        response.status,
        error
      );
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      return null;
    }

    return response.json();
  }

  /**
   * Connect to WebSocket for real-time match events
   * @param {string} matchId - Match ID
   * @param {Function} onMessage - Message handler
   * @param {Function} onError - Error handler
   * @param {Function} onClose - Close handler
   * @returns {WebSocket} WebSocket connection
   */
  connectMatchWebSocket(matchId, onMessage, onError, onClose) {
    // Close existing connection
    if (this.wsConnection) {
      this.wsConnection.close();
    }

    // Determine WebSocket protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsURL = `${protocol}//${window.location.host}/ws/match/${matchId}`;

    // Create WebSocket connection
    this.wsConnection = new WebSocket(wsURL);

    // Set up event handlers
    this.wsConnection.onopen = () => {
      console.log('WebSocket connected:', matchId);
    };

    this.wsConnection.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.wsConnection.onerror = (event) => {
      console.error('WebSocket error:', event);
      if (onError) onError(event);
    };

    this.wsConnection.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      if (onClose) onClose(event);
      this.wsConnection = null;
    };

    return this.wsConnection;
  }

  /**
   * Close WebSocket connection
   */
  closeWebSocket() {
    if (this.wsConnection) {
      this.wsConnection.close();
      this.wsConnection = null;
    }
  }

  /**
   * Send message through WebSocket
   * @param {Object} message - Message to send
   */
  sendWebSocketMessage(message) {
    if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
      this.wsConnection.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected');
    }
  }

  // ===== API Endpoints =====

  /**
   * Get or create user
   * @param {number} telegramUserId - Telegram user ID
   * @returns {Promise<Object>} User data
   */
  async getUser(telegramUserId) {
    return this.get(`/users/${telegramUserId}`);
  }

  /**
   * Get career data
   * @param {number} careerId - Career ID
   * @returns {Promise<Object>} Career data
   */
  async getCareer(careerId) {
    return this.get(`/careers/${careerId}`);
  }

  /**
   * Create new career
   * @param {Object} data - Career creation data
   * @returns {Promise<Object>} Created career
   */
  async createCareer(data) {
    return this.post('/careers', data);
  }

  /**
   * Get squad players
   * @param {number} careerId - Career ID
   * @returns {Promise<Array>} Squad players
   */
  async getSquad(careerId) {
    return this.get(`/careers/${careerId}/squad`);
  }

  /**
   * Search players
   * @param {Object} filters - Search filters
   * @returns {Promise<Array>} Player search results
   */
  async searchPlayers(filters) {
    return this.get('/players/search', filters);
  }

  /**
   * Get player details
   * @param {number} playerId - Player ID
   * @returns {Promise<Object>} Player data
   */
  async getPlayer(playerId) {
    return this.get(`/players/${playerId}`);
  }

  /**
   * Get match data
   * @param {number} matchId - Match ID
   * @returns {Promise<Object>} Match data
   */
  async getMatch(matchId) {
    return this.get(`/matches/${matchId}`);
  }

  /**
   * Simulate match
   * @param {number} matchId - Match ID
   * @returns {Promise<Object>} Match result
   */
  async simulateMatch(matchId) {
    return this.post(`/matches/${matchId}/simulate`);
  }

  /**
   * Get tactics
   * @param {number} careerId - Career ID
   * @returns {Promise<Array>} Tactic presets
   */
  async getTactics(careerId) {
    return this.get(`/careers/${careerId}/tactics`);
  }

  /**
   * Save tactic
   * @param {number} careerId - Career ID
   * @param {Object} tactic - Tactic data
   * @returns {Promise<Object>} Saved tactic
   */
  async saveTactic(careerId, tactic) {
    return this.post(`/careers/${careerId}/tactics`, tactic);
  }

  /**
   * Make transfer bid
   * @param {number} careerId - Career ID
   * @param {Object} bidData - Transfer bid data
   * @returns {Promise<Object>} Bid result
   */
  async makeTransferBid(careerId, bidData) {
    return this.post(`/careers/${careerId}/transfers/bid`, bidData);
  }

  /**
   * Get transfer market
   * @param {number} careerId - Career ID
   * @param {Object} filters - Market filters
   * @returns {Promise<Array>} Available players
   */
  async getTransferMarket(careerId, filters) {
    return this.get(`/careers/${careerId}/transfers/market`, filters);
  }
}

/**
 * Custom API Error class
 */
export class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}
