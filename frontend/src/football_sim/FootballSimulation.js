/**
 * FootballSimulation - Main orchestrator class
 * Creates and connects all subsystems, manages the game loop
 */
import { Engine, SeededRandom } from './core/Engine.js';
import { Vector2 } from './core/Vector2.js';
import { EventBus, EVENTS } from './core/EventBus.js';
import { MatchState, MatchPhase, BallOwnership, PlayState } from './core/MatchState.js';
import { Replay } from './core/Replay.js';
import { PITCH_WIDTH, PITCH_HEIGHT, MATCH_MINUTE_DURATION, PHYSICS_TIMESTEP, PLAYER_CONTROL_RADIUS } from './core/Constants.js';

import { Ball } from './entities/Ball.js';
import { Player, PlayerState } from './entities/Player.js';

import { BallPhysics } from './physics/BallPhysics.js';
import { PlayerPhysics } from './physics/PlayerPhysics.js';
import { CollisionSystem } from './physics/CollisionSystem.js';
import { BallContact } from './physics/BallContact.js';
import { PitchSurface } from './physics/PitchSurface.js';

import { PlayerBrain } from './ai/PlayerBrain.js';
import { GoalkeeperBrain } from './ai/GoalkeeperBrain.js';

import { FatigueSystem } from './systems/FatigueSystem.js';
import { WeatherSystem } from './systems/WeatherSystem.js';
import { RefereeSystem } from './systems/RefereeSystem.js';
import { OffsideSystem } from './systems/OffsideSystem.js';
import { SetPieceSystem } from './systems/SetPieceSystem.js';
import { InjurySystem } from './systems/InjurySystem.js';

import { Camera } from './render/Camera.js';
import { PitchRenderer } from './render/PitchRenderer.js';
import { PlayerRenderer } from './render/PlayerRenderer.js';
import { BallRenderer } from './render/BallRenderer.js';
import { UIOverlay } from './render/UIOverlay.js';
import { Effects } from './render/Effects.js';

import { ProceduralWalk } from './animation/ProceduralWalk.js';
import { KickAnimation } from './animation/KickAnimation.js';

import { getFormation, mirrorFormation } from './data/Formations.js';
import { getTeamTemplate } from './data/TeamTemplates.js';

export class FootballSimulation {
  /**
   * @param {HTMLCanvasElement} canvas
   * @param {Object} options
   * @param {Object} options.homeTeam - Team data or template key
   * @param {Object} options.awayTeam - Team data or template key
   * @param {Object} options.weather - Weather config
   * @param {number} options.seed - Random seed
   * @param {number} options.speed - Initial speed multiplier
   */
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.options = options;

    // Core
    const seed = options.seed || Math.floor(Math.random() * 999999);
    this.rng = new SeededRandom(seed);
    this.eventBus = new EventBus();
    this.matchState = new MatchState();
    this.replay = new Replay();

    // Engine
    this.engine = new Engine({ seed, speed: options.speed || 1 });

    // Entities
    this.ball = new Ball();
    this.homeTeam = null;
    this.awayTeam = null;
    this.allPlayers = [];

    // Physics
    this.ballPhysics = new BallPhysics(this.eventBus);
    this.playerPhysics = new PlayerPhysics();
    this.collisionSystem = new CollisionSystem(this.eventBus);
    this.ballContact = new BallContact(this.eventBus);
    this.pitchSurface = new PitchSurface();

    // Systems
    this.fatigueSystem = new FatigueSystem();
    this.weatherSystem = new WeatherSystem(this.rng);
    this.refereeSystem = new RefereeSystem(this.eventBus, this.rng);
    this.offsideSystem = new OffsideSystem(this.rng);
    this.setPieceSystem = new SetPieceSystem(this.eventBus, this.rng);
    this.injurySystem = new InjurySystem(this.eventBus, this.rng);

    // Rendering
    this.camera = new Camera(canvas.width, canvas.height);
    this.pitchRenderer = new PitchRenderer();
    this.playerRenderer = new PlayerRenderer();
    this.ballRenderer = new BallRenderer();
    this.uiOverlay = new UIOverlay(canvas.width, canvas.height);
    this.effects = new Effects();

    // Animation
    this.walkAnimations = new Map(); // playerId -> ProceduralWalk
    this.kickAnimations = new Map(); // playerId -> KickAnimation

    // AI
    this.playerBrains = new Map(); // playerId -> PlayerBrain/GoalkeeperBrain

    // Initialize
    this._initTeams(options);
    this._initWeather(options.weather);
    this._setupEngine();
    this._setupResize();
  }

  /**
   * Start the simulation
   */
  start() {
    this.matchState.phase = MatchPhase.FIRST_HALF;
    this.matchState.playState = PlayState.KICK_OFF;
    this.matchState.ballOwnership = BallOwnership.DEAD;
    
    // Position for kick-off
    this.ball.resetToCenter();
    this._positionForKickOff('home');
    
    this.replay.startRecording({
      homeTeam: this.homeTeam.name,
      awayTeam: this.awayTeam.name,
      seed: this.rng.seed,
    });

    this.engine.start();
    
    // Auto-start kick-off after brief delay
    setTimeout(() => {
      this.matchState.playState = PlayState.IN_PLAY;
      this.matchState.ballOwnership = BallOwnership.HELD;
      // Give ball to nearest home player
      const kickOffPlayer = this._findNearestPlayer(this.ball.position, 'home');
      if (kickOffPlayer) {
        kickOffPlayer.hasBall = true;
        this.ball.holder = kickOffPlayer;
        this.matchState.ballOwner = kickOffPlayer;
      }
    }, 1500);
  }

  /**
   * Stop the simulation
   */
  stop() {
    this.engine.stop();
    this.replay.stopRecording();
  }

  /**
   * Pause/resume
   */
  pause() { this.engine.pause(); }
  resume() { this.engine.resume(); }
  get isPaused() { return this.engine.isPaused; }
  get isRunning() { return this.engine.isRunning; }

  /**
   * Set simulation speed
   */
  setSpeed(multiplier) {
    this.engine.setSpeed(multiplier);
  }

  /**
   * Set camera mode
   */
  setCameraMode(mode) {
    this.camera.setMode(mode);
  }

  // === INITIALIZATION ===

  _initTeams(options) {
    // Home team
    const homeData = typeof options.homeTeam === 'string' 
      ? getTeamTemplate(options.homeTeam) 
      : options.homeTeam || getTeamTemplate('real_madrid');
    
    const awayData = typeof options.awayTeam === 'string'
      ? getTeamTemplate(options.awayTeam)
      : options.awayTeam || getTeamTemplate('manchester_city');

    const homeFormation = getFormation(homeData.formation || '4-3-3');
    const awayFormation = mirrorFormation(getFormation(awayData.formation || '4-3-3'));

    // Create home team players
    this.homeTeam = { name: homeData.name, color: homeData.color, players: [] };
    homeData.players.forEach((pData, i) => {
      const formPos = homeFormation.positions[i];
      const player = new Player({
        id: `home_${i}`,
        name: pData.name,
        number: pData.number,
        position: formPos?.role || pData.position,
        attributes: pData.attributes,
        teamSide: 'home',
      });
      
      if (formPos) {
        player.position.set(formPos.x, formPos.y);
        player.homePosition.set(formPos.x, formPos.y);
      }
      
      this.homeTeam.players.push(player);
      this.allPlayers.push(player);
      
      // Create AI brain
      if (player.isGoalkeeper()) {
        const brain = new GoalkeeperBrain(player, this.rng);
        brain.initialize('home');
        this.playerBrains.set(player.id, brain);
      } else {
        this.playerBrains.set(player.id, new PlayerBrain(player, this.rng));
      }
      
      // Create animation instances
      this.walkAnimations.set(player.id, new ProceduralWalk());
      this.kickAnimations.set(player.id, new KickAnimation());
    });

    // Create away team players
    this.awayTeam = { name: awayData.name, color: awayData.color, players: [] };
    awayData.players.forEach((pData, i) => {
      const formPos = awayFormation.positions[i];
      const player = new Player({
        id: `away_${i}`,
        name: pData.name,
        number: pData.number,
        position: formPos?.role || pData.position,
        attributes: pData.attributes,
        teamSide: 'away',
      });
      
      if (formPos) {
        player.position.set(formPos.x, formPos.y);
        player.homePosition.set(formPos.x, formPos.y);
      }
      
      this.awayTeam.players.push(player);
      this.allPlayers.push(player);
      
      if (player.isGoalkeeper()) {
        const brain = new GoalkeeperBrain(player, this.rng);
        brain.initialize('away');
        this.playerBrains.set(player.id, brain);
      } else {
        this.playerBrains.set(player.id, new PlayerBrain(player, this.rng));
      }
      
      this.walkAnimations.set(player.id, new ProceduralWalk());
      this.kickAnimations.set(player.id, new KickAnimation());
    });
  }

  _initWeather(weatherConfig) {
    this.weatherSystem.initialize(weatherConfig || {});
    
    if (weatherConfig?.weather === 'wet' || weatherConfig?.weather === 'rain_heavy') {
      this.pitchSurface.setConditions('wet');
      this.ballPhysics.setWeather('wet', this.weatherSystem.getWindForce());
    } else if (weatherConfig?.weather === 'snow') {
      this.pitchSurface.setConditions('snowy');
      this.ballPhysics.setWeather('snow', this.weatherSystem.getWindForce());
    }
  }

  _setupEngine() {
    // Physics system (fixed timestep)
    this.engine.addPhysicsSystem({
      update: (dt, matchTime, rng) => this._physicsUpdate(dt),
    });

    // Render system (every frame)
    this.engine.addRenderSystem({
      render: (interpolation) => this._render(interpolation),
    });
  }

  _setupResize() {
    const resize = () => {
      const container = this.canvas.parentElement;
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      
      if (w === 0 || h === 0) return;
      
      const dpr = window.devicePixelRatio || 1;
      this.canvas.width = w * dpr;
      this.canvas.height = h * dpr;
      this.canvas.style.width = w + 'px';
      this.canvas.style.height = h + 'px';
      
      this.camera.resize(w, h);
      this.uiOverlay.resize(w, h);
    };
    
    window.addEventListener('resize', resize);
    setTimeout(resize, 0);
    setTimeout(resize, 100);
  }

  // === PHYSICS UPDATE (Fixed timestep) ===

  _physicsUpdate(dt) {
    if (!this.matchState.isActive()) return;

    // Update match time
    const minuteIncrement = dt / MATCH_MINUTE_DURATION;
    this.matchState.matchMinute += minuteIncrement;
    this.matchState.elapsedTime += dt;

    // Update weather
    this.weatherSystem.update(dt);
    this.ballPhysics.setWeather(
      this.weatherSystem.weatherType === 'rain_heavy' ? 'wet' : 'dry',
      this.weatherSystem.getWindForce()
    );

    // Store previous positions for interpolation
    this.ball.storePrevious();
    for (const player of this.allPlayers) {
      player.storePrevious();
    }

    // Update ball physics (if not held by a player)
    if (this.ball.isHeld && this.ball.holder) {
      // Ball follows the holder - positioned slightly ahead in facing direction
      const holder = this.ball.holder;
      const ahead = Vector2.fromAngle(holder.facing);
      this.ball.position.x = holder.position.x + ahead.x * 0.8;
      this.ball.position.y = holder.position.y + ahead.y * 0.8;
      this.ball.velocity.set(0, 0);
      this.ball.height = 0;
    } else {
      this.ballPhysics.update(this.ball, dt);
    }
    this.ball.updateTrail();

    // Update AI decisions and player movement
    this._updateAI(dt);
    
    // Update player physics (movement, turning)
    this._updatePlayerMovement(dt);

    // Update fatigue
    this.fatigueSystem.update(this.allPlayers, dt, this.matchState.matchMinute);

    // Update possession tracking
    this._updatePossession(dt);

    // Check for ball out of bounds
    if (this.ball.isOutOfBounds) {
      this._handleBallOut();
    }

    // Update set pieces
    if (this.setPieceSystem.isActive()) {
      const action = this.setPieceSystem.update(dt);
      if (action) this._executeSetPieceAction(action);
    }

    // Update effects
    this.effects.update(dt, this.weatherSystem.getRenderData());

    // Check half end
    if (this.matchState.shouldEndHalf()) {
      this._endHalf();
    }

    // Record replay frame
    this.replay.recordFrame({
      ball: this.ball,
      players: this.allPlayers,
      matchMinute: this.matchState.matchMinute,
      homeScore: this.matchState.homeScore,
      awayScore: this.matchState.awayScore,
    });
  }

  _updateAI(dt) {
    for (const player of this.allPlayers) {
      if (!player.isActive) continue;
      
      const brain = this.playerBrains.get(player.id);
      if (!brain) continue;

      const context = {
        ball: this.ball,
        matchState: this.matchState,
        teammates: this.allPlayers.filter(p => p.teamSide === player.teamSide && p !== player),
        opponents: this.allPlayers.filter(p => p.teamSide !== player.teamSide),
        teamTactics: { pressing: 0.5 },
      };

      const command = brain.update(dt, context);
      if (command) {
        this._processAICommand(player, command, dt);
      }
    }
  }

  _processAICommand(player, command, dt) {
    switch (command.type) {
      case 'move':
        if (command.target) {
          const t = command.target instanceof Vector2 ? command.target : new Vector2(command.target.x, command.target.y);
          player.moveTo(t, command.mode || 'jog');
        }
        break;
      case 'pass':
        if (player.hasBall && command.target) {
          this._executePass(player, command.target);
        }
        break;
      case 'shoot':
        if (player.hasBall && command.target) {
          this._executeShot(player, command.target);
        }
        break;
      case 'dribble':
        if (player.hasBall && command.direction) {
          // Move toward goal while keeping ball
          const attackDir = player.teamSide === 'home' ? 1 : -1;
          const dribbleTarget = new Vector2(
            Math.max(5, Math.min(PITCH_WIDTH - 5, player.position.x + attackDir * 15)),
            Math.max(5, Math.min(PITCH_HEIGHT - 5, player.position.y + (this.rng.next() - 0.5) * 8))
          );
          player.moveTo(dribbleTarget, 'jog');
          // Ball stays with player (isHeld = true)
        }
        break;
      case 'cross':
        if (player.hasBall && command.target) {
          this._executeCross(player, command.target);
        }
        break;
      case 'dive':
        break;
      case 'stay':
        break;
    }
  }

  _executePass(player, target) {
    const targetPos = target.position ? target.position : (target instanceof Vector2 ? target : new Vector2(target.x, target.y));
    const dist = player.position.distance(targetPos);
    const power = Math.min(0.9, 0.3 + dist / 60); // Auto power based on distance
    
    this.ballPhysics.pass(this.ball, targetPos, power, player.getEffectiveAttr('passing'), this.rng);
    player.hasBall = false;
    this.ball.isHeld = false;
    this.ball.holder = null;
    this.ball.lastTouchedBy = player;
    this.ball.lastTouchedTeam = player.teamSide;
    this.matchState.ballOwnership = BallOwnership.PASS_GROUND;
    this.matchState.ballIntendedTarget = target;
    this.matchState.ballOwner = null;
    
    // Offside snapshot
    this.offsideSystem.snapshotAtPass(player, this.allPlayers, this.ball);
    
    player.matchStats.passes++;
    this._holdTimer = 0;
  }

  _executeShot(player, target) {
    const targetPos = target instanceof Vector2 ? target : new Vector2(target.x, target.y);
    const power = 0.7 + this.rng.range(0, 0.3);
    this.ballPhysics.shoot(this.ball, targetPos, power, player.getEffectiveAttr('shooting'), player.getEffectiveAttr('technique'), this.rng);
    player.hasBall = false;
    this.ball.isHeld = false;
    this.ball.holder = null;
    this.ball.lastTouchedBy = player;
    this.ball.lastTouchedTeam = player.teamSide;
    this.matchState.ballOwnership = BallOwnership.SHOT;
    
    player.matchStats.shots++;
    
    // Start kick animation
    const kickAnim = this.kickAnimations.get(player.id);
    if (kickAnim) kickAnim.start('instep', 'right', power);
    
    // Update stats
    if (player.teamSide === 'home') this.matchState.homeShots++;
    else this.matchState.awayShots++;
  }

  _executeCross(player, target) {
    const targetPos = target instanceof Vector2 ? target : new Vector2(target.x, target.y);
    this.ballPhysics.cross(this.ball, targetPos, player.getEffectiveAttr('crossing'), this.rng);
    player.hasBall = false;
    this.ball.isHeld = false;
    this.ball.holder = null;
    this.ball.lastTouchedBy = player;
    this.ball.lastTouchedTeam = player.teamSide;
    this.matchState.ballOwnership = BallOwnership.PASS_AIR;
  }

  _updatePlayerMovement(dt) {
    for (const player of this.allPlayers) {
      if (!player.isActive) continue;
      if (!player.targetPosition) continue;

      const target = player.targetPosition;
      const toTarget = target.sub(player.position);
      const dist = toTarget.length();

      if (dist < 0.5) {
        player.currentSpeed *= 0.9; // Decelerate near target
        if (player.currentSpeed < 0.1) player.currentSpeed = 0;
        continue;
      }

      // Determine target speed based on movement mode
      const paceAttr = player.getEffectiveAttr('pace');
      const fatigueFactor = player.getFatigueFactor();
      let targetSpeed;
      
      switch (player.movementMode) {
        case 'sprint': targetSpeed = (7 + (paceAttr / 20) * 3.5) * fatigueFactor; break;
        case 'jog': targetSpeed = 4.0 * fatigueFactor; break;
        default: targetSpeed = 1.5; break;
      }

      // Acceleration
      const accelAttr = player.getEffectiveAttr('acceleration');
      const accelRate = 3 + (accelAttr / 20) * 5; // 3-8 m/s²
      
      if (player.currentSpeed < targetSpeed) {
        player.currentSpeed = Math.min(targetSpeed, player.currentSpeed + accelRate * dt);
      } else {
        player.currentSpeed = Math.max(targetSpeed, player.currentSpeed - accelRate * 1.5 * dt);
      }

      // Turn toward target
      const targetAngle = toTarget.angle();
      let angleDiff = targetAngle - player.facing;
      while (angleDiff > Math.PI) angleDiff -= Math.PI * 2;
      while (angleDiff < -Math.PI) angleDiff += Math.PI * 2;

      const turnRate = 6 - (player.currentSpeed / 10) * 3.5; // Slower turn at high speed
      const maxTurn = turnRate * dt;
      player.facing += Math.max(-maxTurn, Math.min(maxTurn, angleDiff));

      // Move in facing direction
      const moveDir = Vector2.fromAngle(player.facing);
      player.velocity.x = moveDir.x * player.currentSpeed;
      player.velocity.y = moveDir.y * player.currentSpeed;
      player.position.x += player.velocity.x * dt;
      player.position.y += player.velocity.y * dt;

      // Clamp to pitch
      player.position.x = Math.max(-2, Math.min(PITCH_WIDTH + 2, player.position.x));
      player.position.y = Math.max(-2, Math.min(PITCH_HEIGHT + 2, player.position.y));

      // Update state
      if (player.currentSpeed > 6) player.state = PlayerState.SPRINTING;
      else if (player.currentSpeed > 2) player.state = PlayerState.JOGGING;
      else if (player.currentSpeed > 0.5) player.state = PlayerState.WALKING;
      else player.state = PlayerState.IDLE;

      // Pitch wear
      if (player.currentSpeed > 5) {
        this.pitchSurface.addWear(player.position.x, player.position.y, 0.0001);
      }
    }
  }

  _updatePossession(dt) {
    if (this.matchState.ballOwner) {
      if (this.matchState.ballOwner.teamSide === 'home') {
        this.matchState.homePossessionTime += dt;
      } else {
        this.matchState.awayPossessionTime += dt;
      }
    }

    // If ball is loose or rolling (pass), check if any player can pick it up
    if (!this.ball.isHeld && this.matchState.playState === PlayState.IN_PLAY) {
      let closestPlayer = null;
      let closestDist = Infinity;
      
      for (const player of this.allPlayers) {
        if (!player.isActive) continue;
        const dist = player.position.distance(this.ball.position);
        player.distToBall = dist;
        
        if (dist < PLAYER_CONTROL_RADIUS * 1.5 && this.ball.height < 1.5) {
          // Player can pick up ball immediately
          this.ballContact.processFirstTouch(player, this.ball, this.rng);
          player.hasBall = true;
          this.ball.isHeld = true;
          this.ball.holder = player;
          this.ball.lastTouchedBy = player;
          this.ball.lastTouchedTeam = player.teamSide;
          this.matchState.ballOwner = player;
          this.matchState.ballOwnership = BallOwnership.HELD;
          closestPlayer = null;
          break;
        }
        
        if (dist < closestDist && !player.isGoalkeeper()) {
          closestDist = dist;
          closestPlayer = player;
        }
      }
      
      // Make 2 closest players from each team run to ball
      if (!this.ball.isHeld && closestDist > PLAYER_CONTROL_RADIUS) {
        const chasers = this.allPlayers
          .filter(p => p.isActive && !p.isGoalkeeper())
          .sort((a, b) => a.distToBall - b.distToBall)
          .slice(0, 3);
        
        for (const chaser of chasers) {
          chaser.moveTo(this.ball.position.clone(), chaser.distToBall < 8 ? 'sprint' : 'jog');
        }
      }
    }
  }

  _handleBallOut() {
    // Determine which team gets the ball (opposite of last touch)
    const lastTeam = this.ball.lastTouchedTeam;
    const awardedTeam = lastTeam === 'home' ? 'away' : 'home';
    
    // Stop ball
    this.ball.velocity.set(0, 0);
    this.ball.verticalVelocity = 0;
    this.ball.height = 0;
    this.ball.isOutOfBounds = false;
    this.ball.isHeld = false;
    this.ball.holder = null;
    
    // Remove ball from any player
    for (const p of this.allPlayers) {
      p.hasBall = false;
    }
    
    // Place ball back on pitch edge (simplified: just give to nearest player of awarded team)
    const clampedX = Math.max(1, Math.min(PITCH_WIDTH - 1, this.ball.position.x));
    const clampedY = Math.max(1, Math.min(PITCH_HEIGHT - 1, this.ball.position.y));
    this.ball.position.set(clampedX, clampedY);
    
    // Give ball to nearest player of awarded team after brief pause
    setTimeout(() => {
      const receiver = this._findNearestPlayer(this.ball.position, awardedTeam);
      if (receiver) {
        receiver.hasBall = true;
        this.ball.isHeld = true;
        this.ball.holder = receiver;
        this.ball.lastTouchedBy = receiver;
        this.ball.lastTouchedTeam = receiver.teamSide;
        this.matchState.ballOwner = receiver;
        this.matchState.ballOwnership = BallOwnership.HELD;
        this.matchState.playState = PlayState.IN_PLAY;
      }
    }, 500);
    
    this.matchState.playState = PlayState.THROW_IN;
    this.matchState.ballOwnership = BallOwnership.DEAD;
  }

  _executeSetPieceAction(action) {
    this.matchState.playState = PlayState.IN_PLAY;
    this.matchState.ballOwnership = BallOwnership.HELD;
  }

  _endHalf() {
    if (this.matchState.phase === MatchPhase.FIRST_HALF) {
      this.matchState.phase = MatchPhase.HALF_TIME;
      this.uiOverlay.addNotification('⏱️ HALF TIME');
      
      // Auto-start second half after delay
      setTimeout(() => {
        this.matchState.phase = MatchPhase.SECOND_HALF;
        this.matchState.stoppageAdded = 0;
        this.ball.resetToCenter();
        this._positionForKickOff('away');
        
        setTimeout(() => {
          this.matchState.playState = PlayState.IN_PLAY;
          const kickOffPlayer = this._findNearestPlayer(this.ball.position, 'away');
          if (kickOffPlayer) {
            kickOffPlayer.hasBall = true;
            this.ball.holder = kickOffPlayer;
            this.matchState.ballOwner = kickOffPlayer;
            this.matchState.ballOwnership = BallOwnership.HELD;
          }
        }, 1000);
      }, 3000);
    } else if (this.matchState.phase === MatchPhase.SECOND_HALF) {
      this.matchState.phase = MatchPhase.FULL_TIME;
      this.engine.stop();
      this.uiOverlay.addNotification('🏁 FULL TIME');
      this.replay.stopRecording();
    }
  }

  _positionForKickOff(team) {
    // Reset all players to formation positions
    for (const player of this.allPlayers) {
      player.position.copy(player.homePosition);
      player.velocity.set(0, 0);
      player.currentSpeed = 0;
      player.hasBall = false;
    }
    this.ball.holder = null;
    this.ball.isHeld = false;
  }

  _findNearestPlayer(position, teamSide) {
    let nearest = null;
    let minDist = Infinity;
    const players = teamSide === 'home' ? this.homeTeam.players : this.awayTeam.players;
    
    for (const player of players) {
      if (!player.isActive || player.isGoalkeeper()) continue;
      const dist = player.position.distance(position);
      if (dist < minDist) {
        minDist = dist;
        nearest = player;
      }
    }
    return nearest;
  }

  // === RENDERING ===

  _render(interpolation) {
    const ctx = this.ctx;
    const w = this.canvas.parentElement?.clientWidth || this.canvas.width;
    const h = this.canvas.parentElement?.clientHeight || this.canvas.height;

    if (w === 0 || h === 0) return;

    // Clear in screen space
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.restore();

    // Apply DPR
    const dpr = window.devicePixelRatio || 1;
    ctx.save();
    ctx.scale(dpr, dpr);

    // Fill background
    ctx.fillStyle = '#1a3d1a';
    ctx.fillRect(0, 0, w, h);

    // Update camera
    this.camera.update(this.ball, PHYSICS_TIMESTEP);

    // Apply camera transform (world space)
    this.camera.applyTransform(ctx);

    // Draw pitch
    this.pitchRenderer.draw(ctx, this.pitchSurface.getRenderData());

    // Draw effects (on pitch: slide marks, etc.)
    this.effects.draw(ctx, this.weatherSystem.getRenderData());

    // Draw players
    for (const player of this.allPlayers) {
      if (!player.isActive) continue;
      
      const walkAnim = this.walkAnimations.get(player.id);
      const pose = walkAnim ? walkAnim.update(player.currentSpeed, PHYSICS_TIMESTEP, player.stamina) : null;
      
      this.playerRenderer.drawPlayer(ctx, player, pose, interpolation, {
        teamColor: player.teamSide === 'home' ? this.homeTeam.color : this.awayTeam.color,
        hasBall: player.hasBall,
        isHighlighted: false,
      });
    }

    // Draw ball
    this.ballRenderer.draw(ctx, this.ball, interpolation);

    // Restore from camera transform
    ctx.restore(); // camera
    ctx.restore(); // dpr

    // Draw UI overlay (screen space, with dpr)
    ctx.save();
    ctx.scale(dpr, dpr);
    this.uiOverlay.draw(ctx, this.matchState, {
      homeTeam: this.homeTeam.name,
      awayTeam: this.awayTeam.name,
      homeColor: this.homeTeam.color,
      awayColor: this.awayTeam.color,
      players: this.allPlayers,
      ball: this.ball,
    });

    // Draw weather effects (screen space)
    this.effects.drawWeather(ctx, w, h, this.weatherSystem.getRenderData());
    ctx.restore();
  }

  // === PUBLIC API ===

  /**
   * Get current match state
   */
  getMatchState() {
    return this.matchState;
  }

  /**
   * Get replay data
   */
  getReplay() {
    return this.replay;
  }

  /**
   * Destroy and clean up
   */
  destroy() {
    this.engine.destroy();
    window.removeEventListener('resize', this._setupResize);
  }
}
