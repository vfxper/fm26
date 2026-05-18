/**
 * AnimationEngine - requestAnimationFrame loop, easing functions, animation queue
 * 
 * Manages the render loop at 60 FPS target with fallback to 30 FPS on slow devices.
 * Provides easing functions and an animation queue for smooth transitions.
 * 
 * Task 19.6: Create animation loop with requestAnimationFrame (30+ FPS)
 * Task 19.17: Optimize rendering for 60 FPS on mobile devices
 */

/**
 * Easing functions for smooth animations
 */
export const Easing = {
  linear(t) {
    return t;
  },

  easeInQuad(t) {
    return t * t;
  },

  easeOutQuad(t) {
    return t * (2 - t);
  },

  easeInOutQuad(t) {
    return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
  },

  easeInCubic(t) {
    return t * t * t;
  },

  easeOutCubic(t) {
    return (--t) * t * t + 1;
  },

  easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1;
  },

  easeOutElastic(t) {
    if (t === 0 || t === 1) return t;
    return Math.pow(2, -10 * t) * Math.sin((t - 0.1) * 5 * Math.PI) + 1;
  },

  easeOutBounce(t) {
    if (t < 1 / 2.75) {
      return 7.5625 * t * t;
    } else if (t < 2 / 2.75) {
      return 7.5625 * (t -= 1.5 / 2.75) * t + 0.75;
    } else if (t < 2.5 / 2.75) {
      return 7.5625 * (t -= 2.25 / 2.75) * t + 0.9375;
    } else {
      return 7.5625 * (t -= 2.625 / 2.75) * t + 0.984375;
    }
  },
};

/**
 * Single animation instance
 */
class Animation {
  /**
   * @param {Object} config
   * @param {number} config.duration - Duration in ms
   * @param {Function} config.easing - Easing function
   * @param {Function} config.onUpdate - Called each frame with progress (0-1)
   * @param {Function} [config.onComplete] - Called when animation finishes
   * @param {string} [config.id] - Optional identifier for the animation
   */
  constructor({ duration, easing, onUpdate, onComplete, id }) {
    this.duration = duration;
    this.easing = easing || Easing.linear;
    this.onUpdate = onUpdate;
    this.onComplete = onComplete || null;
    this.id = id || null;
    this.startTime = -1;
    this.isComplete = false;
  }

  /**
   * Start the animation
   * @param {number} currentTime - Current timestamp
   */
  start(currentTime) {
    this.startTime = currentTime;
    this.isComplete = false;
  }

  /**
   * Update the animation
   * @param {number} currentTime - Current timestamp
   * @returns {boolean} True if animation is still running
   */
  update(currentTime) {
    if (this.isComplete) return false;
    if (this.startTime < 0) {
      this.start(currentTime);
    }

    const elapsed = currentTime - this.startTime;
    let progress = Math.min(elapsed / this.duration, 1);
    const easedProgress = this.easing(progress);

    this.onUpdate(easedProgress);

    if (progress >= 1) {
      this.isComplete = true;
      if (this.onComplete) {
        this.onComplete();
      }
      return false;
    }

    return true;
  }
}

export class AnimationEngine {
  constructor() {
    /** @type {number|null} requestAnimationFrame ID */
    this._rafId = null;

    /** @type {boolean} Whether the loop is running */
    this._running = false;

    /** @type {Function|null} External render callback */
    this._renderCallback = null;

    /** @type {Animation[]} Active animations */
    this._animations = [];

    /** @type {Animation[]} Queued animations (play sequentially) */
    this._queue = [];

    /** @type {boolean} Whether queue is being processed */
    this._processingQueue = false;

    /** @type {number} Last frame timestamp */
    this._lastFrameTime = 0;

    /** @type {number} Frame count for FPS calculation */
    this._frameCount = 0;

    /** @type {number} FPS measurement start time */
    this._fpsStartTime = 0;

    /** @type {number} Current measured FPS */
    this.currentFPS = 0;

    /** @type {number} Target FPS (60 default, drops to 30 on slow devices) */
    this.targetFPS = 60;

    /** @type {number} Minimum frame interval in ms (for throttling) */
    this._minFrameInterval = 1000 / 60; // ~16.67ms

    /** @type {number} Consecutive slow frame count for adaptive FPS */
    this._slowFrameCount = 0;

    /** @type {number} Threshold for switching to 30 FPS mode */
    this._slowFrameThreshold = 10;
  }

  /**
   * Set the render callback that gets called each frame
   * @param {Function} callback - Function called with (deltaTime, timestamp)
   */
  setRenderCallback(callback) {
    this._renderCallback = callback;
  }

  /**
   * Start the animation loop
   */
  start() {
    if (this._running) return;
    this._running = true;
    this._lastFrameTime = performance.now();
    this._fpsStartTime = this._lastFrameTime;
    this._frameCount = 0;
    this._loop();
  }

  /**
   * Stop the animation loop
   */
  stop() {
    this._running = false;
    if (this._rafId !== null) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  /**
   * Check if the engine is running
   * @returns {boolean}
   */
  isRunning() {
    return this._running;
  }

  /**
   * Main animation loop
   * @private
   */
  _loop() {
    if (!this._running) return;

    this._rafId = requestAnimationFrame((timestamp) => {
      const deltaTime = timestamp - this._lastFrameTime;

      // Adaptive FPS: skip frame if too fast (throttle to target)
      if (deltaTime < this._minFrameInterval * 0.8) {
        this._loop();
        return;
      }

      // Track FPS
      this._frameCount++;
      const fpsDelta = timestamp - this._fpsStartTime;
      if (fpsDelta >= 1000) {
        this.currentFPS = Math.round((this._frameCount * 1000) / fpsDelta);
        this._frameCount = 0;
        this._fpsStartTime = timestamp;

        // Adaptive FPS: detect slow device
        this._adaptFPS(deltaTime);
      }

      this._lastFrameTime = timestamp;

      // Update all active animations
      this._updateAnimations(timestamp);

      // Process queue
      this._processQueue(timestamp);

      // Call external render callback
      if (this._renderCallback) {
        this._renderCallback(deltaTime, timestamp);
      }

      // Continue loop
      this._loop();
    });
  }

  /**
   * Adapt target FPS based on device performance
   * @param {number} deltaTime - Last frame delta
   * @private
   */
  _adaptFPS(deltaTime) {
    if (this.currentFPS < 25 && this.targetFPS === 60) {
      this._slowFrameCount++;
      if (this._slowFrameCount >= this._slowFrameThreshold) {
        // Switch to 30 FPS target
        this.targetFPS = 30;
        this._minFrameInterval = 1000 / 30;
        this._slowFrameCount = 0;
      }
    } else if (this.currentFPS >= 55 && this.targetFPS === 30) {
      // Device recovered, try 60 FPS again
      this._slowFrameCount++;
      if (this._slowFrameCount >= this._slowFrameThreshold) {
        this.targetFPS = 60;
        this._minFrameInterval = 1000 / 60;
        this._slowFrameCount = 0;
      }
    } else {
      this._slowFrameCount = 0;
    }
  }

  /**
   * Update all active animations
   * @param {number} timestamp
   * @private
   */
  _updateAnimations(timestamp) {
    for (let i = this._animations.length - 1; i >= 0; i--) {
      const anim = this._animations[i];
      const stillRunning = anim.update(timestamp);
      if (!stillRunning) {
        this._animations.splice(i, 1);
      }
    }
  }

  /**
   * Process the sequential animation queue
   * @param {number} timestamp
   * @private
   */
  _processQueue(timestamp) {
    if (this._queue.length === 0) {
      this._processingQueue = false;
      return;
    }

    if (!this._processingQueue) {
      this._processingQueue = true;
      const nextAnim = this._queue[0];
      nextAnim.start(timestamp);
      this._animations.push(nextAnim);

      // Set up completion to advance queue
      const originalComplete = nextAnim.onComplete;
      nextAnim.onComplete = () => {
        if (originalComplete) originalComplete();
        this._queue.shift();
        this._processingQueue = false;
      };
    }
  }

  /**
   * Add an animation to play immediately (parallel with others)
   * @param {Object} config - Animation config
   * @returns {Animation} The created animation
   */
  animate(config) {
    const anim = new Animation(config);
    anim.start(performance.now());
    this._animations.push(anim);
    return anim;
  }

  /**
   * Add an animation to the sequential queue
   * @param {Object} config - Animation config
   * @returns {Animation} The created animation
   */
  enqueue(config) {
    const anim = new Animation(config);
    this._queue.push(anim);
    return anim;
  }

  /**
   * Cancel all animations with a specific ID
   * @param {string} id - Animation ID to cancel
   */
  cancelById(id) {
    this._animations = this._animations.filter((a) => a.id !== id);
    this._queue = this._queue.filter((a) => a.id !== id);
  }

  /**
   * Cancel all running and queued animations
   */
  cancelAll() {
    this._animations = [];
    this._queue = [];
    this._processingQueue = false;
  }

  /**
   * Check if any animations are currently active
   * @returns {boolean}
   */
  hasActiveAnimations() {
    return this._animations.length > 0 || this._queue.length > 0;
  }

  /**
   * Get the number of active animations
   * @returns {number}
   */
  getActiveCount() {
    return this._animations.length;
  }

  /**
   * Instantly complete all animations (for instant playback mode)
   */
  completeAll() {
    // Complete all active animations at progress = 1
    for (const anim of this._animations) {
      anim.onUpdate(1);
      if (anim.onComplete) anim.onComplete();
    }
    this._animations = [];

    // Complete all queued animations
    for (const anim of this._queue) {
      anim.onUpdate(1);
      if (anim.onComplete) anim.onComplete();
    }
    this._queue = [];
    this._processingQueue = false;
  }

  /**
   * Clean up resources
   */
  destroy() {
    this.stop();
    this.cancelAll();
    this._renderCallback = null;
  }
}
