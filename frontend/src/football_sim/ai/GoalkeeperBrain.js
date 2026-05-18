/**
 * GoalkeeperBrain - Specialized AI for goalkeepers
 * Positioning, diving, rushing out, distribution, command of area
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT, GOAL_Y_MIN, GOAL_Y_MAX, GOAL_WIDTH, ATTR_MAX } from '../core/Constants.js';

export const GKState = {
  POSITIONING: 'positioning',
  READY: 'ready',           // On line, weight on toes
  DIVING: 'diving',
  RUSHING_OUT: 'rushing_out',
  CATCHING: 'catching',
  PUNCHING: 'punching',
  DISTRIBUTING: 'distributing',
  RECOVERING: 'recovering', // Getting up after dive
  SWEEPING: 'sweeping',     // Coming out to clear through ball
};

export class GoalkeeperBrain {
  constructor(player, rng) {
    this.player = player;
    this.rng = rng;
    
    this.state = GKState.POSITIONING;
    this.diveTarget = null;
    this.diveTimer = 0;
    this.recoveryTimer = 0;
    
    // Goal position (which end)
    this.goalX = 0; // Set during init
    this.goalCenterY = PITCH_HEIGHT / 2;
    
    // Reach zone (rectangle the GK can cover)
    this.reachWidth = 2.0; // meters horizontal
    this.reachHeight = 2.2; // meters vertical (jump height)
    this.diveReach = 3.0; // meters when diving
  }

  /**
   * Initialize goalkeeper for a specific goal
   * @param {string} side - 'home' or 'away'
   */
  initialize(side) {
    this.goalX = side === 'home' ? 0 : PITCH_WIDTH;
    this.player.position.x = side === 'home' ? 2 : PITCH_WIDTH - 2;
    this.player.position.y = PITCH_HEIGHT / 2;
  }

  /**
   * Main update
   */
  update(dt, context) {
    const { ball, opponents, matchState } = context;
    
    // Handle recovery from dive
    if (this.state === GKState.RECOVERING) {
      this.recoveryTimer -= dt;
      if (this.recoveryTimer <= 0) {
        this.state = GKState.POSITIONING;
      }
      return { type: 'stay' };
    }
    
    // Handle active dive
    if (this.state === GKState.DIVING) {
      this.diveTimer -= dt;
      if (this.diveTimer <= 0) {
        this.state = GKState.RECOVERING;
        this.recoveryTimer = 0.8;
      }
      return { type: 'dive', target: this.diveTarget };
    }
    
    // Check if shot is coming
    if (this._isShotComing(ball, context)) {
      return this._handleShot(ball, context);
    }
    
    // Check if should rush out (1v1 or through ball)
    if (this._shouldRushOut(ball, opponents, context)) {
      this.state = GKState.RUSHING_OUT;
      return { type: 'move', target: ball.position.clone(), mode: 'sprint' };
    }
    
    // Check if should come for cross
    if (this._shouldComeForCross(ball, context)) {
      this.state = GKState.RUSHING_OUT;
      return { type: 'move', target: this._getCrossInterceptPoint(ball), mode: 'sprint' };
    }
    
    // Default: positioning
    this.state = GKState.POSITIONING;
    const optimalPos = this._calculateOptimalPosition(ball);
    return { type: 'move', target: optimalPos, mode: 'jog' };
  }

  /**
   * Calculate optimal position (bisector of angle between ball and posts)
   */
  _calculateOptimalPosition(ball) {
    const goalTop = new Vector2(this.goalX, GOAL_Y_MIN);
    const goalBottom = new Vector2(this.goalX, GOAL_Y_MAX);
    
    // Bisector of angle ball-to-posts
    const toBallFromTop = ball.position.sub(goalTop).normalize();
    const toBallFromBottom = ball.position.sub(goalBottom).normalize();
    
    // Simple: position on line between ball and goal center, offset from goal
    const goalCenter = new Vector2(this.goalX, this.goalCenterY);
    const ballToGoal = goalCenter.sub(ball.position).normalize();
    
    // Distance from goal line depends on ball distance
    const ballDist = ball.position.distance(goalCenter);
    const standDist = Math.min(6, Math.max(1.5, ballDist * 0.08));
    
    const sign = this.goalX === 0 ? 1 : -1;
    const posX = this.goalX + sign * standDist;
    
    // Y position: between ball Y and goal center, weighted by distance
    const yWeight = Math.min(0.8, ballDist / 50);
    const posY = this.goalCenterY + (ball.position.y - this.goalCenterY) * (1 - yWeight) * 0.6;
    
    // Clamp to reasonable range
    const clampedY = Math.max(GOAL_Y_MIN - 2, Math.min(GOAL_Y_MAX + 2, posY));
    
    return new Vector2(posX, clampedY);
  }

  /**
   * Check if a shot is heading toward goal
   */
  _isShotComing(ball, context) {
    if (ball.isHeld) return false;
    
    const speed = ball.velocity.length();
    if (speed < 8) return false; // Too slow to be a shot
    
    // Check if ball is heading toward our goal
    const sign = this.goalX === 0 ? -1 : 1;
    const headingToGoal = ball.velocity.x * sign > 0;
    if (!headingToGoal) return false;
    
    // Predict where ball will cross goal line
    const timeToGoalLine = Math.abs(this.goalX - ball.position.x) / Math.abs(ball.velocity.x);
    if (timeToGoalLine > 2) return false; // Too far away
    
    const predictedY = ball.position.y + ball.velocity.y * timeToGoalLine;
    
    // Is it heading between the posts (with some margin)?
    return predictedY > GOAL_Y_MIN - 2 && predictedY < GOAL_Y_MAX + 2;
  }

  /**
   * Handle incoming shot - decide to dive or stay
   */
  _handleShot(ball, context) {
    const reflexes = this.player.getEffectiveAttr('reflexes');
    const positioning = this.player.getEffectiveAttr('positioning');
    const handling = this.player.getEffectiveAttr('handling');
    
    // Predict ball position at goal line
    const timeToGoal = Math.abs(this.goalX - ball.position.x) / Math.max(1, Math.abs(ball.velocity.x));
    const predictedY = ball.position.y + ball.velocity.y * timeToGoal;
    const predictedH = Math.max(0, ball.height + ball.verticalVelocity * timeToGoal - 0.5 * 9.81 * timeToGoal * timeToGoal);
    
    // Can GK reach it from current position?
    const distY = Math.abs(predictedY - this.player.position.y);
    const canReachStanding = distY < this.reachWidth;
    const canReachDiving = distY < this.diveReach;
    
    // Reaction time based on reflexes
    const reactionTime = 0.1 + (1 - reflexes / ATTR_MAX) * 0.3; // 0.1-0.4s
    
    if (timeToGoal < reactionTime) {
      // Too late to react properly
      if (canReachStanding && this.rng.chance(reflexes / ATTR_MAX * 0.5)) {
        // Reflex save
        this.state = GKState.DIVING;
        this.diveTarget = new Vector2(this.goalX, predictedY);
        this.diveTimer = 0.5;
        return { type: 'dive', target: this.diveTarget, save: true };
      }
      return { type: 'stay' }; // Can't reach
    }
    
    if (canReachStanding) {
      // Just position correctly
      return { type: 'move', target: new Vector2(this.player.position.x, predictedY), mode: 'sprint' };
    }
    
    if (canReachDiving) {
      // Need to dive
      const saveChance = (reflexes + handling) / (ATTR_MAX * 2) * 0.8;
      this.state = GKState.DIVING;
      this.diveTarget = new Vector2(this.goalX, predictedY);
      this.diveTimer = 0.6;
      return { type: 'dive', target: this.diveTarget, save: this.rng.chance(saveChance) };
    }
    
    // Out of reach
    return { type: 'stay' };
  }

  /**
   * Should GK rush out? (1v1 or through ball)
   */
  _shouldRushOut(ball, opponents, context) {
    const rushingOut = this.player.getEffectiveAttr('oneOnOnes');
    const bravery = this.player.attributes.composure; // Using composure as bravery proxy
    
    // Check if attacker is through on goal
    const sign = this.goalX === 0 ? 1 : -1;
    const ballInDangerZone = sign > 0 ? ball.position.x < 25 : ball.position.x > PITCH_WIDTH - 25;
    
    if (!ballInDangerZone) return false;
    
    // Is there an attacker with the ball and no defenders between them and goal?
    const ballHolder = opponents.find(p => p.hasBall);
    if (!ballHolder) return false;
    
    const distToGoal = Math.abs(ballHolder.position.x - this.goalX);
    if (distToGoal > 20) return false;
    
    // Rush out decision based on attributes
    return distToGoal < 15 && this.rng.chance((rushingOut + bravery) / (ATTR_MAX * 2) * 0.6);
  }

  /**
   * Should GK come for a cross?
   */
  _shouldComeForCross(ball, context) {
    if (ball.height < 2) return false; // Ball not in air
    
    const commandOfArea = this.player.getEffectiveAttr('commandOfArea');
    const distToBall = this.player.position.distance(ball.position);
    
    // Only come out if ball is in our box area and high
    const inBoxArea = Math.abs(ball.position.x - this.goalX) < 16;
    
    return inBoxArea && distToBall < 10 && ball.height > 2 && 
           this.rng.chance(commandOfArea / ATTR_MAX * 0.5);
  }

  _getCrossInterceptPoint(ball) {
    // Predict where ball will be in ~0.5s
    const t = 0.5;
    return new Vector2(
      ball.position.x + ball.velocity.x * t,
      ball.position.y + ball.velocity.y * t
    );
  }
}
