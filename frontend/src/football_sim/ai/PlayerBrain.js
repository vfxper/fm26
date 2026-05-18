/**
 * PlayerBrain - Decision making for outfield players
 * 4-layer architecture: Strategic → Situational → Individual → Physical
 * Evaluates options every 0.2-0.3 seconds based on Decisions attribute
 */
import { Vector2 } from '../core/Vector2.js';
import { PITCH_WIDTH, PITCH_HEIGHT, ATTR_MAX, AI_DECISION_INTERVAL } from '../core/Constants.js';

export const BrainState = {
  // With ball
  DRIBBLING: 'dribbling',
  LOOKING_TO_PASS: 'looking_to_pass',
  SHOOTING: 'shooting',
  CROSSING: 'crossing',
  HOLDING: 'holding',
  
  // Without ball - attacking
  MAKING_RUN: 'making_run',
  OFFERING_SHORT: 'offering_short',
  HOLDING_POSITION: 'holding_position',
  OVERLAPPING: 'overlapping',
  
  // Without ball - defending
  PRESSING: 'pressing',
  MARKING: 'marking',
  COVERING: 'covering',
  TRACKING_RUN: 'tracking_run',
  BLOCKING_LANE: 'blocking_lane',
  
  // Transitions
  COUNTER_PRESSING: 'counter_pressing',
  TRANSITIONING: 'transitioning',
  
  // Special
  CELEBRATING: 'celebrating',
  ARGUING: 'arguing',
  RECOVERING: 'recovering',
};

export class PlayerBrain {
  constructor(player, rng) {
    this.player = player;
    this.rng = rng;
    
    this.state = BrainState.HOLDING_POSITION;
    this.decisionTimer = 0;
    this.currentTarget = null;
    this.passTarget = null;
    this.runTarget = null;
    
    // Decision interval based on Decisions attribute
    this.decisionInterval = AI_DECISION_INTERVAL + 
      (1 - player.attributes.decisions / ATTR_MAX) * 0.3; // 0.2-0.5s
  }

  /**
   * Main update - called every physics tick
   */
  update(dt, context) {
    this.decisionTimer -= dt;
    
    // CRITICAL: If player has ball, decide IMMEDIATELY (no waiting)
    if (this.player.hasBall && this.decisionTimer <= 0) {
      this.decisionTimer = this.decisionInterval * 0.5; // Faster decisions with ball
      this._makeDecision(context);
    } else if (!this.player.hasBall && this.decisionTimer <= 0) {
      this.decisionTimer = this.decisionInterval;
      this._makeDecision(context);
    }
    
    return this._executeCurrentState(context);
  }

  /**
   * Make a decision based on current context
   * @param {Object} context - { ball, teammates, opponents, matchState, teamTactics }
   */
  _makeDecision(context) {
    const { ball, matchState } = context;
    const hasBall = this.player.hasBall;
    const teamHasBall = ball.lastTouchedTeam === this.player.teamSide;
    
    if (hasBall) {
      this._decideWithBall(context);
    } else if (teamHasBall) {
      this._decideAttackingWithoutBall(context);
    } else {
      this._decideDefending(context);
    }
  }

  /**
   * Decisions when player has the ball
   */
  _decideWithBall(context) {
    const { ball, teammates, opponents, matchState } = context;
    const decisions = this.player.getEffectiveAttr('decisions');
    const vision = this.player.getEffectiveAttr('vision');
    
    // How long have we been holding the ball? Force pass after 2 seconds
    this._holdTimer = (this._holdTimer || 0) + this.decisionInterval;
    
    // Evaluate options
    const options = [];
    
    // 1. Shooting opportunity
    const shootScore = this._evaluateShot(context);
    if (shootScore > 0.4) options.push({ action: BrainState.SHOOTING, score: shootScore });
    
    // 2. Pass options - ALWAYS evaluate passes (primary action in football)
    const passOptions = this._evaluatePasses(context);
    for (const pass of passOptions) {
      options.push({ action: BrainState.LOOKING_TO_PASS, score: pass.score + 0.2, target: pass.target });
    }
    
    // 3. Dribble (only if space ahead and no good pass)
    const nearestDef = this._nearestOpponent(context);
    if (nearestDef > 5) {
      const dribbleScore = this._evaluateDribble(context);
      options.push({ action: BrainState.DRIBBLING, score: dribbleScore });
    }
    
    // 4. Cross (if in wide position)
    const crossScore = this._evaluateCross(context);
    if (crossScore > 0.3) options.push({ action: BrainState.CROSSING, score: crossScore });
    
    // 5. If held too long, force a pass
    if (this._holdTimer > 1.5 && passOptions.length > 0) {
      this.state = BrainState.LOOKING_TO_PASS;
      this.passTarget = passOptions[0].target;
      this._holdTimer = 0;
      return;
    }
    
    // Sort by score and pick best
    options.sort((a, b) => b.score - a.score);
    
    if (options.length > 0) {
      const flair = this.player.getEffectiveAttr('flair');
      let pickIdx = 0;
      if (flair > 15 && options.length > 1 && this.rng.chance(0.15)) {
        pickIdx = 1;
      }
      
      const chosen = options[Math.min(pickIdx, options.length - 1)];
      this.state = chosen.action;
      if (chosen.target) this.passTarget = chosen.target;
      if (chosen.action !== BrainState.DRIBBLING) this._holdTimer = 0;
    } else {
      // No good options - just pass to nearest teammate
      if (passOptions.length > 0) {
        this.state = BrainState.LOOKING_TO_PASS;
        this.passTarget = passOptions[0].target;
      } else {
        this.state = BrainState.DRIBBLING;
      }
    }
  }

  /**
   * Decisions when team has ball but player doesn't
   */
  _decideAttackingWithoutBall(context) {
    const { ball, teammates, opponents } = context;
    const offTheBall = this.player.getEffectiveAttr('positioning');
    const anticipation = this.player.getEffectiveAttr('anticipation');
    const workRate = this.player.getEffectiveAttr('workRate');
    const teamwork = this.player.getEffectiveAttr('teamwork');
    
    // Distance to ball
    const distToBall = this.player.position.distance(ball.position);
    
    // Am I in a good position to receive?
    const isOpen = this._isPlayerOpen(context);
    
    if (this.player.isAttacker()) {
      // Attackers: make runs, find space
      if (this._canMakeRunBehind(context) && anticipation > 12) {
        this.state = BrainState.MAKING_RUN;
        this.runTarget = this._calculateRunTarget(context);
      } else if (distToBall < 20 && isOpen) {
        this.state = BrainState.OFFERING_SHORT;
        this.currentTarget = this._findReceivingPosition(context);
      } else {
        this.state = BrainState.HOLDING_POSITION;
        this.currentTarget = this._getAttackingPosition(context);
      }
    } else if (this.player.isMidfielder()) {
      // Midfielders: create triangles, offer passing options
      if (distToBall < 25 && isOpen) {
        this.state = BrainState.OFFERING_SHORT;
        this.currentTarget = this._findReceivingPosition(context);
      } else if (this.player.positionRole === 'AM' && this._canMakeRunBehind(context)) {
        this.state = BrainState.MAKING_RUN;
        this.runTarget = this._calculateRunTarget(context);
      } else {
        this.state = BrainState.HOLDING_POSITION;
        this.currentTarget = this._getAttackingPosition(context);
      }
    } else if (this.player.isDefender()) {
      // Defenders: hold shape, overlap if fullback
      if ((this.player.positionRole === 'RB' || this.player.positionRole === 'LB') && 
          workRate > 14 && this.rng.chance(0.3)) {
        this.state = BrainState.OVERLAPPING;
        this.runTarget = this._calculateOverlapTarget(context);
      } else {
        this.state = BrainState.HOLDING_POSITION;
        this.currentTarget = this._getAttackingPosition(context);
      }
    }
  }

  /**
   * Decisions when defending
   */
  _decideDefending(context) {
    const { ball, opponents, teamTactics } = context;
    const marking = this.player.getEffectiveAttr('marking');
    const positioning = this.player.getEffectiveAttr('positioning');
    const workRate = this.player.getEffectiveAttr('workRate');
    const anticipation = this.player.getEffectiveAttr('anticipation');
    
    const distToBall = this.player.position.distance(ball.position);
    const ballHolder = opponents.find(p => p.hasBall);
    
    // Pressing trigger
    const pressingIntensity = teamTactics?.pressing || 0.5;
    const shouldPress = distToBall < 15 * pressingIntensity && workRate > 10;
    
    if (shouldPress && ballHolder) {
      this.state = BrainState.PRESSING;
      this.currentTarget = this._calculatePressingTarget(ballHolder, context);
    } else if (this.player.isDefender()) {
      // Track dangerous runners
      const dangerousRunner = this._findDangerousRunner(context);
      if (dangerousRunner && anticipation > 12) {
        this.state = BrainState.TRACKING_RUN;
        this.currentTarget = dangerousRunner.position.clone();
      } else {
        this.state = BrainState.COVERING;
        this.currentTarget = this._getDefensivePosition(context);
      }
    } else if (this.player.isMidfielder()) {
      // Block passing lanes
      if (ballHolder && distToBall < 25) {
        this.state = BrainState.BLOCKING_LANE;
        this.currentTarget = this._calculateLaneBlockPosition(ballHolder, context);
      } else {
        this.state = BrainState.COVERING;
        this.currentTarget = this._getDefensivePosition(context);
      }
    } else {
      // Attackers: light press or hold high
      if (shouldPress && workRate > 14) {
        this.state = BrainState.PRESSING;
        this.currentTarget = ball.position.clone();
      } else {
        this.state = BrainState.HOLDING_POSITION;
        this.currentTarget = this._getDefensivePosition(context);
      }
    }
  }

  // === Evaluation functions ===

  _evaluateShot(context) {
    const { opponents } = context;
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    const goalX = attackDir > 0 ? PITCH_WIDTH : 0;
    const goalY = PITCH_HEIGHT / 2;
    
    const distToGoal = Math.abs(this.player.position.x - goalX);
    if (distToGoal > 30) return 0; // Too far
    
    const shooting = this.player.getEffectiveAttr('shooting');
    const composure = this.player.getEffectiveAttr('composure');
    
    // Angle to goal
    const angleToGoal = Math.abs(Math.atan2(goalY - this.player.position.y, goalX - this.player.position.x));
    const angleFactor = 1 - Math.abs(angleToGoal) / (Math.PI / 2);
    
    // Distance factor (closer = better)
    const distFactor = 1 - distToGoal / 30;
    
    // Pressure factor
    const nearestDef = this._nearestOpponent(context);
    const pressureFactor = nearestDef > 3 ? 1 : nearestDef / 3;
    
    return (shooting / ATTR_MAX) * distFactor * angleFactor * pressureFactor * 0.8;
  }

  _evaluatePasses(context) {
    const { teammates, opponents } = context;
    const vision = this.player.getEffectiveAttr('vision');
    const passing = this.player.getEffectiveAttr('passing');
    
    // Number of options visible depends on Vision
    const maxOptions = Math.floor(3 + (vision / ATTR_MAX) * 7); // 3-10 options
    
    const options = [];
    const activeTeammates = teammates.filter(t => t.isActive && t !== this.player && !t.isGoalkeeper());
    
    // Sort by distance for priority
    const sorted = activeTeammates
      .map(t => ({ player: t, dist: this.player.position.distance(t.position) }))
      .filter(t => t.dist < 50 && t.dist > 2) // Not too far, not too close
      .sort((a, b) => a.dist - b.dist)
      .slice(0, maxOptions);
    
    for (const { player: teammate, dist } of sorted) {
      // Is passing lane clear?
      const laneClear = this._isPassingLaneClear(this.player.position, teammate.position, opponents);
      
      // Forward progress bonus
      const attackDir = this.player.teamSide === 'home' ? 1 : -1;
      const progressX = (teammate.position.x - this.player.position.x) * attackDir;
      const progressBonus = Math.max(0, progressX / 40) * 0.4;
      
      // Safety (shorter = safer, but not too short)
      const idealDist = 15; // 15m is ideal pass distance
      const distScore = 1 - Math.abs(dist - idealDist) / 40;
      
      // Is teammate open? (no opponent within 3m)
      const teammateOpen = opponents.every(o => !o.isActive || o.position.distance(teammate.position) > 3);
      const openBonus = teammateOpen ? 0.3 : 0;
      
      // Lane clear is critical
      const laneBonus = laneClear ? 0.3 : -0.5;
      
      const score = (passing / ATTR_MAX) * 0.2 + distScore * 0.2 + progressBonus + openBonus + laneBonus;
      
      if (score > 0) {
        options.push({ target: teammate, score: Math.max(0.1, score) });
      }
    }
    
    // If no good options found, add a safe back-pass
    if (options.length === 0 && activeTeammates.length > 0) {
      const safest = activeTeammates
        .filter(t => {
          const attackDir = this.player.teamSide === 'home' ? 1 : -1;
          return (t.position.x - this.player.position.x) * attackDir < 0; // Behind us
        })
        .sort((a, b) => this.player.position.distance(a.position) - this.player.position.distance(b.position));
      
      if (safest.length > 0) {
        options.push({ target: safest[0], score: 0.3 });
      } else {
        // Just pass to nearest
        const nearest = activeTeammates.sort((a, b) => 
          this.player.position.distance(a.position) - this.player.position.distance(b.position)
        )[0];
        if (nearest) options.push({ target: nearest, score: 0.2 });
      }
    }
    
    return options.sort((a, b) => b.score - a.score).slice(0, 3);
  }

  _evaluateDribble(context) {
    const dribbling = this.player.getEffectiveAttr('dribbling');
    const pace = this.player.getEffectiveAttr('pace');
    const flair = this.player.getEffectiveAttr('flair');
    
    const nearestDef = this._nearestOpponent(context);
    const spaceFactor = Math.min(1, nearestDef / 5); // More space = better
    
    return (dribbling / ATTR_MAX) * spaceFactor * 0.5 + (flair / ATTR_MAX) * 0.1;
  }

  _evaluateCross(context) {
    const { teammates } = context;
    const crossing = this.player.getEffectiveAttr('crossing');
    
    // Only cross from wide positions
    const y = this.player.position.y;
    const isWide = y < 15 || y > PITCH_HEIGHT - 15;
    if (!isWide) return 0;
    
    // Check if attackers are in the box
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    const boxX = attackDir > 0 ? PITCH_WIDTH - 16.5 : 16.5;
    const inBox = teammates.filter(t => {
      const inBoxX = attackDir > 0 ? t.position.x > boxX : t.position.x < boxX;
      return inBoxX && t.isActive;
    });
    
    if (inBox.length === 0) return 0;
    
    return (crossing / ATTR_MAX) * 0.6 * (inBox.length / 3);
  }

  // === Helper functions ===

  _nearestOpponent(context) {
    const { opponents } = context;
    let minDist = Infinity;
    for (const opp of opponents) {
      if (!opp.isActive) continue;
      const d = this.player.position.distance(opp.position);
      if (d < minDist) minDist = d;
    }
    return minDist;
  }

  _isPassingLaneClear(from, to, opponents) {
    const dir = to.sub(from).normalize();
    const dist = from.distance(to);
    
    for (const opp of opponents) {
      if (!opp.isActive) continue;
      // Project opponent onto passing line
      const toOpp = opp.position.sub(from);
      const proj = toOpp.dot(dir);
      if (proj < 0 || proj > dist) continue;
      
      const closest = from.add(dir.mul(proj));
      const perpDist = opp.position.distance(closest);
      if (perpDist < 2.0) return false; // Opponent within 2m of passing lane
    }
    return true;
  }

  _isPlayerOpen(context) {
    const nearest = this._nearestOpponent(context);
    return nearest > 3;
  }

  _canMakeRunBehind(context) {
    const { opponents } = context;
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    const goalX = attackDir > 0 ? PITCH_WIDTH : 0;
    const distToGoal = Math.abs(this.player.position.x - goalX);
    
    return distToGoal < 40 && distToGoal > 10;
  }

  _calculateRunTarget(context) {
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    const goalX = attackDir > 0 ? PITCH_WIDTH : 0;
    
    // Run behind the defensive line
    return new Vector2(
      this.player.position.x + attackDir * this.rng.range(10, 20),
      this.player.position.y + this.rng.range(-8, 8)
    ).clampLengthMut(PITCH_WIDTH); // Keep on pitch
  }

  _calculateOverlapTarget(context) {
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    const side = this.player.positionRole === 'RB' ? 1 : -1;
    
    return new Vector2(
      this.player.position.x + attackDir * 20,
      side > 0 ? PITCH_HEIGHT - 5 : 5
    );
  }

  _findReceivingPosition(context) {
    // Move to create passing angle
    const { ball } = context;
    const toBall = ball.position.sub(this.player.position).normalize();
    const perp = toBall.perpendicular();
    const offset = perp.mul(this.rng.range(-5, 5));
    
    return this.player.position.add(toBall.mul(-3)).add(offset);
  }

  _getAttackingPosition(context) {
    const { ball } = context;
    const homePos = this.player.homePosition;
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    
    // Shift formation toward ball (compact play)
    const ballInfluenceX = (ball.position.x - homePos.x) * 0.25;
    const ballInfluenceY = (ball.position.y - homePos.y) * 0.15;
    
    // Push forward when team has ball
    const forwardPush = attackDir * 8;
    
    return new Vector2(
      Math.max(2, Math.min(PITCH_WIDTH - 2, homePos.x + ballInfluenceX + forwardPush)),
      Math.max(3, Math.min(PITCH_HEIGHT - 3, homePos.y + ballInfluenceY))
    );
  }

  _getDefensivePosition(context) {
    const { ball } = context;
    const homePos = this.player.homePosition;
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    
    // Drop back toward own goal
    const dropBack = -attackDir * 10;
    
    // Shift toward ball laterally (compact)
    const ballInfluenceY = (ball.position.y - homePos.y) * 0.25;
    const ballInfluenceX = (ball.position.x - homePos.x) * 0.2;
    
    return new Vector2(
      Math.max(2, Math.min(PITCH_WIDTH - 2, homePos.x + ballInfluenceX + dropBack)),
      Math.max(3, Math.min(PITCH_HEIGHT - 3, homePos.y + ballInfluenceY))
    );
  }

  _calculatePressingTarget(ballHolder, context) {
    // Press by cutting off forward passing lane
    const attackDir = ballHolder.teamSide === 'home' ? 1 : -1;
    const offset = Vector2.fromAngle(this.player.position.angleTo(ballHolder.position));
    
    // Approach from angle that blocks forward pass
    return ballHolder.position.add(new Vector2(-attackDir * 2, 0));
  }

  _calculateLaneBlockPosition(ballHolder, context) {
    // Stand between ball and nearest forward teammate
    const { opponents } = context;
    const attackDir = ballHolder.teamSide === 'home' ? 1 : -1;
    
    // Find most dangerous forward player
    const forwardPlayers = opponents.filter(p => {
      const ahead = attackDir > 0 ? p.position.x > ballHolder.position.x : p.position.x < ballHolder.position.x;
      return ahead && p.isActive && !p.isGoalkeeper();
    });
    
    if (forwardPlayers.length === 0) return this.player.homePosition.clone();
    
    const target = forwardPlayers[0];
    // Position between ball and target
    return ballHolder.position.lerp(target.position, 0.4);
  }

  _findDangerousRunner(context) {
    const { opponents } = context;
    const attackDir = this.player.teamSide === 'home' ? -1 : 1; // Opponent's attack direction
    
    for (const opp of opponents) {
      if (!opp.isActive || opp.isGoalkeeper()) continue;
      if (opp.state === 'sprinting' || opp.aiState?.role === 'making_run') {
        const dist = this.player.position.distance(opp.position);
        if (dist < 15) return opp;
      }
    }
    return null;
  }

  /**
   * Execute current state - returns movement/action command
   */
  _executeCurrentState(context) {
    switch (this.state) {
      case BrainState.SHOOTING:
        return { type: 'shoot', target: this._getShootTarget(context) };
      case BrainState.LOOKING_TO_PASS:
        return { type: 'pass', target: this.passTarget };
      case BrainState.DRIBBLING:
        return { type: 'dribble', direction: this._getDribbleDirection(context) };
      case BrainState.CROSSING:
        return { type: 'cross', target: this._getCrossTarget(context) };
      case BrainState.MAKING_RUN:
        return { type: 'move', target: this.runTarget, mode: 'sprint' };
      case BrainState.OFFERING_SHORT:
        return { type: 'move', target: this.currentTarget, mode: 'jog' };
      case BrainState.PRESSING:
        return { type: 'move', target: this.currentTarget, mode: 'sprint' };
      case BrainState.TRACKING_RUN:
        return { type: 'move', target: this.currentTarget, mode: 'sprint' };
      case BrainState.BLOCKING_LANE:
        return { type: 'move', target: this.currentTarget, mode: 'jog' };
      case BrainState.OVERLAPPING:
        return { type: 'move', target: this.runTarget, mode: 'sprint' };
      default:
        return { type: 'move', target: this.currentTarget || this.player.homePosition, mode: 'jog' };
    }
  }

  _getShootTarget(context) {
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    const goalX = attackDir > 0 ? PITCH_WIDTH : 0;
    const goalY = PITCH_HEIGHT / 2;
    // Aim for corners
    const side = this.rng.chance(0.5) ? -1 : 1;
    return new Vector2(goalX, goalY + side * this.rng.range(1, 3));
  }

  _getDribbleDirection(context) {
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    // Dribble toward opponent's goal with slight variation
    const goalX = attackDir > 0 ? PITCH_WIDTH : 0;
    const toGoal = new Vector2(goalX - this.player.position.x, PITCH_HEIGHT/2 - this.player.position.y).normalize();
    return toGoal;
  }

  _getCrossTarget(context) {
    const attackDir = this.player.teamSide === 'home' ? 1 : -1;
    return new Vector2(
      attackDir > 0 ? PITCH_WIDTH - 10 : 10,
      PITCH_HEIGHT / 2 + this.rng.range(-6, 6)
    );
  }
}
