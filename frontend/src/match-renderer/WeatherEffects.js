/**
 * WeatherEffects - Rain, snow, fog particle effects
 * 
 * Renders lightweight weather overlay effects on the canvas.
 * Respects reduced-motion accessibility settings.
 * 
 * Task 19.15: Implement weather effects (rain, snow, fog)
 */

/**
 * @typedef {'none'|'rain'|'snow'|'fog'} WeatherType
 */

/**
 * Single particle for weather effects
 */
class Particle {
  constructor() {
    this.x = 0;
    this.y = 0;
    this.vx = 0;
    this.vy = 0;
    this.size = 1;
    this.alpha = 1;
    this.life = 1;
  }
}

export class WeatherEffects {
  /**
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D context
   * @param {import('./AccessibilityManager.js').AccessibilityManager} accessibilityManager
   */
  constructor(ctx, accessibilityManager) {
    /** @type {CanvasRenderingContext2D} */
    this.ctx = ctx;

    /** @type {import('./AccessibilityManager.js').AccessibilityManager} */
    this.accessibilityManager = accessibilityManager;

    /** @type {WeatherType} Current weather type */
    this.weatherType = 'none';

    /** @type {number} Weather intensity (0-1) */
    this.intensity = 0.5;

    /** @type {number} Canvas width */
    this.canvasWidth = 0;

    /** @type {number} Canvas height */
    this.canvasHeight = 0;

    /** @type {Particle[]} Active particles */
    this._particles = [];

    /** @type {number} Maximum particle count */
    this._maxParticles = 150;

    /** @type {number} Fog opacity (for fog effect) */
    this._fogOpacity = 0;

    /** @type {number} Fog target opacity */
    this._fogTargetOpacity = 0;
  }

  /**
   * Update canvas dimensions
   * @param {number} width
   * @param {number} height
   */
  setCanvasSize(width, height) {
    this.canvasWidth = width;
    this.canvasHeight = height;
  }

  /**
   * Set the weather type and intensity
   * @param {WeatherType} type - Weather type
   * @param {number} [intensity=0.5] - Intensity from 0 to 1
   */
  setWeather(type, intensity = 0.5) {
    this.weatherType = type;
    this.intensity = Math.max(0, Math.min(1, intensity));

    // Reset particles when changing weather
    this._particles = [];

    if (type === 'fog') {
      this._fogTargetOpacity = 0.15 + this.intensity * 0.2;
    } else {
      this._fogTargetOpacity = 0;
    }

    // Adjust particle count based on intensity
    this._maxParticles = Math.floor(50 + this.intensity * 150);
  }

  /**
   * Update weather particles (called each frame)
   * @param {number} deltaTime - Time since last frame in ms
   */
  update(deltaTime) {
    // Skip if reduced motion or no weather
    if (this.accessibilityManager.shouldSkipAnimations() || this.weatherType === 'none') {
      return;
    }

    const dt = deltaTime / 16.67; // Normalize to 60fps

    switch (this.weatherType) {
      case 'rain':
        this._updateRain(dt);
        break;
      case 'snow':
        this._updateSnow(dt);
        break;
      case 'fog':
        this._updateFog(dt);
        break;
    }
  }

  /**
   * Draw weather effects
   */
  draw() {
    if (this.weatherType === 'none') return;

    // For reduced motion, show a static overlay instead of particles
    if (this.accessibilityManager.shouldSkipAnimations()) {
      this._drawStaticOverlay();
      return;
    }

    switch (this.weatherType) {
      case 'rain':
        this._drawRain();
        break;
      case 'snow':
        this._drawSnow();
        break;
      case 'fog':
        this._drawFog();
        break;
    }
  }

  /**
   * Update rain particles
   * @param {number} dt - Normalized delta time
   * @private
   */
  _updateRain(dt) {
    // Spawn new particles
    while (this._particles.length < this._maxParticles) {
      const p = new Particle();
      p.x = Math.random() * this.canvasWidth;
      p.y = -10;
      p.vx = -1 - Math.random() * 2; // Slight wind
      p.vy = 8 + Math.random() * 6; // Falling speed
      p.size = 1 + Math.random() * 1.5;
      p.alpha = 0.3 + Math.random() * 0.4;
      this._particles.push(p);
    }

    // Update existing particles
    for (let i = this._particles.length - 1; i >= 0; i--) {
      const p = this._particles[i];
      p.x += p.vx * dt;
      p.y += p.vy * dt;

      // Remove if off screen
      if (p.y > this.canvasHeight || p.x < -10) {
        this._particles.splice(i, 1);
      }
    }
  }

  /**
   * Update snow particles
   * @param {number} dt - Normalized delta time
   * @private
   */
  _updateSnow(dt) {
    // Spawn new particles
    while (this._particles.length < this._maxParticles) {
      const p = new Particle();
      p.x = Math.random() * this.canvasWidth;
      p.y = -5;
      p.vx = (Math.random() - 0.5) * 1.5; // Gentle drift
      p.vy = 1 + Math.random() * 2; // Slow falling
      p.size = 2 + Math.random() * 3;
      p.alpha = 0.5 + Math.random() * 0.4;
      p.life = Math.random() * Math.PI * 2; // For wobble
      this._particles.push(p);
    }

    // Update existing particles
    for (let i = this._particles.length - 1; i >= 0; i--) {
      const p = this._particles[i];
      p.life += 0.02 * dt;
      p.x += (p.vx + Math.sin(p.life) * 0.5) * dt; // Wobble
      p.y += p.vy * dt;

      // Remove if off screen
      if (p.y > this.canvasHeight || p.x < -10 || p.x > this.canvasWidth + 10) {
        this._particles.splice(i, 1);
      }
    }
  }

  /**
   * Update fog effect
   * @param {number} dt - Normalized delta time
   * @private
   */
  _updateFog(dt) {
    // Smoothly transition fog opacity
    const speed = 0.01 * dt;
    if (this._fogOpacity < this._fogTargetOpacity) {
      this._fogOpacity = Math.min(this._fogTargetOpacity, this._fogOpacity + speed);
    } else if (this._fogOpacity > this._fogTargetOpacity) {
      this._fogOpacity = Math.max(this._fogTargetOpacity, this._fogOpacity - speed);
    }
  }

  /**
   * Draw rain particles
   * @private
   */
  _drawRain() {
    const ctx = this.ctx;

    ctx.lineCap = 'round';

    for (const p of this._particles) {
      ctx.strokeStyle = `rgba(180, 200, 255, ${p.alpha})`;
      ctx.lineWidth = p.size * 0.5;
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x + p.vx * 2, p.y + p.vy * 2);
      ctx.stroke();
    }
  }

  /**
   * Draw snow particles
   * @private
   */
  _drawSnow() {
    const ctx = this.ctx;

    for (const p of this._particles) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`;
      ctx.fill();
    }
  }

  /**
   * Draw fog overlay
   * @private
   */
  _drawFog() {
    if (this._fogOpacity <= 0) return;

    const ctx = this.ctx;

    // Create a gradient fog effect (thicker at edges)
    const gradient = ctx.createRadialGradient(
      this.canvasWidth / 2,
      this.canvasHeight / 2,
      this.canvasWidth * 0.2,
      this.canvasWidth / 2,
      this.canvasHeight / 2,
      this.canvasWidth * 0.7
    );
    gradient.addColorStop(0, `rgba(200, 200, 200, ${this._fogOpacity * 0.3})`);
    gradient.addColorStop(1, `rgba(180, 180, 180, ${this._fogOpacity})`);

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
  }

  /**
   * Draw a static overlay for reduced-motion mode
   * @private
   */
  _drawStaticOverlay() {
    const ctx = this.ctx;

    switch (this.weatherType) {
      case 'rain':
        // Simple blue-tinted overlay
        ctx.fillStyle = `rgba(100, 130, 180, ${0.1 * this.intensity})`;
        ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
        break;
      case 'snow':
        // Simple white overlay
        ctx.fillStyle = `rgba(255, 255, 255, ${0.08 * this.intensity})`;
        ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
        break;
      case 'fog':
        // Simple gray overlay
        ctx.fillStyle = `rgba(180, 180, 180, ${0.15 * this.intensity})`;
        ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
        break;
    }
  }

  /**
   * Clear all particles
   */
  clear() {
    this._particles = [];
    this._fogOpacity = 0;
  }
}
