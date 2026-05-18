/**
 * BallRenderer - Draws ball with shadow, trail, height indication, spin
 */
import { BALL_RADIUS } from '../core/Constants.js';

export class BallRenderer {
  constructor() {
    this.trailEnabled = true;
    this.shadowEnabled = true;
  }

  /**
   * Draw the ball
   * @param {CanvasRenderingContext2D} ctx
   * @param {Object} ball - Ball entity
   * @param {number} alpha - Interpolation factor
   */
  draw(ctx, ball, alpha) {
    const pos = ball.getInterpolatedPosition(alpha);
    const height = ball.height;
    const speed = ball.velocity.length();
    
    // Trail (for fast-moving ball)
    if (this.trailEnabled && ball.trail.length > 1) {
      this._drawTrail(ctx, ball.trail);
    }
    
    // Shadow (separate from ball, distance indicates height)
    if (this.shadowEnabled) {
      const shadowOffset = height * 0.3; // Shadow moves away as ball rises
      const shadowScale = 1 - height * 0.05; // Shadow shrinks as ball rises
      
      ctx.fillStyle = `rgba(0, 0, 0, ${0.3 - height * 0.02})`;
      ctx.beginPath();
      ctx.ellipse(
        pos.x + shadowOffset * 0.2,
        pos.y + shadowOffset,
        BALL_RADIUS * 2 * shadowScale,
        BALL_RADIUS * 1.2 * shadowScale,
        0, 0, Math.PI * 2
      );
      ctx.fill();
    }
    
    // Ball size - make it clearly visible (real ball is 22cm but needs to be visible on screen)
    const visualRadius = BALL_RADIUS * 4 * (1 + height * 0.03);
    
    // Ball body
    ctx.save();
    ctx.translate(pos.x, pos.y - height * 0.15); // Offset up based on height
    ctx.rotate(ball.rollAngle);
    
    // White ball
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(0, 0, visualRadius, 0, Math.PI * 2);
    ctx.fill();
    
    // Ball pattern (pentagons)
    ctx.fillStyle = '#333333';
    const patternSize = visualRadius * 0.35;
    // Center pentagon
    ctx.beginPath();
    for (let i = 0; i < 5; i++) {
      const angle = (i / 5) * Math.PI * 2 - Math.PI / 2;
      const px = Math.cos(angle) * patternSize;
      const py = Math.sin(angle) * patternSize;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();
    
    // Outline
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.lineWidth = 0.03;
    ctx.beginPath();
    ctx.arc(0, 0, visualRadius, 0, Math.PI * 2);
    ctx.stroke();
    
    // Highlight (3D effect)
    const gradient = ctx.createRadialGradient(
      -visualRadius * 0.3, -visualRadius * 0.3, 0,
      0, 0, visualRadius
    );
    gradient.addColorStop(0, 'rgba(255, 255, 255, 0.4)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0.1)');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(0, 0, visualRadius, 0, Math.PI * 2);
    ctx.fill();
    
    ctx.restore();
    
    // Speed indicator (motion blur effect for very fast ball)
    if (speed > 20) {
      const blurLength = Math.min(3, (speed - 20) * 0.1);
      const dir = ball.velocity.normalize();
      ctx.strokeStyle = `rgba(255, 255, 255, ${0.1 + (speed - 20) * 0.01})`;
      ctx.lineWidth = visualRadius * 1.5;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
      ctx.lineTo(pos.x - dir.x * blurLength, pos.y - dir.y * blurLength);
      ctx.stroke();
    }
  }

  _drawTrail(ctx, trail) {
    if (trail.length < 2) return;
    
    ctx.lineCap = 'round';
    for (let i = 1; i < trail.length; i++) {
      const t = i / trail.length;
      const alpha = t * 0.3;
      const width = t * BALL_RADIUS * 4;
      
      ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
      ctx.lineWidth = width;
      ctx.beginPath();
      ctx.moveTo(trail[i - 1].x, trail[i - 1].y);
      ctx.lineTo(trail[i].x, trail[i].y);
      ctx.stroke();
    }
  }
}
