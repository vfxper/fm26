/**
 * Camera - Follows ball with smooth lerp, zoom control, minimap
 */
import { PITCH_WIDTH, PITCH_HEIGHT, CAMERA_LERP_SPEED } from '../core/Constants.js';

export class Camera {
  constructor(canvasWidth, canvasHeight) {
    this.canvasWidth = canvasWidth;
    this.canvasHeight = canvasHeight;
    
    // Camera position (center of view in world coords)
    this.x = PITCH_WIDTH / 2;
    this.y = PITCH_HEIGHT / 2;
    
    // Target (what camera follows)
    this.targetX = this.x;
    this.targetY = this.y;
    
    // Zoom
    this.zoom = 1.0;
    this.targetZoom = 1.0;
    this.minZoom = 0.5;
    this.maxZoom = 2.5;
    
    // Pixels per meter at zoom 1.0
    this.baseScale = Math.min(
      canvasWidth / (PITCH_WIDTH + 10),
      canvasHeight / (PITCH_HEIGHT + 10)
    );
    
    // Smoothing
    this.lerpSpeed = CAMERA_LERP_SPEED;
    this.zoomLerpSpeed = 0.03;
    
    // Shake (for goals, big tackles)
    this.shakeIntensity = 0;
    this.shakeDecay = 5;
    this.shakeOffsetX = 0;
    this.shakeOffsetY = 0;
    
    // Mode
    this.mode = 'follow_ball'; // 'follow_ball', 'tactical', 'fixed'
  }

  /**
   * Update camera position
   * @param {Object} ball - Ball entity
   * @param {number} dt - Delta time
   */
  update(ball, dt) {
    if (this.mode === 'follow_ball' && ball) {
      this.targetX = ball.position.x;
      this.targetY = ball.position.y;
    } else if (this.mode === 'tactical') {
      // Show full pitch
      this.targetX = PITCH_WIDTH / 2;
      this.targetY = PITCH_HEIGHT / 2;
      this.targetZoom = this.minZoom;
    }
    
    // Smooth follow
    this.x += (this.targetX - this.x) * this.lerpSpeed;
    this.y += (this.targetY - this.y) * this.lerpSpeed;
    this.zoom += (this.targetZoom - this.zoom) * this.zoomLerpSpeed;
    
    // Clamp camera to pitch bounds (with margin)
    const margin = 5;
    const viewW = this.canvasWidth / (this.baseScale * this.zoom) / 2;
    const viewH = this.canvasHeight / (this.baseScale * this.zoom) / 2;
    
    this.x = Math.max(-margin + viewW, Math.min(PITCH_WIDTH + margin - viewW, this.x));
    this.y = Math.max(-margin + viewH, Math.min(PITCH_HEIGHT + margin - viewH, this.y));
    
    // Update shake
    if (this.shakeIntensity > 0.01) {
      this.shakeOffsetX = (Math.random() - 0.5) * this.shakeIntensity * 2;
      this.shakeOffsetY = (Math.random() - 0.5) * this.shakeIntensity * 2;
      this.shakeIntensity *= Math.exp(-this.shakeDecay * dt);
    } else {
      this.shakeOffsetX = 0;
      this.shakeOffsetY = 0;
      this.shakeIntensity = 0;
    }
  }

  /**
   * Apply camera transform to canvas context
   * @param {CanvasRenderingContext2D} ctx
   */
  applyTransform(ctx) {
    const scale = this.baseScale * this.zoom;
    const offsetX = this.canvasWidth / 2 - (this.x * scale) + this.shakeOffsetX;
    const offsetY = this.canvasHeight / 2 - (this.y * scale) + this.shakeOffsetY;
    
    ctx.save();
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);
  }

  /**
   * Convert world coordinates to screen coordinates
   */
  worldToScreen(worldX, worldY) {
    const scale = this.baseScale * this.zoom;
    return {
      x: (worldX - this.x) * scale + this.canvasWidth / 2 + this.shakeOffsetX,
      y: (worldY - this.y) * scale + this.canvasHeight / 2 + this.shakeOffsetY,
    };
  }

  /**
   * Convert screen coordinates to world coordinates
   */
  screenToWorld(screenX, screenY) {
    const scale = this.baseScale * this.zoom;
    return {
      x: (screenX - this.canvasWidth / 2 - this.shakeOffsetX) / scale + this.x,
      y: (screenY - this.canvasHeight / 2 - this.shakeOffsetY) / scale + this.y,
    };
  }

  /**
   * Trigger camera shake (for goals, big tackles)
   * @param {number} intensity - Shake strength (pixels)
   */
  shake(intensity = 3) {
    this.shakeIntensity = intensity;
  }

  /**
   * Set zoom level
   */
  setZoom(zoom) {
    this.targetZoom = Math.max(this.minZoom, Math.min(this.maxZoom, zoom));
  }

  /**
   * Set camera mode
   */
  setMode(mode) {
    this.mode = mode;
    if (mode === 'tactical') {
      this.targetZoom = this.minZoom;
    } else if (mode === 'follow_ball') {
      this.targetZoom = 1.0;
    }
  }

  /**
   * Resize handler
   */
  resize(width, height) {
    this.canvasWidth = width;
    this.canvasHeight = height;
    this.baseScale = Math.min(
      width / (PITCH_WIDTH + 10),
      height / (PITCH_HEIGHT + 10)
    );
  }
}
