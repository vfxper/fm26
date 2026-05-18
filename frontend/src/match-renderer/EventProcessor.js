/**
 * EventProcessor - Processes match events into animations
 * 
 * Takes the time-stamped event stream from the match engine and converts
 * each event into visual animations (pass, shot, goal, tackle).
 * 
 * Task 19.7: Implement event processing system
 * Task 19.8: Create pass animation with easing
 * Task 19.9: Implement shot animation
 * Task 19.10: Create goal celebration animation (max 3 seconds)
 * Task 19.11: Implement tackle animation
 */

import { Easing } from './AnimationEngine.js';

export class EventProcessor {
  /**
   * @param {import('./AnimationEngine.js').AnimationEngine} animationEngine
   * @param {import('./PlayerRenderer.js').PlayerRenderer} playerRenderer
   * @param {import('./BallRenderer.js').BallRenderer} ballRenderer
   * @param {import('./AccessibilityManager.js').AccessibilityManager} accessibilityManager
   */
  constructor(animationEngine, playerRenderer, ballRenderer, accessibilityManager) {
    /** @type {import('./AnimationEngine.js').AnimationEngine} */
    this.animationEngine = animationEngine;

    /** @type {import('./PlayerRenderer.js').PlayerRenderer} */
    this.playerRenderer = playerRenderer;

    /** @type {import('./BallRenderer.js').BallRenderer} */
    this.ballRenderer = ballRenderer;

    /** @type {import('./AccessibilityManager.js').AccessibilityManager} */
    this.accessibilityManager = accessibilityManager;

    /** @type {Array} Event queue to process */
    this._eventQueue = [];

    /** @type {number} Current event index */
    this._currentIndex = 0;

    /** @type {number} Playback speed multiplier */
    this.playbackSpeed = 1;

    /** @type {number} Time accumulator for event timing */
    this._timeAccumulator = 0;

    /** @type {number} Current match minute */
    this.currentMinute = 0;

    /** @type {number} Current match second */
    this.currentSecond = 0;

    /** @type {boolean} Whether currently processing an event animation */
    this._isAnimating = false;

    /** @type {Function|null} Callback when a goal is scored */
    this.onGoal = null;

    /** @type {Function|null} Callback when match time updates */
    this.onTimeUpdate = null;

    /** @type {Function|null} Callback when all events are processed */
    this.onComplete = null;

    /** @type {Object|null} Active celebration state */
    this._celebration = null;
  }

  /**
   * Load events from match data
   * @param {Array} events - Array of match events
   */
  loadEvents(events) {
    this._eventQueue = [...events];
    this._currentIndex = 0;
    this._timeAccumulator = 0;
    this.currentMinute = 0;
    this.currentSecond = 0;
    this._isAnimating = false;
    this._celebration = null;
  }

  /**
   * Set playback speed
   * @param {number} speed - 1, 2, 4, or 0 for instant
   */
  setSpeed(speed) {
    this.playbackSpeed = speed;
  }

  /**
   * Update event processing (called each frame)
   * @param {number} deltaTime - Time since last frame in ms
   */
  update(deltaTime) {
    if (this._currentIndex >= this._eventQueue.length) {
      if (this.onComplete && !this._isAnimating) {
        this.onComplete();
      }
      return;
    }

    // If in instant mode, process all events immediately
    if (this.playbackSpeed === 0) {
      this._processAllInstantly();
      return;
    }

    // Don't advance time while animating
    if (this._isAnimating) return;

    // Accumulate time based on playback speed
    // Each match second = 100ms real time at 1x speed
    this._timeAccumulator += deltaTime * this.playbackSpeed;

    // Check if next event should fire
    const nextEvent = this._eventQueue[this._currentIndex];
    if (!nextEvent) return;

    const eventTimeMs = (nextEvent.minute * 60 + (nextEvent.second || 0)) * 100;
    const currentTimeMs = (this.currentMinute * 60 + this.currentSecond) * 100;
    const timeDiff = eventTimeMs - currentTimeMs;

    if (this._timeAccumulator >= timeDiff || timeDiff <= 0) {
      this._timeAccumulator = 0;
      this._processEvent(nextEvent);
      this._currentIndex++;
    } else {
      // Update match clock
      const progressSeconds = this._timeAccumulator / 100;
      const totalSeconds = this.currentMinute * 60 + this.currentSecond + progressSeconds;
      this.currentMinute = Math.floor(totalSeconds / 60);
      this.currentSecond = Math.floor(totalSeconds % 60);

      if (this.onTimeUpdate) {
        this.onTimeUpdate(this.currentMinute, this.currentSecond);
      }
    }
  }

  /**
   * Process all remaining events instantly
   * @private
   */
  _processAllInstantly() {
    while (this._currentIndex < this._eventQueue.length) {
      const event = this._eventQueue[this._currentIndex];
      this._processEventInstant(event);
      this._currentIndex++;
    }

    if (this.onComplete) {
      this.onComplete();
    }
  }

  /**
   * Process a single event instantly (no animation)
   * @param {Object} event
   * @private
   */
  _processEventInstant(event) {
    this.currentMinute = event.minute || 0;
    this.currentSecond = event.second || 0;

    if (event.position) {
      this.ballRenderer.setPosition(event.position.x, event.position.y);
    }

    if (event.event_type === 'GOAL' && this.onGoal) {
      this.onGoal(event);
    }

    if (this.onTimeUpdate) {
      this.onTimeUpdate(this.currentMinute, this.currentSecond);
    }
  }

  /**
   * Process a single event with animation
   * @param {Object} event
   * @private
   */
  _processEvent(event) {
    this.currentMinute = event.minute || 0;
    this.currentSecond = event.second || 0;

    if (this.onTimeUpdate) {
      this.onTimeUpdate(this.currentMinute, this.currentSecond);
    }

    switch (event.event_type) {
      case 'PASS':
        this._animatePass(event);
        break;
      case 'SHOT':
        this._animateShot(event);
        break;
      case 'GOAL':
        this._animateGoal(event);
        break;
      case 'TACKLE':
        this._animateTackle(event);
        break;
      case 'KICKOFF':
      case 'HALF_TIME':
      case 'FULL_TIME':
        this._handleMatchEvent(event);
        break;
      default:
        // Unknown event type, just update ball position
        if (event.position) {
          this.ballRenderer.setPosition(event.position.x, event.position.y);
        }
        break;
    }
  }

  /**
   * Animate a pass event
   * Task 19.8: Create pass animation with easing
   * @param {Object} event
   * @private
   */
  _animatePass(event) {
    if (this.accessibilityManager.shouldSkipAnimations()) {
      if (event.position) {
        this.ballRenderer.setPosition(event.position.x, event.position.y);
      }
      return;
    }

    const startPos = { x: this.ballRenderer.x, y: this.ballRenderer.y };
    const endPos = event.position || startPos;

    // Calculate duration based on distance (longer passes take more time)
    const dx = endPos.x - startPos.x;
    const dy = endPos.y - startPos.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    const baseDuration = Math.min(800, Math.max(300, distance * 15));
    const duration = baseDuration / this.playbackSpeed;

    this._isAnimating = true;
    this.ballRenderer.inMotion = true;

    // Highlight involved players
    if (event.player_id) this.playerRenderer.highlightPlayer(event.player_id);
    if (event.target_player_id) this.playerRenderer.highlightPlayer(event.target_player_id);

    this.animationEngine.animate({
      duration,
      easing: Easing.easeInOutQuad,
      onUpdate: (progress) => {
        const x = startPos.x + (endPos.x - startPos.x) * progress;
        const y = startPos.y + (endPos.y - startPos.y) * progress;
        this.ballRenderer.setPosition(x, y);
      },
      onComplete: () => {
        this.ballRenderer.stop();
        this.playerRenderer.clearHighlights();
        this._isAnimating = false;
      },
    });
  }

  /**
   * Animate a shot event
   * Task 19.9: Implement shot animation
   * @param {Object} event
   * @private
   */
  _animateShot(event) {
    if (this.accessibilityManager.shouldSkipAnimations()) {
      if (event.position) {
        this.ballRenderer.setPosition(event.position.x, event.position.y);
      }
      return;
    }

    const startPos = { x: this.ballRenderer.x, y: this.ballRenderer.y };
    const endPos = event.position || startPos;

    // Shots are faster than passes
    const duration = Math.max(200, 400 / this.playbackSpeed);

    this._isAnimating = true;
    this.ballRenderer.inMotion = true;

    // Highlight shooter
    if (event.player_id) this.playerRenderer.highlightPlayer(event.player_id);

    this.animationEngine.animate({
      duration,
      easing: Easing.easeOutCubic, // Fast start, slow end (like a real shot)
      onUpdate: (progress) => {
        const x = startPos.x + (endPos.x - startPos.x) * progress;
        const y = startPos.y + (endPos.y - startPos.y) * progress;
        this.ballRenderer.setPosition(x, y);
      },
      onComplete: () => {
        this.ballRenderer.stop();
        this.playerRenderer.clearHighlights();
        this._isAnimating = false;
      },
    });
  }

  /**
   * Animate a goal event with celebration
   * Task 19.10: Create goal celebration animation (max 3 seconds)
   * @param {Object} event
   * @private
   */
  _animateGoal(event) {
    // Notify goal callback
    if (this.onGoal) {
      this.onGoal(event);
    }

    if (this.accessibilityManager.shouldSkipAnimations()) {
      if (event.position) {
        this.ballRenderer.setPosition(event.position.x, event.position.y);
      }
      return;
    }

    // Goal celebration: max 3 seconds
    const celebrationDuration = Math.min(3000, 3000 / this.playbackSpeed);

    this._isAnimating = true;
    this._celebration = {
      active: true,
      team: event.team,
      playerId: event.player_id,
      startTime: performance.now(),
      duration: celebrationDuration,
      progress: 0,
    };

    // Highlight scorer
    if (event.player_id) this.playerRenderer.highlightPlayer(event.player_id);

    this.animationEngine.animate({
      duration: celebrationDuration,
      easing: Easing.easeOutCubic,
      onUpdate: (progress) => {
        if (this._celebration) {
          this._celebration.progress = progress;
        }
      },
      onComplete: () => {
        this._celebration = null;
        this.playerRenderer.clearHighlights();
        this._isAnimating = false;
      },
    });
  }

  /**
   * Animate a tackle event
   * Task 19.11: Implement tackle animation
   * @param {Object} event
   * @private
   */
  _animateTackle(event) {
    if (this.accessibilityManager.shouldSkipAnimations()) {
      if (event.position) {
        this.ballRenderer.setPosition(event.position.x, event.position.y);
      }
      return;
    }

    const duration = Math.max(200, 500 / this.playbackSpeed);

    this._isAnimating = true;

    // Highlight both players involved
    if (event.player_id) this.playerRenderer.highlightPlayer(event.player_id);
    if (event.target_player_id) this.playerRenderer.highlightPlayer(event.target_player_id);

    // Quick shake effect on ball position
    const baseX = event.position ? event.position.x : this.ballRenderer.x;
    const baseY = event.position ? event.position.y : this.ballRenderer.y;

    this.animationEngine.animate({
      duration,
      easing: Easing.easeOutQuad,
      onUpdate: (progress) => {
        // Shake effect that dampens over time
        const shake = (1 - progress) * 1.5;
        const offsetX = Math.sin(progress * Math.PI * 6) * shake;
        const offsetY = Math.cos(progress * Math.PI * 4) * shake;
        this.ballRenderer.setPosition(baseX + offsetX, baseY + offsetY);
      },
      onComplete: () => {
        this.ballRenderer.setPosition(baseX, baseY);
        this.ballRenderer.stop();
        this.playerRenderer.clearHighlights();
        this._isAnimating = false;
      },
    });
  }

  /**
   * Handle non-animated match events (kickoff, half-time, full-time)
   * @param {Object} event
   * @private
   */
  _handleMatchEvent(event) {
    if (event.event_type === 'KICKOFF') {
      this.ballRenderer.setPosition(52.5, 34);
    } else if (event.event_type === 'HALF_TIME') {
      this.ballRenderer.setPosition(52.5, 34);
    } else if (event.event_type === 'FULL_TIME') {
      this.ballRenderer.stop();
    }
  }

  /**
   * Get the current celebration state (for overlay rendering)
   * @returns {Object|null} Celebration state or null
   */
  getCelebration() {
    return this._celebration;
  }

  /**
   * Check if there are more events to process
   * @returns {boolean}
   */
  hasMoreEvents() {
    return this._currentIndex < this._eventQueue.length;
  }

  /**
   * Get progress through the event list (0-1)
   * @returns {number}
   */
  getProgress() {
    if (this._eventQueue.length === 0) return 0;
    return this._currentIndex / this._eventQueue.length;
  }

  /**
   * Reset the processor to the beginning
   */
  reset() {
    this._currentIndex = 0;
    this._timeAccumulator = 0;
    this.currentMinute = 0;
    this.currentSecond = 0;
    this._isAnimating = false;
    this._celebration = null;
    this.playerRenderer.clearHighlights();
    this.ballRenderer.setPosition(52.5, 34);
    this.ballRenderer.stop();
  }
}
