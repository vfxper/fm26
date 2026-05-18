/**
 * ProceduralWalk - Generates walking/running animation procedurally
 * Step frequency and length depend on speed, fatigue affects posture
 */

export class ProceduralWalk {
  constructor() {
    this.phase = 0; // 0-1 cycle
    this.stepLength = 0;
    this.stepFrequency = 0;
  }

  /**
   * Update walk cycle
   * @param {number} speed - Current player speed (m/s)
   * @param {number} dt - Delta time
   * @param {number} fatigue - 0-1 (1 = fresh)
   * @param {number} height - Player height factor (0.8-1.2)
   * @returns {Object} Bone offsets for this frame
   */
  update(speed, dt, fatigue = 1, height = 1) {
    if (speed < 0.1) {
      // Standing still
      this.phase = 0;
      return this._getIdlePose(fatigue);
    }

    // Step frequency increases with speed
    // Walk: ~2 steps/sec, Jog: ~3, Sprint: ~4.5
    if (speed < 2) {
      this.stepFrequency = 1.5 + speed * 0.25;
      this.stepLength = 0.6 * height;
    } else if (speed < 5) {
      this.stepFrequency = 2.0 + (speed - 2) * 0.33;
      this.stepLength = 0.8 * height;
    } else {
      this.stepFrequency = 3.0 + (speed - 5) * 0.3;
      this.stepLength = 1.0 * height;
    }

    // Advance phase
    this.phase += this.stepFrequency * dt;
    if (this.phase >= 1) this.phase -= 1;

    // Generate pose
    return this._generatePose(speed, fatigue, height);
  }

  /**
   * Generate bone offsets based on current phase
   */
  _generatePose(speed, fatigue, height) {
    const p = this.phase * Math.PI * 2; // Convert to radians for sin/cos
    const amplitude = Math.min(1, speed / 8); // 0-1 based on speed
    
    // Fatigue effects: slouched posture, shorter stride
    const fatigueSlump = (1 - fatigue) * 2; // 0-2 pixels slump
    const strideFactor = 0.7 + fatigue * 0.3; // 70-100% stride

    // Leg movement (alternating)
    const leftLegPhase = Math.sin(p);
    const rightLegPhase = Math.sin(p + Math.PI);
    
    // Arm swing (opposite to legs)
    const leftArmSwing = Math.sin(p + Math.PI) * amplitude * 2;
    const rightArmSwing = Math.sin(p) * amplitude * 2;

    // Body bob (vertical oscillation)
    const bodyBob = Math.abs(Math.sin(p)) * amplitude * 0.5;

    // Lean forward when sprinting
    const leanForward = speed > 6 ? (speed - 6) * 0.3 : 0;

    return {
      pelvis: { x: 0, y: bodyBob },
      spine: { x: 0, y: -2 + bodyBob * 0.5 - leanForward * 0.5 + fatigueSlump * 0.3 },
      head: { x: 0, y: -5 + bodyBob * 0.3 - leanForward + fatigueSlump },
      leftShoulder: { x: -3, y: -3 + bodyBob * 0.3 },
      rightShoulder: { x: 3, y: -3 + bodyBob * 0.3 },
      leftHip: { x: -2, y: 1 },
      rightHip: { x: 2, y: 1 },
      leftFoot: { 
        x: -2 + leftLegPhase * amplitude * strideFactor * 1.5, 
        y: 4 + leftLegPhase * amplitude * strideFactor * 3 
      },
      rightFoot: { 
        x: 2 + rightLegPhase * amplitude * strideFactor * 1.5, 
        y: 4 + rightLegPhase * amplitude * strideFactor * 3 
      },
      leftHand: { x: -4 + leftArmSwing, y: -1 + Math.abs(leftArmSwing) * 0.3 },
      rightHand: { x: 4 + rightArmSwing, y: -1 + Math.abs(rightArmSwing) * 0.3 },
      // Metadata
      isContact: leftLegPhase > 0.8 || rightLegPhase > 0.8, // Foot on ground
      stepPhase: this.phase,
    };
  }

  _getIdlePose(fatigue) {
    const slump = (1 - fatigue) * 1.5;
    return {
      pelvis: { x: 0, y: 0 },
      spine: { x: 0, y: -2 + slump * 0.2 },
      head: { x: 0, y: -5 + slump },
      leftShoulder: { x: -3, y: -3 },
      rightShoulder: { x: 3, y: -3 },
      leftHip: { x: -2, y: 1 },
      rightHip: { x: 2, y: 1 },
      leftFoot: { x: -2, y: 4 },
      rightFoot: { x: 2, y: 4 },
      leftHand: { x: -4, y: -1 + slump },
      rightHand: { x: 4, y: -1 + slump },
      isContact: true,
      stepPhase: 0,
    };
  }
}
