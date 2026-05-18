/**
 * PitchRenderer - Draws the football pitch with markings, grass stripes, wear
 */
import { PITCH_WIDTH, PITCH_HEIGHT, CENTER_CIRCLE_RADIUS, PENALTY_AREA_WIDTH, PENALTY_AREA_DEPTH, GOAL_AREA_WIDTH, GOAL_AREA_DEPTH, PENALTY_SPOT_DISTANCE, GOAL_WIDTH } from '../core/Constants.js';

export class PitchRenderer {
  constructor() {
    // Grass colors
    this.grassDark = '#2d7a2d';
    this.grassLight = '#35882e';
    this.lineColor = 'rgba(255, 255, 255, 0.85)';
    this.lineWidth = 0.12; // meters
    
    // Stripe width in meters
    this.stripeWidth = PITCH_WIDTH / 12;
  }

  /**
   * Draw the full pitch
   * @param {CanvasRenderingContext2D} ctx - Canvas context (already transformed by camera)
   * @param {Object} surfaceData - From PitchSurface.getRenderData()
   */
  draw(ctx, surfaceData = null) {
    // Background (outside pitch)
    ctx.fillStyle = '#1a5c1a';
    ctx.fillRect(-10, -10, PITCH_WIDTH + 20, PITCH_HEIGHT + 20);
    
    // Grass stripes
    for (let i = 0; i < 12; i++) {
      ctx.fillStyle = i % 2 === 0 ? this.grassDark : this.grassLight;
      ctx.fillRect(i * this.stripeWidth, 0, this.stripeWidth, PITCH_HEIGHT);
    }
    
    // Wear overlay
    if (surfaceData && surfaceData.wearMap) {
      this._drawWear(ctx, surfaceData);
    }
    
    // Snow overlay
    if (surfaceData && surfaceData.snowMap) {
      this._drawSnow(ctx, surfaceData);
    }
    
    // Pitch markings
    ctx.strokeStyle = this.lineColor;
    ctx.lineWidth = this.lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    // Outer boundary
    ctx.strokeRect(0, 0, PITCH_WIDTH, PITCH_HEIGHT);
    
    // Center line
    ctx.beginPath();
    ctx.moveTo(PITCH_WIDTH / 2, 0);
    ctx.lineTo(PITCH_WIDTH / 2, PITCH_HEIGHT);
    ctx.stroke();
    
    // Center circle
    ctx.beginPath();
    ctx.arc(PITCH_WIDTH / 2, PITCH_HEIGHT / 2, CENTER_CIRCLE_RADIUS, 0, Math.PI * 2);
    ctx.stroke();
    
    // Center spot
    ctx.fillStyle = this.lineColor;
    ctx.beginPath();
    ctx.arc(PITCH_WIDTH / 2, PITCH_HEIGHT / 2, 0.2, 0, Math.PI * 2);
    ctx.fill();
    
    // Penalty areas (left)
    const paY = (PITCH_HEIGHT - PENALTY_AREA_WIDTH) / 2;
    ctx.strokeRect(0, paY, PENALTY_AREA_DEPTH, PENALTY_AREA_WIDTH);
    
    // Penalty areas (right)
    ctx.strokeRect(PITCH_WIDTH - PENALTY_AREA_DEPTH, paY, PENALTY_AREA_DEPTH, PENALTY_AREA_WIDTH);
    
    // Goal areas (left)
    const gaY = (PITCH_HEIGHT - GOAL_AREA_WIDTH) / 2;
    ctx.strokeRect(0, gaY, GOAL_AREA_DEPTH, GOAL_AREA_WIDTH);
    
    // Goal areas (right)
    ctx.strokeRect(PITCH_WIDTH - GOAL_AREA_DEPTH, gaY, GOAL_AREA_DEPTH, GOAL_AREA_WIDTH);
    
    // Penalty spots
    ctx.fillStyle = this.lineColor;
    ctx.beginPath();
    ctx.arc(PENALTY_SPOT_DISTANCE, PITCH_HEIGHT / 2, 0.2, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(PITCH_WIDTH - PENALTY_SPOT_DISTANCE, PITCH_HEIGHT / 2, 0.2, 0, Math.PI * 2);
    ctx.fill();
    
    // Penalty arcs
    const arcRadius = CENTER_CIRCLE_RADIUS;
    ctx.beginPath();
    const arcAngle = Math.acos(PENALTY_AREA_DEPTH / arcRadius - PENALTY_SPOT_DISTANCE / arcRadius);
    // Left arc (outside penalty area)
    ctx.arc(PENALTY_SPOT_DISTANCE, PITCH_HEIGHT / 2, arcRadius, -Math.PI/3, Math.PI/3);
    ctx.stroke();
    ctx.beginPath();
    // Right arc
    ctx.arc(PITCH_WIDTH - PENALTY_SPOT_DISTANCE, PITCH_HEIGHT / 2, arcRadius, Math.PI - Math.PI/3, Math.PI + Math.PI/3);
    ctx.stroke();
    
    // Corner arcs
    const cornerRadius = 1; // 1 meter
    ctx.beginPath();
    ctx.arc(0, 0, cornerRadius, 0, Math.PI / 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(PITCH_WIDTH, 0, cornerRadius, Math.PI / 2, Math.PI);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(0, PITCH_HEIGHT, cornerRadius, -Math.PI / 2, 0);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(PITCH_WIDTH, PITCH_HEIGHT, cornerRadius, Math.PI, Math.PI * 1.5);
    ctx.stroke();
    
    // Goals
    this._drawGoals(ctx);
  }

  _drawGoals(ctx) {
    const goalDepth = 2.44;
    const goalY = (PITCH_HEIGHT - GOAL_WIDTH) / 2;
    
    // Left goal
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
    ctx.lineWidth = 0.15;
    ctx.strokeRect(-goalDepth, goalY, goalDepth, GOAL_WIDTH);
    
    // Goal net (left)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 0.05;
    for (let i = 0; i < 8; i++) {
      const y = goalY + (GOAL_WIDTH / 8) * i;
      ctx.beginPath();
      ctx.moveTo(-goalDepth, y);
      ctx.lineTo(0, y);
      ctx.stroke();
    }
    for (let i = 0; i < 4; i++) {
      const x = -goalDepth + (goalDepth / 4) * i;
      ctx.beginPath();
      ctx.moveTo(x, goalY);
      ctx.lineTo(x, goalY + GOAL_WIDTH);
      ctx.stroke();
    }
    
    // Right goal
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
    ctx.lineWidth = 0.15;
    ctx.strokeRect(PITCH_WIDTH, goalY, goalDepth, GOAL_WIDTH);
    
    // Goal net (right)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.lineWidth = 0.05;
    for (let i = 0; i < 8; i++) {
      const y = goalY + (GOAL_WIDTH / 8) * i;
      ctx.beginPath();
      ctx.moveTo(PITCH_WIDTH, y);
      ctx.lineTo(PITCH_WIDTH + goalDepth, y);
      ctx.stroke();
    }
    for (let i = 0; i < 4; i++) {
      const x = PITCH_WIDTH + (goalDepth / 4) * i;
      ctx.beginPath();
      ctx.moveTo(x, goalY);
      ctx.lineTo(x, goalY + GOAL_WIDTH);
      ctx.stroke();
    }
  }

  _drawWear(ctx, surfaceData) {
    const { wearMap, gridCols, gridRows } = surfaceData;
    const cellW = PITCH_WIDTH / gridCols;
    const cellH = PITCH_HEIGHT / gridRows;
    
    for (let r = 0; r < gridRows; r++) {
      for (let c = 0; c < gridCols; c++) {
        const wear = wearMap[r * gridCols + c];
        if (wear > 0.1) {
          ctx.fillStyle = `rgba(139, 119, 42, ${wear * 0.3})`;
          ctx.fillRect(c * cellW, r * cellH, cellW, cellH);
        }
      }
    }
  }

  _drawSnow(ctx, surfaceData) {
    const { snowMap, gridCols, gridRows } = surfaceData;
    const cellW = PITCH_WIDTH / gridCols;
    const cellH = PITCH_HEIGHT / gridRows;
    
    for (let r = 0; r < gridRows; r++) {
      for (let c = 0; c < gridCols; c++) {
        const snow = snowMap[r * gridCols + c];
        if (snow > 0.05) {
          ctx.fillStyle = `rgba(255, 255, 255, ${snow * 0.5})`;
          ctx.fillRect(c * cellW, r * cellH, cellW, cellH);
        }
      }
    }
  }
}
