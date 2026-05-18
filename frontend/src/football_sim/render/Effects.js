/**
 * Effects - Particle systems, weather visuals, shadows, celebrations
 */

export class Effects {
  constructor() {
    this.particles = [];
    this.maxParticles = 500;
    
    // Rain drops
    this.rainDrops = [];
    
    // Snow flakes
    this.snowFlakes = [];
    
    // Slide tackle marks
    this.slideMarks = [];
    this.maxSlideMarks = 20;
  }

  /**
   * Update all effects
   * @param {number} dt - Delta time
   * @param {Object} weatherData - From WeatherSystem.getRenderData()
   */
  update(dt, weatherData = {}) {
    // Update particles
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.life -= dt;
      if (p.life <= 0) {
        this.particles.splice(i, 1);
      }
    }
    
    // Update rain
    if (weatherData.rainIntensity > 0) {
      this._updateRain(dt, weatherData);
    }
    
    // Update snow
    if (weatherData.snowIntensity > 0) {
      this._updateSnow(dt, weatherData);
    }
    
    // Fade slide marks
    for (let i = this.slideMarks.length - 1; i >= 0; i--) {
      this.slideMarks[i].alpha -= dt * 0.02;
      if (this.slideMarks[i].alpha <= 0) {
        this.slideMarks.splice(i, 1);
      }
    }
  }

  /**
   * Draw all effects
   * @param {CanvasRenderingContext2D} ctx - With camera transform applied
   * @param {Object} weatherData
   */
  draw(ctx, weatherData = {}) {
    // Slide marks (on pitch)
    this._drawSlideMarks(ctx);
    
    // Particles (splashes, celebrations)
    this._drawParticles(ctx);
  }

  /**
   * Draw weather effects (drawn after everything, in screen space)
   * @param {CanvasRenderingContext2D} ctx - Raw canvas (no camera)
   * @param {number} canvasWidth
   * @param {number} canvasHeight
   * @param {Object} weatherData
   */
  drawWeather(ctx, canvasWidth, canvasHeight, weatherData = {}) {
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    
    if (weatherData.rainIntensity > 0) {
      this._drawRain(ctx, canvasWidth, canvasHeight, weatherData);
    }
    
    if (weatherData.snowIntensity > 0) {
      this._drawSnow(ctx, canvasWidth, canvasHeight, weatherData);
    }
    
    if (weatherData.fogDensity > 0) {
      this._drawFog(ctx, canvasWidth, canvasHeight, weatherData);
    }
    
    ctx.restore();
  }

  /**
   * Spawn celebration particles at position
   */
  spawnCelebration(x, y) {
    for (let i = 0; i < 30; i++) {
      this.particles.push({
        x, y,
        vx: (Math.random() - 0.5) * 10,
        vy: (Math.random() - 0.5) * 10,
        life: 1 + Math.random() * 2,
        color: ['#ffd700', '#ff6b6b', '#4fc3f7', '#66bb6a'][Math.floor(Math.random() * 4)],
        size: 0.1 + Math.random() * 0.2,
      });
    }
  }

  /**
   * Spawn splash particles (wet pitch tackle)
   */
  spawnSplash(x, y) {
    for (let i = 0; i < 8; i++) {
      this.particles.push({
        x, y,
        vx: (Math.random() - 0.5) * 5,
        vy: (Math.random() - 0.5) * 5,
        life: 0.3 + Math.random() * 0.3,
        color: 'rgba(150, 200, 255, 0.6)',
        size: 0.05 + Math.random() * 0.1,
      });
    }
  }

  /**
   * Add slide tackle mark
   */
  addSlideMark(x, y, angle, length = 2) {
    this.slideMarks.push({ x, y, angle, length, alpha: 0.6 });
    if (this.slideMarks.length > this.maxSlideMarks) {
      this.slideMarks.shift();
    }
  }

  _updateRain(dt, weatherData) {
    const count = Math.floor(weatherData.rainIntensity * 50);
    while (this.rainDrops.length < count) {
      this.rainDrops.push({
        x: Math.random(),
        y: Math.random(),
        speed: 0.8 + Math.random() * 0.4,
        length: 0.02 + Math.random() * 0.02,
      });
    }
    while (this.rainDrops.length > count) {
      this.rainDrops.pop();
    }
    
    for (const drop of this.rainDrops) {
      drop.y += drop.speed * dt;
      drop.x += (weatherData.windDirection ? Math.cos(weatherData.windDirection) * 0.1 : 0) * dt;
      if (drop.y > 1) { drop.y = 0; drop.x = Math.random(); }
      if (drop.x > 1) drop.x = 0;
      if (drop.x < 0) drop.x = 1;
    }
  }

  _updateSnow(dt, weatherData) {
    const count = Math.floor(weatherData.snowIntensity * 30);
    while (this.snowFlakes.length < count) {
      this.snowFlakes.push({
        x: Math.random(),
        y: Math.random(),
        speed: 0.1 + Math.random() * 0.15,
        wobble: Math.random() * Math.PI * 2,
        size: 1 + Math.random() * 2,
      });
    }
    
    for (const flake of this.snowFlakes) {
      flake.y += flake.speed * dt;
      flake.wobble += dt * 2;
      flake.x += Math.sin(flake.wobble) * 0.02 * dt;
      if (flake.y > 1) { flake.y = 0; flake.x = Math.random(); }
    }
  }

  _drawParticles(ctx) {
    for (const p of this.particles) {
      const alpha = Math.min(1, p.life);
      ctx.fillStyle = p.color || `rgba(255, 215, 0, ${alpha})`;
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  _drawSlideMarks(ctx) {
    for (const mark of this.slideMarks) {
      ctx.save();
      ctx.translate(mark.x, mark.y);
      ctx.rotate(mark.angle);
      ctx.fillStyle = `rgba(80, 60, 20, ${mark.alpha})`;
      ctx.fillRect(-0.2, -mark.length / 2, 0.4, mark.length);
      ctx.restore();
    }
  }

  _drawRain(ctx, w, h, weatherData) {
    ctx.strokeStyle = `rgba(180, 210, 255, ${weatherData.rainIntensity * 0.4})`;
    ctx.lineWidth = 1;
    
    for (const drop of this.rainDrops) {
      const x = drop.x * w;
      const y = drop.y * h;
      const len = drop.length * h;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + 1, y + len);
      ctx.stroke();
    }
  }

  _drawSnow(ctx, w, h, weatherData) {
    ctx.fillStyle = `rgba(255, 255, 255, ${weatherData.snowIntensity * 0.7})`;
    
    for (const flake of this.snowFlakes) {
      ctx.beginPath();
      ctx.arc(flake.x * w, flake.y * h, flake.size, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  _drawFog(ctx, w, h, weatherData) {
    const gradient = ctx.createLinearGradient(0, 0, 0, h);
    const fogAlpha = weatherData.fogDensity * 0.3;
    gradient.addColorStop(0, `rgba(200, 200, 200, ${fogAlpha * 0.5})`);
    gradient.addColorStop(0.5, `rgba(180, 180, 180, ${fogAlpha})`);
    gradient.addColorStop(1, `rgba(200, 200, 200, ${fogAlpha * 0.7})`);
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, w, h);
  }

  /**
   * Reset all effects
   */
  reset() {
    this.particles = [];
    this.rainDrops = [];
    this.snowFlakes = [];
    this.slideMarks = [];
  }
}
