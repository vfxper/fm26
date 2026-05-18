/**
 * Match Renderer Module (Legacy)
 * 
 * This file is kept for backward compatibility.
 * The full modular implementation is in ./match-renderer/ directory.
 * 
 * For new code, import from './match-renderer/index.js' instead:
 *   import { MatchRenderer } from './match-renderer/index.js';
 */

// Re-export the new modular MatchRenderer
export { MatchRenderer as ModularMatchRenderer } from './match-renderer/index.js';

/**
 * Legacy MatchRenderer class (preserved for backward compatibility)
 * @deprecated Use ModularMatchRenderer from './match-renderer/index.js' instead
 */
export class MatchRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    
    // Match state
    this.events = [];
    this.currentEventIndex = 0;
    this.playbackSpeed = 1; // 1x, 2x, 4x, or 0 for instant
    this.isPaused = false;
    this.isPlaying = false;
    
    // Pitch dimensions (meters)
    this.pitchWidth = 105;
    this.pitchHeight = 68;
    
    // Player and ball state
    this.players = new Map(); // player_id -> {x, y, team, number, name}
    this.ball = { x: 52.5, y: 34 }; // Center of pitch
    
    // Animation
    this.animationFrame = null;
    this.lastFrameTime = 0;
    
    // Match info
    this.homeTeam = { name: 'Home', score: 0, color: '#ff0000' };
    this.awayTeam = { name: 'Away', score: 0, color: '#0000ff' };
    this.currentMinute = 0;
    this.currentSecond = 0;
    
    // Initialize canvas size
    this.resize();
  }

  /**
   * Resize canvas to fit container
   */
  resize() {
    const container = this.canvas.parentElement;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    // Set canvas size
    this.canvas.width = containerWidth;
    this.canvas.height = containerHeight;
    
    // Calculate scale to fit pitch
    const widthScale = this.canvas.width / this.pitchWidth;
    const heightScale = this.canvas.height / this.pitchHeight;
    this.scale = Math.min(widthScale, heightScale) * 0.9; // 90% to leave margins
    
    // Calculate offsets to center pitch
    this.offsetX = (this.canvas.width - this.pitchWidth * this.scale) / 2;
    this.offsetY = (this.canvas.height - this.pitchHeight * this.scale) / 2;
    
    // Redraw if not playing
    if (!this.isPlaying) {
      this.draw();
    }
  }

  /**
   * Load match data and start rendering
   * @param {Object} matchData - Match data with events, teams, players
   */
  loadMatch(matchData) {
    this.events = matchData.events || [];
    this.currentEventIndex = 0;
    
    // Set team info
    this.homeTeam = {
      name: matchData.homeTeam?.name || 'Home',
      score: 0,
      color: matchData.homeTeam?.color || '#ff0000',
    };
    
    this.awayTeam = {
      name: matchData.awayTeam?.name || 'Away',
      score: 0,
      color: matchData.awayTeam?.color || '#0000ff',
    };
    
    // Initialize player positions
    this.initializePlayers(matchData.homeTeam?.players || [], matchData.awayTeam?.players || []);
    
    // Reset match time
    this.currentMinute = 0;
    this.currentSecond = 0;
    
    // Draw initial state
    this.draw();
  }

  /**
   * Initialize player positions based on formation
   * @param {Array} homePlayers - Home team players
   * @param {Array} awayPlayers - Away team players
   */
  initializePlayers(homePlayers, awayPlayers) {
    this.players.clear();
    
    // Add home players
    homePlayers.forEach((player, index) => {
      this.players.set(player.id, {
        x: player.x || this.getDefaultPosition(index, 'home').x,
        y: player.y || this.getDefaultPosition(index, 'home').y,
        team: 'home',
        number: player.number || index + 1,
        name: player.name || `Player ${index + 1}`,
      });
    });
    
    // Add away players
    awayPlayers.forEach((player, index) => {
      this.players.set(player.id, {
        x: player.x || this.getDefaultPosition(index, 'away').x,
        y: player.y || this.getDefaultPosition(index, 'away').y,
        team: 'away',
        number: player.number || index + 1,
        name: player.name || `Player ${index + 1}`,
      });
    });
  }

  /**
   * Get default position for player based on index and team
   * @param {number} index - Player index
   * @param {string} team - 'home' or 'away'
   * @returns {Object} {x, y} position
   */
  getDefaultPosition(index, team) {
    // Simple 4-4-2 formation
    const positions = [
      { x: 10, y: 34 },  // GK
      { x: 25, y: 10 },  // LB
      { x: 25, y: 24 },  // CB
      { x: 25, y: 44 },  // CB
      { x: 25, y: 58 },  // RB
      { x: 50, y: 10 },  // LM
      { x: 50, y: 24 },  // CM
      { x: 50, y: 44 },  // CM
      { x: 50, y: 58 },  // RM
      { x: 80, y: 24 },  // ST
      { x: 80, y: 44 },  // ST
    ];
    
    const pos = positions[index] || { x: 52.5, y: 34 };
    
    // Mirror for away team
    if (team === 'away') {
      return { x: this.pitchWidth - pos.x, y: pos.y };
    }
    
    return pos;
  }

  /**
   * Start match playback
   */
  start() {
    if (this.isPlaying) return;
    
    this.isPlaying = true;
    this.isPaused = false;
    this.lastFrameTime = performance.now();
    this.animate();
  }

  /**
   * Pause match playback
   */
  pause() {
    this.isPaused = true;
  }

  /**
   * Resume match playback
   */
  resume() {
    if (!this.isPlaying) {
      this.start();
    } else {
      this.isPaused = false;
      this.lastFrameTime = performance.now();
    }
  }

  /**
   * Stop match playback
   */
  stop() {
    this.isPlaying = false;
    this.isPaused = false;
    
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
  }

  /**
   * Set playback speed
   * @param {number} speed - 1, 2, 4, or 0 for instant
   */
  setSpeed(speed) {
    this.playbackSpeed = speed;
  }

  /**
   * Main animation loop
   */
  animate() {
    if (!this.isPlaying) return;
    
    const currentTime = performance.now();
    const deltaTime = currentTime - this.lastFrameTime;
    this.lastFrameTime = currentTime;
    
    // Update match state if not paused
    if (!this.isPaused) {
      this.update(deltaTime);
    }
    
    // Draw current state
    this.draw();
    
    // Continue animation loop
    this.animationFrame = requestAnimationFrame(() => this.animate());
  }

  /**
   * Update match state
   * @param {number} deltaTime - Time since last frame (ms)
   */
  update(deltaTime) {
    // Process events based on playback speed
    if (this.playbackSpeed === 0) {
      // Instant: process all remaining events
      while (this.currentEventIndex < this.events.length) {
        this.processEvent(this.events[this.currentEventIndex]);
        this.currentEventIndex++;
      }
      this.stop();
    } else {
      // Normal playback: process events at specified speed
      // TODO: Implement time-based event processing
    }
  }

  /**
   * Process a single match event
   * @param {Object} event - Match event
   */
  processEvent(event) {
    this.currentMinute = event.minute || 0;
    this.currentSecond = event.second || 0;
    
    switch (event.event_type) {
      case 'GOAL':
        if (event.team === 'home') {
          this.homeTeam.score++;
        } else {
          this.awayTeam.score++;
        }
        break;
      
      case 'PASS':
      case 'SHOT':
      case 'TACKLE':
        // Update ball position
        if (event.position) {
          this.ball.x = event.position.x;
          this.ball.y = event.position.y;
        }
        break;
    }
  }

  /**
   * Draw current match state
   */
  draw() {
    // Clear canvas
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Draw pitch
    this.drawPitch();
    
    // Draw players
    this.drawPlayers();
    
    // Draw ball
    this.drawBall();
    
    // Draw UI overlay
    this.drawOverlay();
  }

  /**
   * Draw pitch with markings
   */
  drawPitch() {
    const ctx = this.ctx;
    
    // Pitch background
    ctx.fillStyle = '#2d5016';
    ctx.fillRect(
      this.offsetX,
      this.offsetY,
      this.pitchWidth * this.scale,
      this.pitchHeight * this.scale
    );
    
    // Pitch markings
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    
    // Outer boundary
    ctx.strokeRect(
      this.offsetX,
      this.offsetY,
      this.pitchWidth * this.scale,
      this.pitchHeight * this.scale
    );
    
    // Center line
    const centerX = this.offsetX + (this.pitchWidth / 2) * this.scale;
    ctx.beginPath();
    ctx.moveTo(centerX, this.offsetY);
    ctx.lineTo(centerX, this.offsetY + this.pitchHeight * this.scale);
    ctx.stroke();
    
    // Center circle
    const centerY = this.offsetY + (this.pitchHeight / 2) * this.scale;
    ctx.beginPath();
    ctx.arc(centerX, centerY, 9.15 * this.scale, 0, Math.PI * 2);
    ctx.stroke();
    
    // Center spot
    ctx.beginPath();
    ctx.arc(centerX, centerY, 0.3 * this.scale, 0, Math.PI * 2);
    ctx.fill();
  }

  /**
   * Draw all players
   */
  drawPlayers() {
    this.players.forEach((player) => {
      const x = this.offsetX + player.x * this.scale;
      const y = this.offsetY + player.y * this.scale;
      const radius = 8;
      
      // Player circle
      this.ctx.fillStyle = player.team === 'home' ? this.homeTeam.color : this.awayTeam.color;
      this.ctx.beginPath();
      this.ctx.arc(x, y, radius, 0, Math.PI * 2);
      this.ctx.fill();
      
      // Player number
      this.ctx.fillStyle = '#ffffff';
      this.ctx.font = 'bold 10px Arial';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'middle';
      this.ctx.fillText(player.number, x, y);
    });
  }

  /**
   * Draw ball
   */
  drawBall() {
    const x = this.offsetX + this.ball.x * this.scale;
    const y = this.offsetY + this.ball.y * this.scale;
    const radius = 4;
    
    // Ball
    this.ctx.fillStyle = '#ffffff';
    this.ctx.beginPath();
    this.ctx.arc(x, y, radius, 0, Math.PI * 2);
    this.ctx.fill();
    
    // Ball outline
    this.ctx.strokeStyle = '#000000';
    this.ctx.lineWidth = 1;
    this.ctx.stroke();
  }

  /**
   * Draw UI overlay (score, time, etc.)
   */
  drawOverlay() {
    const ctx = this.ctx;
    
    // Scoreboard background
    const scoreboardWidth = 200;
    const scoreboardHeight = 60;
    const scoreboardX = (this.canvas.width - scoreboardWidth) / 2;
    const scoreboardY = 10;
    
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(scoreboardX, scoreboardY, scoreboardWidth, scoreboardHeight);
    
    // Score text
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 24px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    const scoreText = `${this.homeTeam.score} - ${this.awayTeam.score}`;
    ctx.fillText(scoreText, this.canvas.width / 2, scoreboardY + 25);
    
    // Time text
    ctx.font = '14px Arial';
    const timeText = `${this.currentMinute}'`;
    ctx.fillText(timeText, this.canvas.width / 2, scoreboardY + 45);
  }

  /**
   * Convert screen coordinates to pitch coordinates
   * @param {number} screenX - Screen X coordinate
   * @param {number} screenY - Screen Y coordinate
   * @returns {Object} {x, y} pitch coordinates
   */
  screenToPitch(screenX, screenY) {
    return {
      x: (screenX - this.offsetX) / this.scale,
      y: (screenY - this.offsetY) / this.scale,
    };
  }

  /**
   * Convert pitch coordinates to screen coordinates
   * @param {number} pitchX - Pitch X coordinate
   * @param {number} pitchY - Pitch Y coordinate
   * @returns {Object} {x, y} screen coordinates
   */
  pitchToScreen(pitchX, pitchY) {
    return {
      x: this.offsetX + pitchX * this.scale,
      y: this.offsetY + pitchY * this.scale,
    };
  }
}
