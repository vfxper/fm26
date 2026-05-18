/**
 * Engine - Main game loop with fixed physics timestep and variable render rate
 * Uses a seeded PRNG for deterministic simulation.
 */
import { PHYSICS_TIMESTEP, DEFAULT_SEED, MATCH_MINUTE_DURATION } from './Constants.js';
import { EventBus, EVENTS } from './EventBus.js';

/**
 * Seeded pseudo-random number generator (Mulberry32)
 */
export class SeededRandom {
  constructor(seed = DEFAULT_SEED) {
    this._seed = seed;
    this._state = seed;
  }

  /** Returns a float in [0, 1) */
  next() {
    this._state |= 0;
    this._state = (this._state + 0x6D2B79F5) | 0;
    let t = Math.imul(this._state ^ (this._state >>> 15), 1 | this._state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /** Returns a float in [min, max) */
  range(min, max) {
    return min + this.next() * (max - min);
  }

  /** Returns an integer in [min, max] inclusive */
  int(min, max) {
    return Math.floor(this.range(min, max + 1));
  }

  /** Returns true with given probability */
  chance(probability) {
    return this.next() < probability;
  }

  /** Pick a random element from array */
  pick(array) {
    return array[Math.floor(this.next() * array.length)];
  }

  /** Gaussian random (Box-Muller) */
  gaussian(mean = 0, stddev = 1) {
    const u1 = this.next();
    const u2 = this.next();
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    return mean + z * stddev;
  }

  /** Reset to initial seed */
  reset() {
    this._state = this._seed;
  }

  get seed() { return this._seed; }
}

export class Engine {
  /**
   * @param {Object} options
   * @param {number} [options.seed] - Random seed
   * @param {number} [options.speed] - Time multiplier (1x, 2x, 4x)
   */
  constructor(options = {}) {
    this.eventBus = new EventBus();
    this.rng = new SeededRandom(options.seed || DEFAULT_SEED);
    this.speed = options.speed || 1;

    // Timing
    this._accumulator = 0;
    this._lastTime = 0;
    this._running = false;
    this._paused = false;
    this._rafId = null;

    // Match time tracking
    this.matchTime = 0; // in seconds of match time
    this.matchMinute = 0;
    this.realTimeElapsed = 0;

    // Systems to update
    this._physicsSystems = []; // Updated at fixed timestep
    this._renderSystems = []; // Updated each frame

    // Stats
    this.fps = 0;
    this._frameCount = 0;
    this._fpsTimer = 0;

    // Bind the loop
    this._loop = this._loop.bind(this);
  }

  /**
   * Register a system for physics updates (fixed timestep)
   * @param {Object} system - Must have update(dt, matchTime, rng) method
   */
  addPhysicsSystem(system) {
    this._physicsSystems.push(system);
  }

  /**
   * Register a system for render updates (every frame)
   * @param {Object} system - Must have render(interpolation) method
   */
  addRenderSystem(system) {
    this._renderSystems.push(system);
  }

  /**
   * Remove a physics system
   */
  removePhysicsSystem(system) {
    const idx = this._physicsSystems.indexOf(system);
    if (idx !== -1) this._physicsSystems.splice(idx, 1);
  }

  /**
   * Remove a render system
   */
  removeRenderSystem(system) {
    const idx = this._renderSystems.indexOf(system);
    if (idx !== -1) this._renderSystems.splice(idx, 1);
  }

  /**
   * Start the game loop
   */
  start() {
    if (this._running) return;
    this._running = true;
    this._paused = false;
    this._lastTime = performance.now();
    this._accumulator = 0;
    this._rafId = requestAnimationFrame(this._loop);
  }

  /**
   * Stop the game loop
   */
  stop() {
    this._running = false;
    if (this._rafId) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  /**
   * Pause/unpause
   */
  pause() { this._paused = true; }
  resume() { this._paused = false; this._lastTime = performance.now(); }
  get isPaused() { return this._paused; }
  get isRunning() { return this._running; }

  /**
   * Set simulation speed
   * @param {number} multiplier
   */
  setSpeed(multiplier) {
    this.speed = multiplier;
  }

  /**
   * Main loop - fixed timestep physics, variable render
   */
  _loop(currentTime) {
    if (!this._running) return;
    this._rafId = requestAnimationFrame(this._loop);

    if (this._paused) {
      this._lastTime = currentTime;
      // Still render when paused
      for (const system of this._renderSystems) {
        system.render(0);
      }
      return;
    }

    let frameTime = (currentTime - this._lastTime) / 1000; // in seconds
    this._lastTime = currentTime;

    // Cap frame time to prevent spiral of death
    if (frameTime > 0.25) frameTime = 0.25;

    // Apply speed multiplier
    frameTime *= this.speed;

    this._accumulator += frameTime;

    // Fixed timestep physics updates
    while (this._accumulator >= PHYSICS_TIMESTEP) {
      // Update match time
      const matchTimeDelta = PHYSICS_TIMESTEP / MATCH_MINUTE_DURATION; // in match minutes
      this.matchTime += PHYSICS_TIMESTEP;
      this.matchMinute = this.matchTime / MATCH_MINUTE_DURATION;
      this.realTimeElapsed += PHYSICS_TIMESTEP;

      // Update all physics systems
      for (const system of this._physicsSystems) {
        system.update(PHYSICS_TIMESTEP, this.matchTime, this.rng);
      }

      this._accumulator -= PHYSICS_TIMESTEP;
    }

    // Interpolation factor for smooth rendering
    const interpolation = this._accumulator / PHYSICS_TIMESTEP;

    // Render
    for (const system of this._renderSystems) {
      system.render(interpolation);
    }

    // FPS counter
    this._frameCount++;
    this._fpsTimer += frameTime / this.speed; // real time
    if (this._fpsTimer >= 1.0) {
      this.fps = this._frameCount;
      this._frameCount = 0;
      this._fpsTimer -= 1.0;
    }
  }

  /**
   * Reset engine state
   */
  reset() {
    this.stop();
    this.matchTime = 0;
    this.matchMinute = 0;
    this.realTimeElapsed = 0;
    this._accumulator = 0;
    this.rng.reset();
  }

  /**
   * Destroy and clean up
   */
  destroy() {
    this.stop();
    this.eventBus.clear();
    this._physicsSystems = [];
    this._renderSystems = [];
  }
}
