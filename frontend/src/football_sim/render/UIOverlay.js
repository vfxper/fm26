/**
 * UIOverlay - HUD elements: scoreboard, time, events, minimap
 */
import { PITCH_WIDTH, PITCH_HEIGHT } from '../core/Constants.js';

export class UIOverlay {
  constructor(canvasWidth, canvasHeight) {
    this.width = canvasWidth;
    this.height = canvasHeight;
    
    // Event notifications
    this.notifications = [];
    this.maxNotifications = 5;
    this.notificationDuration = 4; // seconds
  }

  /**
   * Draw all UI elements
   * @param {CanvasRenderingContext2D} ctx - Raw canvas context (no camera transform)
   * @param {Object} matchState - MatchState
   * @param {Object} options - { homeTeam, awayTeam, homeColor, awayColor }
   */
  draw(ctx, matchState, options = {}) {
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0); // Reset transform for UI
    
    this._drawScoreboard(ctx, matchState, options);
    this._drawNotifications(ctx);
    this._drawMinimap(ctx, matchState, options);
    
    ctx.restore();
  }

  _drawScoreboard(ctx, matchState, options) {
    const { homeTeam = 'Home', awayTeam = 'Away', homeColor = '#4fc3f7', awayColor = '#ef5350' } = options;
    
    const centerX = this.width / 2;
    const y = 12;
    const boxW = 280;
    const boxH = 36;
    
    // Background
    ctx.fillStyle = 'rgba(15, 25, 35, 0.85)';
    ctx.beginPath();
    ctx.roundRect(centerX - boxW / 2, y, boxW, boxH, 6);
    ctx.fill();
    
    // Border
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = 1;
    ctx.stroke();
    
    // Home team
    ctx.fillStyle = homeColor;
    ctx.font = 'bold 12px sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(homeTeam, centerX - 45, y + boxH / 2);
    
    // Score
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 18px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${matchState.homeScore} - ${matchState.awayScore}`, centerX, y + boxH / 2);
    
    // Away team
    ctx.fillStyle = awayColor;
    ctx.font = 'bold 12px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(awayTeam, centerX + 45, y + boxH / 2);
    
    // Time
    ctx.fillStyle = '#66bb6a';
    ctx.font = 'bold 11px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(matchState.getTimeString(), centerX, y + boxH + 14);
    
    // Possession bar
    const possession = matchState.getPossession();
    const barY = y + boxH + 24;
    const barW = 160;
    const barH = 4;
    
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.fillRect(centerX - barW / 2, barY, barW, barH);
    
    const homeW = (possession.home / 100) * barW;
    ctx.fillStyle = homeColor;
    ctx.fillRect(centerX - barW / 2, barY, homeW, barH);
    ctx.fillStyle = awayColor;
    ctx.fillRect(centerX - barW / 2 + homeW, barY, barW - homeW, barH);
    
    // Possession text
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`${possession.home}%`, centerX - barW / 2, barY + 12);
    ctx.textAlign = 'right';
    ctx.fillText(`${possession.away}%`, centerX + barW / 2, barY + 12);
  }

  _drawNotifications(ctx) {
    const now = performance.now() / 1000;
    
    // Remove expired
    this.notifications = this.notifications.filter(n => now - n.time < this.notificationDuration);
    
    const x = this.width / 2;
    let y = this.height - 60;
    
    for (let i = this.notifications.length - 1; i >= 0; i--) {
      const notif = this.notifications[i];
      const age = now - notif.time;
      const alpha = Math.min(1, (this.notificationDuration - age) / 0.5);
      
      ctx.fillStyle = `rgba(15, 25, 35, ${0.8 * alpha})`;
      ctx.beginPath();
      ctx.roundRect(x - 140, y - 12, 280, 24, 4);
      ctx.fill();
      
      ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(notif.text, x, y);
      
      y -= 28;
    }
  }

  _drawMinimap(ctx, matchState, options) {
    const { players = [], ball = null, homeColor = '#4fc3f7', awayColor = '#ef5350' } = options;
    
    const mmW = 120;
    const mmH = 78;
    const mmX = this.width - mmW - 10;
    const mmY = this.height - mmH - 10;
    const scaleX = mmW / PITCH_WIDTH;
    const scaleY = mmH / PITCH_HEIGHT;
    
    // Background
    ctx.fillStyle = 'rgba(30, 80, 30, 0.7)';
    ctx.beginPath();
    ctx.roundRect(mmX, mmY, mmW, mmH, 4);
    ctx.fill();
    
    // Border
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 1;
    ctx.strokeRect(mmX, mmY, mmW, mmH);
    
    // Center line
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.beginPath();
    ctx.moveTo(mmX + mmW / 2, mmY);
    ctx.lineTo(mmX + mmW / 2, mmY + mmH);
    ctx.stroke();
    
    // Players
    if (players.length > 0) {
      for (const player of players) {
        if (!player.isActive) continue;
        const px = mmX + player.position.x * scaleX;
        const py = mmY + player.position.y * scaleY;
        
        ctx.fillStyle = player.teamSide === 'home' ? homeColor : awayColor;
        ctx.beginPath();
        ctx.arc(px, py, 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    
    // Ball
    if (ball) {
      const bx = mmX + ball.position.x * scaleX;
      const by = mmY + ball.position.y * scaleY;
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(bx, by, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  /**
   * Add a notification
   */
  addNotification(text) {
    this.notifications.push({ text, time: performance.now() / 1000 });
    if (this.notifications.length > this.maxNotifications) {
      this.notifications.shift();
    }
  }

  /**
   * Resize
   */
  resize(width, height) {
    this.width = width;
    this.height = height;
  }
}
