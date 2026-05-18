/**
 * MatchState - Central match state: score, time, phase, ball ownership
 */
import { MATCH_DURATION_MINUTES, HALF_DURATION_MINUTES, EXTRA_TIME_HALF } from './Constants.js';

export const MatchPhase = {
  PRE_MATCH: 'pre_match',
  FIRST_HALF: 'first_half',
  HALF_TIME: 'half_time',
  SECOND_HALF: 'second_half',
  EXTRA_FIRST: 'extra_first',
  EXTRA_BREAK: 'extra_break',
  EXTRA_SECOND: 'extra_second',
  PENALTIES: 'penalties',
  FULL_TIME: 'full_time',
};

export const BallOwnership = {
  HELD: 'held',           // Ball at player's feet, dribbling
  PASS_AIR: 'pass_air',  // Ball in flight (pass)
  PASS_GROUND: 'pass_ground', // Ball rolling (ground pass)
  SHOT: 'shot',           // Ball heading toward goal
  LOOSE: 'loose',         // Contested / deflection (max 1 sec)
  DEAD: 'dead',           // Out of play, set piece pending
};

export const PlayState = {
  IN_PLAY: 'in_play',
  GOAL_KICK: 'goal_kick',
  CORNER: 'corner',
  THROW_IN: 'throw_in',
  FREE_KICK: 'free_kick',
  PENALTY: 'penalty',
  KICK_OFF: 'kick_off',
  DROPPED_BALL: 'dropped_ball',
  GOAL_SCORED: 'goal_scored',
  HALF_TIME_BREAK: 'half_time_break',
  INJURY_STOP: 'injury_stop',
  VAR_CHECK: 'var_check',
};

export class MatchState {
  constructor() {
    // Score
    this.homeScore = 0;
    this.awayScore = 0;

    // Time
    this.matchMinute = 0;       // 0-90+ (display minute)
    this.matchSeconds = 0;      // 0-59
    this.elapsedTime = 0;       // Total elapsed sim time in seconds
    this.stoppageTime = 0;      // Added time for current half
    this.stoppageAdded = 0;     // How much stoppage was added

    // Phase
    this.phase = MatchPhase.PRE_MATCH;
    this.playState = PlayState.KICK_OFF;

    // Ball ownership
    this.ballOwnership = BallOwnership.DEAD;
    this.ballOwner = null;        // Player currently controlling
    this.ballIntendedTarget = null; // For passes: who it's going to
    this.ballLastTouchedBy = null;
    this.ballLastTouchedTeam = null; // 'home' or 'away'
    this.looseTimer = 0;          // Time ball has been loose (max 1 sec rule)

    // Possession tracking
    this.homePossessionTime = 0;
    this.awayPossessionTime = 0;

    // Set piece info
    this.setPieceTeam = null;     // 'home' or 'away'
    this.setPiecePosition = null; // Vector2
    this.setPieceTaker = null;    // Player taking set piece

    // Events log
    this.events = [];

    // Cards
    this.homeYellowCards = 0;
    this.awayYellowCards = 0;
    this.homeRedCards = 0;
    this.awayRedCards = 0;

    // Substitutions
    this.homeSubsUsed = 0;
    this.awaySubsUsed = 0;
    this.maxSubs = 5;

    // Stats
    this.homeShots = 0;
    this.awayShots = 0;
    this.homeShotsOnTarget = 0;
    this.awayShotsOnTarget = 0;
    this.homeCorners = 0;
    this.awayCorners = 0;
    this.homeFouls = 0;
    this.awayFouls = 0;
    this.homeOffsides = 0;
    this.awayOffsides = 0;

    // Advantage play
    this.advantageActive = false;
    this.advantageTeam = null;
    this.advantageTimer = 0;
    this.pendingFoul = null;
  }

  /**
   * Get display time string (e.g., "45+2'")
   */
  getTimeString() {
    const min = Math.floor(this.matchMinute);
    if (this.stoppageAdded > 0 && this.matchMinute > HALF_DURATION_MINUTES) {
      const extra = Math.floor(this.matchMinute - (this.phase === MatchPhase.FIRST_HALF ? HALF_DURATION_MINUTES : MATCH_DURATION_MINUTES));
      if (extra > 0) {
        const base = this.phase === MatchPhase.FIRST_HALF ? 45 : 90;
        return `${base}+${extra}'`;
      }
    }
    return `${min}'`;
  }

  /**
   * Get possession percentage
   */
  getPossession() {
    const total = this.homePossessionTime + this.awayPossessionTime;
    if (total === 0) return { home: 50, away: 50 };
    return {
      home: Math.round((this.homePossessionTime / total) * 100),
      away: Math.round((this.awayPossessionTime / total) * 100),
    };
  }

  /**
   * Add event to log
   */
  addEvent(event) {
    event.minute = Math.floor(this.matchMinute);
    event.second = Math.floor(this.matchSeconds);
    event.timestamp = this.elapsedTime;
    this.events.push(event);
  }

  /**
   * Is the ball in play?
   */
  isInPlay() {
    return this.playState === PlayState.IN_PLAY;
  }

  /**
   * Is the match currently active (clock running)?
   */
  isActive() {
    return this.phase === MatchPhase.FIRST_HALF ||
           this.phase === MatchPhase.SECOND_HALF ||
           this.phase === MatchPhase.EXTRA_FIRST ||
           this.phase === MatchPhase.EXTRA_SECOND;
  }

  /**
   * Check if half should end
   */
  shouldEndHalf() {
    if (this.phase === MatchPhase.FIRST_HALF) {
      return this.matchMinute >= HALF_DURATION_MINUTES + this.stoppageAdded;
    }
    if (this.phase === MatchPhase.SECOND_HALF) {
      return this.matchMinute >= MATCH_DURATION_MINUTES + this.stoppageAdded;
    }
    if (this.phase === MatchPhase.EXTRA_FIRST) {
      return this.matchMinute >= MATCH_DURATION_MINUTES + EXTRA_TIME_HALF + this.stoppageAdded;
    }
    if (this.phase === MatchPhase.EXTRA_SECOND) {
      return this.matchMinute >= MATCH_DURATION_MINUTES + EXTRA_TIME_HALF * 2 + this.stoppageAdded;
    }
    return false;
  }
}
