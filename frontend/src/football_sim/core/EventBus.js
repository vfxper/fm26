/**
 * EventBus - Pub/sub event system for decoupled communication between modules
 */
export class EventBus {
  constructor() {
    this._listeners = new Map();
    this._onceListeners = new Map();
  }

  /**
   * Subscribe to an event
   * @param {string} event - Event name
   * @param {Function} callback - Handler function
   * @returns {Function} Unsubscribe function
   */
  on(event, callback) {
    if (!this._listeners.has(event)) {
      this._listeners.set(event, []);
    }
    this._listeners.get(event).push(callback);
    return () => this.off(event, callback);
  }

  /**
   * Subscribe to an event once
   * @param {string} event - Event name
   * @param {Function} callback - Handler function
   */
  once(event, callback) {
    if (!this._onceListeners.has(event)) {
      this._onceListeners.set(event, []);
    }
    this._onceListeners.get(event).push(callback);
  }

  /**
   * Unsubscribe from an event
   * @param {string} event - Event name
   * @param {Function} callback - Handler to remove
   */
  off(event, callback) {
    const listeners = this._listeners.get(event);
    if (listeners) {
      const idx = listeners.indexOf(callback);
      if (idx !== -1) listeners.splice(idx, 1);
    }
    const once = this._onceListeners.get(event);
    if (once) {
      const idx = once.indexOf(callback);
      if (idx !== -1) once.splice(idx, 1);
    }
  }

  /**
   * Emit an event
   * @param {string} event - Event name
   * @param {*} data - Event data
   */
  emit(event, data) {
    const listeners = this._listeners.get(event);
    if (listeners) {
      for (let i = 0; i < listeners.length; i++) {
        listeners[i](data);
      }
    }
    const once = this._onceListeners.get(event);
    if (once && once.length > 0) {
      const callbacks = [...once];
      this._onceListeners.set(event, []);
      for (let i = 0; i < callbacks.length; i++) {
        callbacks[i](data);
      }
    }
  }

  /**
   * Remove all listeners
   */
  clear() {
    this._listeners.clear();
    this._onceListeners.clear();
  }

  /**
   * Remove all listeners for a specific event
   * @param {string} event
   */
  clearEvent(event) {
    this._listeners.delete(event);
    this._onceListeners.delete(event);
  }
}

// Event name constants
export const EVENTS = {
  // Match flow
  MATCH_START: 'match:start',
  MATCH_END: 'match:end',
  HALF_TIME: 'match:halftime',
  SECOND_HALF_START: 'match:secondhalf',
  EXTRA_TIME_START: 'match:extratime',
  PENALTIES_START: 'match:penalties',

  // Goals and scoring
  GOAL_SCORED: 'goal:scored',
  SHOT_TAKEN: 'shot:taken',
  SHOT_SAVED: 'shot:saved',
  SHOT_MISSED: 'shot:missed',

  // Ball events
  BALL_KICKED: 'ball:kicked',
  BALL_PASSED: 'ball:passed',
  BALL_CROSSED: 'ball:crossed',
  BALL_OUT: 'ball:out',
  BALL_POSSESSION_CHANGE: 'ball:possession',

  // Player events
  PLAYER_TACKLE: 'player:tackle',
  PLAYER_FOUL: 'player:foul',
  PLAYER_INJURY: 'player:injury',
  PLAYER_SUBSTITUTION: 'player:substitution',

  // Referee
  FOUL_COMMITTED: 'ref:foul',
  CARD_SHOWN: 'ref:card',
  OFFSIDE_CALLED: 'ref:offside',
  ADVANTAGE_PLAYED: 'ref:advantage',
  FREE_KICK_AWARDED: 'ref:freekick',
  PENALTY_AWARDED: 'ref:penalty',
  CORNER_AWARDED: 'ref:corner',
  THROW_IN_AWARDED: 'ref:throwin',
  GOAL_KICK_AWARDED: 'ref:goalkick',

  // Set pieces
  SET_PIECE_START: 'setpiece:start',
  SET_PIECE_END: 'setpiece:end',

  // State changes
  STATE_CHANGE: 'state:change',
  POSSESSION_CHANGE: 'possession:change',

  // Commentary
  COMMENTARY: 'commentary:add',

  // Weather
  WEATHER_CHANGE: 'weather:change',
};
