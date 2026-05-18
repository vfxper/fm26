/**
 * PitchSurface - Physical properties of the pitch surface
 * Handles friction, wear, snow accumulation, puddles, bumps
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT, FRICTION_DRY, FRICTION_WET, FRICTION_SNOW } from '../core/Constants.js';

export const SurfaceType = {
  DRY: 'dry',
  DAMP: 'damp',
  WET: 'wet',
  FROZEN: 'frozen',
  SNOWY: 'snowy',
};

export class PitchSurface {
  constructor() {
    // Grid resolution for surface detail (10x10 meter cells)
    this.gridCols = Math.ceil(PITCH_WIDTH / 10);
    this.gridRows = Math.ceil(PITCH_HEIGHT / 10);
    
    // Wear map (0 = pristine, 1 = completely worn)
    this.wearMap = new Float32Array(this.gridCols * this.gridRows);
    
    // Snow accumulation map (0 = none, 1 = thick)
    this.snowMap = new Float32Array(this.gridCols * this.gridRows);
    
    // Puddle map (0 = dry, 1 = deep puddle)
    this.puddleMap = new Float32Array(this.gridCols * this.gridRows);
    
    // Base surface type
    this.surfaceType = SurfaceType.DRY;
    
    // Base friction coefficient
    this.baseFriction = FRICTION_DRY;
    
    // Bump probability (increases with wear)
    this.bumpChance = 0.002; // per meter of ball travel
  }

  /**
   * Set weather conditions
   */
  setConditions(surfaceType) {
    this.surfaceType = surfaceType;
    switch (surfaceType) {
      case SurfaceType.DRY: this.baseFriction = FRICTION_DRY; break;
      case SurfaceType.DAMP: this.baseFriction = (FRICTION_DRY + FRICTION_WET) / 2; break;
      case SurfaceType.WET: this.baseFriction = FRICTION_WET; break;
      case SurfaceType.FROZEN: this.baseFriction = FRICTION_SNOW * 0.8; break;
      case SurfaceType.SNOWY: this.baseFriction = FRICTION_SNOW; break;
    }
  }

  /**
   * Get friction at a specific position
   * @param {number} x - X position in meters
   * @param {number} y - Y position in meters
   * @returns {number} Friction coefficient
   */
  getFrictionAt(x, y) {
    const col = Math.min(this.gridCols - 1, Math.max(0, Math.floor(x / 10)));
    const row = Math.min(this.gridRows - 1, Math.max(0, Math.floor(y / 10)));
    const idx = row * this.gridCols + col;
    
    let friction = this.baseFriction;
    
    // Worn areas have slightly less friction (smoother)
    const wear = this.wearMap[idx];
    friction *= (1 - wear * 0.15);
    
    // Puddles reduce friction significantly
    const puddle = this.puddleMap[idx];
    friction *= (1 - puddle * 0.4);
    
    // Snow adds extra friction (ball sinks in)
    const snow = this.snowMap[idx];
    friction += snow * 0.3;
    
    return Math.max(0.05, friction);
  }

  /**
   * Check if ball hits a bump at position
   * @param {number} x - X position
   * @param {number} y - Y position
   * @param {Object} rng - Random number generator
   * @returns {Vector2|null} Deflection vector if bump hit, null otherwise
   */
  checkBump(x, y, rng) {
    const col = Math.min(this.gridCols - 1, Math.max(0, Math.floor(x / 10)));
    const row = Math.min(this.gridRows - 1, Math.max(0, Math.floor(y / 10)));
    const idx = row * this.gridCols + col;
    
    // Bump chance increases with wear
    const wear = this.wearMap[idx];
    const chance = this.bumpChance * (1 + wear * 5);
    
    if (rng.chance(chance)) {
      // Random deflection angle (5-15 degrees)
      const angle = rng.range(-0.26, 0.26); // ±15°
      const strength = rng.range(0.5, 2.0); // m/s vertical bounce
      return { angle, verticalBounce: strength };
    }
    return null;
  }

  /**
   * Add wear at a position (called when players run/slide)
   * @param {number} x - X position
   * @param {number} y - Y position
   * @param {number} amount - Wear amount (0-1)
   */
  addWear(x, y, amount) {
    const col = Math.min(this.gridCols - 1, Math.max(0, Math.floor(x / 10)));
    const row = Math.min(this.gridRows - 1, Math.max(0, Math.floor(y / 10)));
    const idx = row * this.gridCols + col;
    this.wearMap[idx] = Math.min(1, this.wearMap[idx] + amount);
  }

  /**
   * Add snow at position (cleared by ball/player movement)
   */
  addSnow(amount) {
    for (let i = 0; i < this.snowMap.length; i++) {
      this.snowMap[i] = Math.min(1, this.snowMap[i] + amount);
    }
  }

  /**
   * Clear snow at position (ball/player passed through)
   */
  clearSnowAt(x, y, radius = 1) {
    const col = Math.min(this.gridCols - 1, Math.max(0, Math.floor(x / 10)));
    const row = Math.min(this.gridRows - 1, Math.max(0, Math.floor(y / 10)));
    const idx = row * this.gridCols + col;
    this.snowMap[idx] = Math.max(0, this.snowMap[idx] - 0.3);
  }

  /**
   * Add puddles (rain accumulation)
   */
  addPuddles(intensity) {
    // Puddles form in low areas (center circle, penalty areas)
    for (let r = 0; r < this.gridRows; r++) {
      for (let c = 0; c < this.gridCols; c++) {
        const idx = r * this.gridCols + c;
        const x = c * 10 + 5;
        const y = r * 10 + 5;
        
        // More puddles in center and penalty areas
        let puddleFactor = 0.3;
        const distToCenter = Math.sqrt((x - PITCH_WIDTH/2)**2 + (y - PITCH_HEIGHT/2)**2);
        if (distToCenter < 15) puddleFactor = 0.6;
        if (x < 16.5 || x > PITCH_WIDTH - 16.5) puddleFactor = 0.5;
        
        this.puddleMap[idx] = Math.min(1, this.puddleMap[idx] + intensity * puddleFactor * 0.01);
      }
    }
  }

  /**
   * Get surface data for rendering
   */
  getRenderData() {
    return {
      wearMap: this.wearMap,
      snowMap: this.snowMap,
      puddleMap: this.puddleMap,
      gridCols: this.gridCols,
      gridRows: this.gridRows,
      surfaceType: this.surfaceType,
    };
  }

  /**
   * Reset surface to pristine
   */
  reset() {
    this.wearMap.fill(0);
    this.snowMap.fill(0);
    this.puddleMap.fill(0);
  }
}
