/**
 * MatchRenderer - Main class that initializes canvas, manages rendering loop,
 * and coordinates all sub-modules for 2D match visualization.
 * 
 * This is the primary entry point for the match rendering system.
 * It creates and wires together all sub-components:
 * - PitchRenderer: draws the pitch with markings
 * - PlayerRenderer: renders player sprites
 * - BallRenderer: renders the ball
 * - AnimationEngine: manages the render loop and animations
 * - EventProcessor: converts match events into animations
 * - UIOverlay: displays score, time, formation
 * - PlaybackControls: speed and pause controls
 * - WeatherEffects: rain, snow, fog overlays
 * - AccessibilityManager: reduced-motion support
 * 
 * Task 19.1: Implement MatchRenderer class with canvas initialization
 */

import { PitchRenderer } from './PitchRenderer.js';
import { PlayerRenderer } from './PlayerRenderer.js';
import { BallRenderer } from './BallRenderer.js';
import { AnimationEngine } from './AnimationEngine.js';
import { EventProcessor } from './EventProcessor.js';
import { UIOverlay } from './UIOverlay.js';
import { PlaybackControls } from './PlaybackControls.js';
import { WeatherEffects } from './WeatherEffects.js';
import { AccessibilityManager } from './AccessibilityManager.js';

export class MatchRenderer {
  /**
   * Create a new MatchRenderer
   * @param {HTMLCanvasElement|string} canvasOrSelector - Canvas element or CSS selector
   * @param {Object} [options] - Configuration options
   * @param {string} [options.weather='none'] - Weather type: 'none', 'rain', 'snow', 'fog'
   * @param {number} [options.weatherIntensity=0.5] - Weather intensity (0-1)
   * @param {boolean} [options.showNames=false] - Whether to show player names
   * @param {number} [options.initialSpeed=1] - Initial playback speed
   */
  constructor(canvasOrSelector, options = {}) {
    // Resolve canvas element
    if (typeof canvasOrSelector === 'string') {
      this.canvas = document.querySelector(canvasOrSelector);
    } else {
      this.canvas = canvasOrSelector;
    }

    if (!this.canvas || !(this.canvas instanceof HTMLCanvasElement)) {
      throw new Error('MatchRenderer: valid canvas element or selector required');
    }

    /** @type {CanvasRenderingContext2D} */
    this.ctx = this.canvas.getContext('2d');

    // Initialize sub-modules
    /** @type {AccessibilityManager} */
    this.accessibility = new AccessibilityManager();

    /** @type {PitchRenderer} */
    this.pitch = new PitchRenderer(this.ctx);

    /** @type {PlayerRenderer} */
    this.players = new PlayerRenderer(this.ctx, this.pitch);

    /** @type {BallRenderer} */
    this.ball = new BallRenderer(this.ctx, this.pitch);

    /** @type {AnimationEngine} */
    this.animation = new AnimationEngine();

    /** @type {EventProcessor} */
    this.events = new EventProcessor(
      this.animation,
      this.players,
      this.ball,
      this.accessibility
    );

    /** @type {UIOverlay} */
    this.overlay = new UIOverlay(this.ctx);

    /** @type {PlaybackControls} */
    this.controls = new PlaybackControls(this.ctx);

    /** @type {WeatherEffects} */
    this.weather = new WeatherEffects(this.ctx, this.accessibility);

    // Match state
    /** @type {boolean} Whether a match is loaded */
    this._matchLoaded = false;

    /** @type {boolean} Whether the match is playing */
    this._isPlaying = false;

    /** @type {boolean} Whether the match is paused */
    this._isPaused = false;

    /** @type {number} Home team score */
    this._homeScore = 0;

    /** @type {number} Away team score */
    this._awayScore = 0;

    // Apply options
    this.players.showNames = options.showNames || false;

    if (options.weather && options.weather !== 'none') {
      this.weather.setWeather(options.weather, options.weatherIntensity || 0.5);
    }

    // Wire up callbacks
    this._setupCallbacks();

    // Set initial speed
    this.setSpeed(options.initialSpeed || 1);

    // Set up canvas sizing
    this._setupCanvas();

    // Set up event listeners
    this._setupEventListeners();
  }

  /**
   * Set up internal callbacks between modules
   * @private
   */
  _setupCallbacks() {
    // Event processor callbacks
    this.events.onGoal = (event) => {
      if (event.team === 'home') {
        this._homeScore++;
      } else {
        this._awayScore++;
      }
      this.overlay.setScore(this._homeScore, this._awayScore);

      const scorerName = this._getPlayerName(event.player_id);
      this.overlay.addEvent(`⚽ GOAL! ${scorerName} (${event.minute}')`);
    };

    this.events.onTimeUpdate = (minute, second) => {
      this.overlay.setTime(minute, second);
    };

    this.events.onComplete = () => {
      this._isPlaying = false;
      this.animation.stop();
    };

    // Playback controls callbacks
    this.controls.onSpeedChange = (speed) => {
      this.events.setSpeed(speed);
    };

    this.controls.onPauseChange = (paused) => {
      this._isPaused = paused;
      this.overlay.setPaused(paused);
    };

    // Animation engine render callback
    this.animation.setRenderCallback((deltaTime, timestamp) => {
      this._onFrame(deltaTime, timestamp);
    });
  }

  /**
   * Set up canvas sizing and DPI scaling
   * @private
   */
  _setupCanvas() {
    this._resize();
  }

  /**
   * Set up DOM event listeners
   * @private
   */
  _setupEventListeners() {
    // Resize observer for responsive scaling
    this._resizeObserver = new ResizeObserver(() => {
      this._resize();
    });
    this._resizeObserver.observe(this.canvas.parentElement || this.canvas);

    // Click/tap handler for playback controls
    this._handleClick = (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const x = (e.clientX - rect.left) * (this.canvas.width / rect.width);
      const y = (e.clientY - rect.top) * (this.canvas.height / rect.height);
      this.controls.handleClick(x, y);
    };
    this.canvas.addEventListener('click', this._handleClick);

    // Touch handler
    this._handleTouch = (e) => {
      e.preventDefault();
      const touch = e.touches[0];
      const rect = this.canvas.getBoundingClientRect();
      const x = (touch.clientX - rect.left) * (this.canvas.width / rect.width);
      const y = (touch.clientY - rect.top) * (this.canvas.height / rect.height);
      this.controls.handleClick(x, y);
    };
    this.canvas.addEventListener('touchstart', this._handleTouch, { passive: false });
  }

  /**
   * Handle canvas resize
   * @private
   */
  _resize() {
    const container = this.canvas.parentElement;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight || Math.round(width * 0.65);

    // Handle device pixel ratio for sharp rendering
    const dpr = Math.min(window.devicePixelRatio || 1, 2); // Cap at 2x for performance

    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.canvas.style.width = `${width}px`;
    this.canvas.style.height = `${height}px`;

    // Scale context for DPI
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Update all sub-modules with new dimensions
    this.pitch.calculateScale(width, height);
    this.overlay.setCanvasSize(width, height);
    this.controls.setCanvasSize(width, height);
    this.weather.setCanvasSize(width, height);

    // Redraw if not actively animating
    if (!this.animation.isRunning()) {
      this._draw();
    }
  }

  /**
   * Load match data and prepare for playback
   * @param {Object} matchData - Match data object
   * @param {Object} matchData.homeTeam - {name, color, formation, players: [{id, number, name, x, y}]}
   * @param {Object} matchData.awayTeam - {name, color, formation, players: [{id, number, name, x, y}]}
   * @param {Array} matchData.events - Array of match events
   * @param {string} [matchData.weather] - Weather type
   * @param {number} [matchData.weatherIntensity] - Weather intensity
   */
  loadMatch(matchData) {
    // Reset state
    this._homeScore = 0;
    this._awayScore = 0;
    this._isPlaying = false;
    this._isPaused = false;

    // Set team info
    const homeTeam = matchData.homeTeam || {};
    const awayTeam = matchData.awayTeam || {};

    this.overlay.setTeams(
      { name: homeTeam.name, color: homeTeam.color || '#2563eb', formation: homeTeam.formation },
      { name: awayTeam.name, color: awayTeam.color || '#dc2626', formation: awayTeam.formation }
    );
    this.overlay.setScore(0, 0);
    this.overlay.setTime(0, 0);
    this.overlay.setPaused(false);

    // Set player colors
    this.players.setTeamColors(homeTeam.color || '#2563eb', awayTeam.color || '#dc2626');

    // Initialize players
    this.players.initializePlayers(homeTeam.players || [], awayTeam.players || []);

    // Load events
    this.events.loadEvents(matchData.events || []);

    // Set weather
    if (matchData.weather) {
      this.weather.setWeather(matchData.weather, matchData.weatherIntensity || 0.5);
    }

    // Reset ball to center
    this.ball.setPosition(52.5, 34);

    this._matchLoaded = true;

    // Draw initial state
    this._draw();
  }

  /**
   * Start match playback
   */
  start() {
    if (!this._matchLoaded) return;
    this._isPlaying = true;
    this._isPaused = false;
    this.controls.setPaused(false);
    this.animation.start();
  }

  /**
   * Pause match playback
   */
  pause() {
    this._isPaused = true;
    this.controls.setPaused(true);
    this.overlay.setPaused(true);
  }

  /**
   * Resume match playback
   */
  resume() {
    this._isPaused = false;
    this.controls.setPaused(false);
    this.overlay.setPaused(false);

    if (!this.animation.isRunning()) {
      this.animation.start();
    }
  }

  /**
   * Toggle pause/resume
   */
  togglePause() {
    if (this._isPaused) {
      this.resume();
    } else {
      this.pause();
    }
  }

  /**
   * Stop match playback completely
   */
  stop() {
    this._isPlaying = false;
    this._isPaused = false;
    this.animation.stop();
    this.animation.cancelAll();
  }

  /**
   * Set playback speed
   * @param {number} speed - 1, 2, 4, or 0 for instant
   */
  setSpeed(speed) {
    this.controls.setSpeed(speed);
    this.events.setSpeed(speed);
  }

  /**
   * Set weather effect
   * @param {string} type - 'none', 'rain', 'snow', 'fog'
   * @param {number} [intensity=0.5] - Intensity (0-1)
   */
  setWeather(type, intensity = 0.5) {
    this.weather.setWeather(type, intensity);
  }

  /**
   * Called each animation frame
   * @param {number} deltaTime - Time since last frame in ms
   * @param {number} timestamp - Current timestamp
   * @private
   */
  _onFrame(deltaTime, timestamp) {
    // Update game state if not paused
    if (!this._isPaused && this._isPlaying) {
      this.events.update(deltaTime);
      this.weather.update(deltaTime);
      this.ball.updateTrail();
    }

    // Update celebration state in overlay
    this.overlay.setCelebration(this.events.getCelebration());

    // Draw everything
    this._draw();
  }

  /**
   * Draw the complete scene
   * @private
   */
  _draw() {
    const ctx = this.ctx;
    const canvas = this.canvas;

    // Clear canvas (use logical size)
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const width = canvas.width / dpr;
    const height = canvas.height / dpr;

    ctx.clearRect(0, 0, width, height);

    // Background
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, width, height);

    // Draw layers in order
    this.pitch.draw();
    this.weather.draw();
    this.players.draw();
    this.ball.draw();
    this.overlay.draw();
    this.controls.draw();
  }

  /**
   * Get a player's name by ID
   * @param {number} playerId
   * @returns {string}
   * @private
   */
  _getPlayerName(playerId) {
    const player = this.players.players.get(playerId);
    return player ? player.name : `#${playerId}`;
  }

  /**
   * Get current match state
   * @returns {Object} Current state
   */
  getState() {
    return {
      isPlaying: this._isPlaying,
      isPaused: this._isPaused,
      homeScore: this._homeScore,
      awayScore: this._awayScore,
      minute: this.events.currentMinute,
      second: this.events.currentSecond,
      speed: this.controls.speed,
      fps: this.animation.currentFPS,
      progress: this.events.getProgress(),
    };
  }

  /**
   * Clean up all resources and event listeners
   */
  destroy() {
    // Stop animation
    this.stop();

    // Remove event listeners
    if (this._handleClick) {
      this.canvas.removeEventListener('click', this._handleClick);
    }
    if (this._handleTouch) {
      this.canvas.removeEventListener('touchstart', this._handleTouch);
    }

    // Disconnect resize observer
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
    }

    // Destroy sub-modules
    this.animation.destroy();
    this.accessibility.destroy();
    this.weather.clear();
  }
}
