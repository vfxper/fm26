/**
 * Skeleton - Simplified 2D skeleton for procedural player animation
 * 8-bone structure: pelvis, spine, head, 2 arms, 2 legs (upper+lower)
 * All positions are relative offsets from player center for 2D top-down view
 */

export class Skeleton {
  constructor() {
    // Bone positions (relative to player center, in pixels for rendering)
    this.pelvis = { x: 0, y: 0 };
    this.spine = { x: 0, y: -2 };
    this.head = { x: 0, y: -5 };
    this.leftShoulder = { x: -3, y: -3 };
    this.rightShoulder = { x: 3, y: -3 };
    this.leftHip = { x: -2, y: 1 };
    this.rightHip = { x: 2, y: 1 };
    this.leftFoot = { x: -2, y: 4 };
    this.rightFoot = { x: 2, y: 4 };
    this.leftHand = { x: -4, y: -1 };
    this.rightHand = { x: 4, y: -1 };
    
    // Animation blend weights
    this.blendWeights = {
      walk: 0,
      run: 0,
      sprint: 0,
      kick: 0,
      tackle: 0,
      celebrate: 0,
      idle: 1,
    };
  }

  /**
   * Reset to default pose
   */
  reset() {
    this.pelvis = { x: 0, y: 0 };
    this.spine = { x: 0, y: -2 };
    this.head = { x: 0, y: -5 };
    this.leftShoulder = { x: -3, y: -3 };
    this.rightShoulder = { x: 3, y: -3 };
    this.leftHip = { x: -2, y: 1 };
    this.rightHip = { x: 2, y: 1 };
    this.leftFoot = { x: -2, y: 4 };
    this.rightFoot = { x: 2, y: 4 };
    this.leftHand = { x: -4, y: -1 };
    this.rightHand = { x: 4, y: -1 };
  }

  /**
   * Blend between two poses
   */
  static blend(poseA, poseB, t) {
    const result = new Skeleton();
    const bones = ['pelvis', 'spine', 'head', 'leftShoulder', 'rightShoulder',
                   'leftHip', 'rightHip', 'leftFoot', 'rightFoot', 'leftHand', 'rightHand'];
    
    for (const bone of bones) {
      result[bone] = {
        x: poseA[bone].x + (poseB[bone].x - poseA[bone].x) * t,
        y: poseA[bone].y + (poseB[bone].y - poseA[bone].y) * t,
      };
    }
    return result;
  }
}
