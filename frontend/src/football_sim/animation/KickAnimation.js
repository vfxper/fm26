/**
 * KickAnimation - Procedural kick animations (shot, pass, cross, tackle)
 * Phases: wind-up → contact → follow-through
 */

export const KickType = {
  INSTEP: 'instep',       // Laces - power shot
  INSIDE: 'inside',       // Side foot - accuracy
  OUTSIDE: 'outside',     // Outside foot - curve
  TOE_POKE: 'toe_poke',  // Quick poke
  VOLLEY: 'volley',       // Ball in air
  HEADER: 'header',       // Heading
  SLIDE: 'slide',         // Slide tackle
};

export class KickAnimation {
  constructor() {
    this.active = false;
    this.type = KickType.INSTEP;
    this.phase = 0;        // 0-1 progress
    this.duration = 0.4;   // Total animation time
    this.timer = 0;
    this.contactPoint = 0.6; // Phase at which ball is struck (60% through)
    this.contacted = false;
    this.foot = 'right';   // Which foot is kicking
  }

  /**
   * Start a kick animation
   * @param {string} type - KickType
   * @param {string} foot - 'left' or 'right'
   * @param {number} power - 0-1 (affects wind-up time)
   */
  start(type, foot = 'right', power = 0.7) {
    this.active = true;
    this.type = type;
    this.foot = foot;
    this.phase = 0;
    this.contacted = false;
    
    // Duration depends on type and power
    switch (type) {
      case KickType.INSTEP:
        this.duration = 0.3 + power * 0.2; // 0.3-0.5s
        this.contactPoint = 0.6;
        break;
      case KickType.INSIDE:
        this.duration = 0.25 + power * 0.1;
        this.contactPoint = 0.55;
        break;
      case KickType.OUTSIDE:
        this.duration = 0.3 + power * 0.15;
        this.contactPoint = 0.6;
        break;
      case KickType.TOE_POKE:
        this.duration = 0.15;
        this.contactPoint = 0.5;
        break;
      case KickType.VOLLEY:
        this.duration = 0.35 + power * 0.15;
        this.contactPoint = 0.55;
        break;
      case KickType.HEADER:
        this.duration = 0.3;
        this.contactPoint = 0.5;
        break;
      case KickType.SLIDE:
        this.duration = 0.6;
        this.contactPoint = 0.4;
        break;
    }
    
    this.timer = this.duration;
  }

  /**
   * Update animation
   * @param {number} dt - Delta time
   * @returns {Object} Bone offsets + contact event
   */
  update(dt) {
    if (!this.active) return null;
    
    this.timer -= dt;
    this.phase = 1 - (this.timer / this.duration);
    
    // Check for contact moment
    let contactEvent = false;
    if (!this.contacted && this.phase >= this.contactPoint) {
      this.contacted = true;
      contactEvent = true;
    }
    
    // Animation complete
    if (this.timer <= 0) {
      this.active = false;
      this.phase = 1;
    }
    
    const pose = this._generatePose();
    return { pose, contactEvent, phase: this.phase, active: this.active };
  }

  /**
   * Generate bone offsets for current phase
   */
  _generatePose() {
    const p = this.phase;
    const isRight = this.foot === 'right';
    const side = isRight ? 1 : -1;
    
    switch (this.type) {
      case KickType.INSTEP:
      case KickType.INSIDE:
      case KickType.OUTSIDE:
        return this._getKickPose(p, side);
      case KickType.HEADER:
        return this._getHeaderPose(p);
      case KickType.SLIDE:
        return this._getSlidePose(p, side);
      case KickType.VOLLEY:
        return this._getVolleyPose(p, side);
      default:
        return this._getKickPose(p, side);
    }
  }

  _getKickPose(phase, side) {
    // Wind-up: leg goes back
    // Contact: leg swings forward
    // Follow-through: leg continues forward and up
    
    let kickLegY, kickLegX, standLegY;
    let bodyLean;
    
    if (phase < this.contactPoint) {
      // Wind-up phase
      const t = phase / this.contactPoint;
      kickLegY = 4 - t * 6; // Leg goes back (y increases = back in top-down)
      kickLegX = side * (2 + t * 2);
      standLegY = 4;
      bodyLean = -t * 1.5; // Lean back slightly
    } else {
      // Follow-through
      const t = (phase - this.contactPoint) / (1 - this.contactPoint);
      kickLegY = -2 + t * 4; // Leg swings forward then returns
      kickLegX = side * (4 - t * 2);
      standLegY = 4;
      bodyLean = -1.5 + t * 1.5; // Return to upright
    }
    
    const result = {
      pelvis: { x: 0, y: 0 },
      spine: { x: 0, y: -2 + bodyLean * 0.3 },
      head: { x: 0, y: -5 + bodyLean },
      leftShoulder: { x: -3, y: -3 },
      rightShoulder: { x: 3, y: -3 },
      leftHip: { x: -2, y: 1 },
      rightHip: { x: 2, y: 1 },
      leftFoot: { x: side > 0 ? -2 : kickLegX, y: side > 0 ? standLegY : kickLegY },
      rightFoot: { x: side > 0 ? kickLegX : 2, y: side > 0 ? kickLegY : standLegY },
      leftHand: { x: -4 + (side > 0 ? 0 : -bodyLean), y: -1 },
      rightHand: { x: 4 + (side > 0 ? bodyLean : 0), y: -1 },
    };
    
    return result;
  }

  _getHeaderPose(phase) {
    // Jump up, head forward at contact
    const jumpHeight = Math.sin(phase * Math.PI) * 3;
    const headForward = phase > 0.4 && phase < 0.7 ? (phase - 0.4) * 10 : 0;
    
    return {
      pelvis: { x: 0, y: -jumpHeight },
      spine: { x: 0, y: -2 - jumpHeight },
      head: { x: 0, y: -5 - jumpHeight - headForward },
      leftShoulder: { x: -3, y: -3 - jumpHeight },
      rightShoulder: { x: 3, y: -3 - jumpHeight },
      leftHip: { x: -2, y: 1 - jumpHeight * 0.5 },
      rightHip: { x: 2, y: 1 - jumpHeight * 0.5 },
      leftFoot: { x: -2, y: 4 - jumpHeight * 0.3 },
      rightFoot: { x: 2, y: 4 - jumpHeight * 0.3 },
      leftHand: { x: -5, y: -2 - jumpHeight },
      rightHand: { x: 5, y: -2 - jumpHeight },
    };
  }

  _getSlidePose(phase, side) {
    // Slide tackle: body goes low, leg extends
    const slideExtend = Math.min(1, phase * 2) * 6;
    const bodyDrop = Math.min(1, phase * 3) * 3;
    
    return {
      pelvis: { x: 0, y: bodyDrop },
      spine: { x: 0, y: -2 + bodyDrop },
      head: { x: 0, y: -4 + bodyDrop },
      leftShoulder: { x: -3, y: -2 + bodyDrop },
      rightShoulder: { x: 3, y: -2 + bodyDrop },
      leftHip: { x: -2, y: 1 + bodyDrop * 0.5 },
      rightHip: { x: 2, y: 1 + bodyDrop * 0.5 },
      leftFoot: { x: side > 0 ? -2 : -2 - slideExtend, y: side > 0 ? 4 + bodyDrop : 2 },
      rightFoot: { x: side > 0 ? 2 + slideExtend : 2, y: side > 0 ? 2 : 4 + bodyDrop },
      leftHand: { x: -4, y: bodyDrop },
      rightHand: { x: 4, y: bodyDrop },
    };
  }

  _getVolleyPose(phase, side) {
    // Similar to kick but with raised body
    const pose = this._getKickPose(phase, side);
    // Raise everything slightly (ball is in air)
    pose.pelvis.y -= 1;
    pose.spine.y -= 1;
    pose.head.y -= 1;
    return pose;
  }

  get isActive() { return this.active; }
  get hasContacted() { return this.contacted; }
}
