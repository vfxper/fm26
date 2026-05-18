/**
 * PlayerRenderer - Draws players with procedural animation, shadows, names
 */
import { PLAYER_RADIUS } from '../core/Constants.js';

export class PlayerRenderer {
  constructor() {
    this.showNames = true;
    this.showNumbers = true;
    this.playerScale = 2.5; // Увеличенный масштаб для видимости
  }

  /**
   * Draw a single player
   * @param {CanvasRenderingContext2D} ctx
   * @param {Object} player - Player entity
   * @param {Object} pose - Animation pose from ProceduralWalk/KickAnimation
   * @param {number} alpha - Interpolation factor
   * @param {Object} options - { teamColor, isHighlighted, hasBall }
   */
  drawPlayer(ctx, player, pose, alpha, options = {}) {
    const pos = player.getInterpolatedPosition(alpha);
    const { teamColor = '#4fc3f7', isHighlighted = false, hasBall = false } = options;
    
    ctx.save();
    ctx.translate(pos.x, pos.y);
    ctx.rotate(player.facing);
    
    // Shadow (offset based on "height" - always on ground)
    ctx.fillStyle = 'rgba(0, 0, 0, 0.25)';
    ctx.beginPath();
    ctx.ellipse(0.1, 0.15, PLAYER_RADIUS * 0.9, PLAYER_RADIUS * 0.5, 0, 0, Math.PI * 2);
    ctx.fill();
    
    // Body (main circle)
    const radius = PLAYER_RADIUS * this.playerScale;
    
    // Highlight glow for ball carrier
    if (hasBall || isHighlighted) {
      ctx.shadowColor = hasBall ? '#ffd700' : '#ffffff';
      ctx.shadowBlur = 0.5;
    }
    
    // Jersey (main body)
    ctx.fillStyle = teamColor;
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
    
    // Jersey outline
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.lineWidth = 0.05;
    ctx.stroke();
    
    // Direction indicator (small triangle showing facing)
    ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
    ctx.beginPath();
    ctx.moveTo(radius * 0.8, 0);
    ctx.lineTo(radius * 0.3, -radius * 0.3);
    ctx.lineTo(radius * 0.3, radius * 0.3);
    ctx.closePath();
    ctx.fill();
    
    // Legs (from pose data)
    if (pose) {
      this._drawLegs(ctx, pose, radius, teamColor);
    }
    
    ctx.restore();
    
    // Number (drawn without rotation for readability)
    if (this.showNumbers) {
      ctx.fillStyle = '#ffffff';
      ctx.font = `bold ${radius * 1.2}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(player.number, pos.x, pos.y);
    }
    
    // Name (below player)
    if (this.showNames) {
      ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.font = `${radius * 0.7}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillText(player.name.split(' ').pop(), pos.x, pos.y + radius + 0.3);
    }
    
    // Fatigue indicator (small bar above player when tired)
    if (player.stamina < 0.5) {
      this._drawFatigueBar(ctx, pos, radius, player.stamina);
    }
    
    // Card indicator
    if (player.matchStats.yellowCards > 0) {
      this._drawCardIndicator(ctx, pos, radius, player.matchStats.yellowCards, player.matchStats.redCards);
    }
  }

  _drawLegs(ctx, pose, radius, teamColor) {
    // Draw simplified leg positions from pose
    const legColor = this._darkenColor(teamColor, 0.3);
    ctx.fillStyle = legColor;
    
    if (pose.leftFoot) {
      const lf = pose.leftFoot;
      ctx.beginPath();
      ctx.arc(lf.x * 0.05, lf.y * 0.05, radius * 0.25, 0, Math.PI * 2);
      ctx.fill();
    }
    if (pose.rightFoot) {
      const rf = pose.rightFoot;
      ctx.beginPath();
      ctx.arc(rf.x * 0.05, rf.y * 0.05, radius * 0.25, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  _drawFatigueBar(ctx, pos, radius, stamina) {
    const barWidth = radius * 2;
    const barHeight = 0.12;
    const x = pos.x - barWidth / 2;
    const y = pos.y - radius - 0.5;
    
    // Background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(x, y, barWidth, barHeight);
    
    // Fill
    const color = stamina > 0.3 ? '#ffa726' : '#ef5350';
    ctx.fillStyle = color;
    ctx.fillRect(x, y, barWidth * stamina, barHeight);
  }

  _drawCardIndicator(ctx, pos, radius, yellows, reds) {
    const x = pos.x + radius * 0.8;
    const y = pos.y - radius * 0.8;
    const size = 0.25;
    
    if (reds > 0) {
      ctx.fillStyle = '#f44336';
    } else {
      ctx.fillStyle = '#ffeb3b';
    }
    ctx.fillRect(x, y, size, size * 1.4);
  }

  _darkenColor(hex, amount) {
    // Simple color darkening
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    const factor = 1 - amount;
    return `rgb(${Math.floor(r * factor)}, ${Math.floor(g * factor)}, ${Math.floor(b * factor)})`;
  }
}
