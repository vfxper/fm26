/**
 * Replay - Records and plays back match state for replay/streaming
 * Stores snapshots at configurable intervals for efficient replay.
 */

export class Replay {
  constructor(options = {}) {
    this.snapshotInterval = options.snapshotInterval || 3; // frames between snapshots
    this.frames = [];
    this.events = [];
    this.frameCount = 0;
    this.isRecording = false;
    this.isPlaying = false;
    this.playbackFrame = 0;
    this.metadata = {
      homeTeam: '',
      awayTeam: '',
      date: null,
      seed: 0,
    };
  }

  /**
   * Start recording
   */
  startRecording(metadata) {
    this.isRecording = true;
    this.frames = [];
    this.events = [];
    this.frameCount = 0;
    this.metadata = { ...this.metadata, ...metadata, date: Date.now() };
  }

  /**
   * Record a frame snapshot
   * @param {Object} snapshot - { ball, players[], matchMinute, score }
   */
  recordFrame(snapshot) {
    if (!this.isRecording) return;
    this.frameCount++;
    
    if (this.frameCount % this.snapshotInterval === 0) {
      this.frames.push({
        frame: this.frameCount,
        ball: {
          x: snapshot.ball.position.x,
          y: snapshot.ball.position.y,
          h: snapshot.ball.height,
          vx: snapshot.ball.velocity.x,
          vy: snapshot.ball.velocity.y,
        },
        players: snapshot.players.map(p => ({
          id: p.id,
          x: p.position.x,
          y: p.position.y,
          facing: p.facing,
          state: p.state,
          hasBall: p.hasBall,
          stamina: Math.round(p.stamina * 100) / 100,
        })),
        minute: snapshot.matchMinute,
        homeScore: snapshot.homeScore,
        awayScore: snapshot.awayScore,
      });
    }
  }

  /**
   * Record an event (goal, foul, card, etc.)
   */
  recordEvent(event) {
    if (!this.isRecording) return;
    this.events.push({ ...event, frame: this.frameCount });
  }

  /**
   * Stop recording
   */
  stopRecording() {
    this.isRecording = false;
  }

  /**
   * Get frame for playback
   * @param {number} frame - Frame number
   */
  getFrame(frame) {
    const idx = Math.floor(frame / this.snapshotInterval);
    return this.frames[idx] || null;
  }

  /**
   * Get interpolated frame between two snapshots
   */
  getInterpolatedFrame(frame) {
    const idx = frame / this.snapshotInterval;
    const lower = Math.floor(idx);
    const upper = Math.ceil(idx);
    const t = idx - lower;

    const f1 = this.frames[lower];
    const f2 = this.frames[upper];
    if (!f1) return null;
    if (!f2 || lower === upper) return f1;

    // Interpolate ball
    const ball = {
      x: f1.ball.x + (f2.ball.x - f1.ball.x) * t,
      y: f1.ball.y + (f2.ball.y - f1.ball.y) * t,
      h: f1.ball.h + (f2.ball.h - f1.ball.h) * t,
    };

    // Interpolate players
    const players = f1.players.map((p1, i) => {
      const p2 = f2.players[i];
      if (!p2) return p1;
      return {
        ...p1,
        x: p1.x + (p2.x - p1.x) * t,
        y: p1.y + (p2.y - p1.y) * t,
        facing: this._lerpAngle(p1.facing, p2.facing, t),
      };
    });

    return { ball, players, minute: f2.minute, homeScore: f2.homeScore, awayScore: f2.awayScore };
  }

  _lerpAngle(a, b, t) {
    let diff = b - a;
    while (diff > Math.PI) diff -= Math.PI * 2;
    while (diff < -Math.PI) diff += Math.PI * 2;
    return a + diff * t;
  }

  /**
   * Export replay data as JSON
   */
  export() {
    return JSON.stringify({
      metadata: this.metadata,
      frames: this.frames,
      events: this.events,
      totalFrames: this.frameCount,
    });
  }

  /**
   * Import replay data
   */
  import(json) {
    const data = typeof json === 'string' ? JSON.parse(json) : json;
    this.metadata = data.metadata;
    this.frames = data.frames;
    this.events = data.events;
    this.frameCount = data.totalFrames;
  }

  get totalDuration() {
    return this.frameCount;
  }

  get snapshotCount() {
    return this.frames.length;
  }
}
