/**
 * Constants - All physics and game constants for the football simulation
 */

// Pitch dimensions in meters
export const PITCH_WIDTH = 105;
export const PITCH_HEIGHT = 68;
export const HALF_PITCH_WIDTH = PITCH_WIDTH / 2;
export const HALF_PITCH_HEIGHT = PITCH_HEIGHT / 2;

// Goal dimensions
export const GOAL_WIDTH = 7.32;
export const GOAL_DEPTH = 2.44;
export const GOAL_Y_MIN = (PITCH_HEIGHT - GOAL_WIDTH) / 2;
export const GOAL_Y_MAX = (PITCH_HEIGHT + GOAL_WIDTH) / 2;

// Penalty area
export const PENALTY_AREA_WIDTH = 40.32;
export const PENALTY_AREA_DEPTH = 16.5;
export const GOAL_AREA_WIDTH = 18.32;
export const GOAL_AREA_DEPTH = 5.5;
export const PENALTY_SPOT_DISTANCE = 11;
export const CENTER_CIRCLE_RADIUS = 9.15;

// Ball physics
export const BALL_MASS = 0.43; // kg
export const BALL_RADIUS = 0.11; // meters (circumference ~0.7m)
export const BALL_DRAG_COEFFICIENT = 0.05; // REDUCED - was too high, ball was dying instantly
export const BALL_AIR_DENSITY = 1.225; // kg/m³
export const BALL_CROSS_SECTION = Math.PI * BALL_RADIUS * BALL_RADIUS;
export const BALL_BOUNCE_RESTITUTION = 0.7;
export const BALL_MAX_SPEED = 35; // m/s (~126 km/h)
export const BALL_MAGNUS_COEFFICIENT = 0.08; // Reduced - was causing crazy curves
export const GRAVITY = 9.81; // m/s²

// Ground friction coefficients - REDUCED for realistic rolling
export const FRICTION_DRY = 0.15; // Was 0.4 - ball was stopping too fast
export const FRICTION_WET = 0.10;
export const FRICTION_SNOW = 0.08;

// Player physics
export const PLAYER_RADIUS = 0.4; // meters
export const PLAYER_MASS = 75; // kg (average)
export const PLAYER_MIN_SPEED = 7.0; // m/s (pace 1)
export const PLAYER_MAX_SPEED = 10.0; // m/s (pace 20)
export const PLAYER_WALK_SPEED = 1.5; // m/s
export const PLAYER_JOG_SPEED = 4.0; // m/s
export const PLAYER_ACCEL_TIME_MIN = 1.5; // seconds (acceleration 20)
export const PLAYER_ACCEL_TIME_MAX = 3.0; // seconds (acceleration 1)
export const PLAYER_DECEL_FACTOR = 0.8; // deceleration is faster
export const PLAYER_TURN_RATE_BASE = 6.0; // radians/sec at low speed
export const PLAYER_TURN_RATE_SPRINT = 2.5; // radians/sec at sprint

// Player control
export const PLAYER_KICK_RANGE = 1.2; // meters - how close to ball to kick
export const PLAYER_TACKLE_RANGE = 1.5; // meters
export const PLAYER_HEADER_HEIGHT = 1.8; // meters - ball height for header
export const PLAYER_CONTROL_RADIUS = 0.8; // meters - ball control range

// AI timing
export const AI_DECISION_INTERVAL = 0.5; // seconds between decisions
export const AI_REACTION_TIME_MIN = 0.1; // seconds
export const AI_REACTION_TIME_MAX = 0.4; // seconds

// Match timing
export const MATCH_DURATION_MINUTES = 90;
export const HALF_DURATION_MINUTES = 45;
export const EXTRA_TIME_HALF = 15;
export const PHYSICS_TIMESTEP = 1 / 60; // 60 Hz fixed timestep
export const RENDER_TIMESTEP = 1 / 60; // 60 FPS target

// Simulation time scale: how many real seconds = 1 match minute
export const MATCH_MINUTE_DURATION = 1.5; // 1.5 real seconds per match minute at 1x speed

// Fatigue
export const FATIGUE_WALK_RATE = 0.008; // per minute
export const FATIGUE_JOG_RATE = 0.02; // per minute
export const FATIGUE_SPRINT_RATE = 0.04; // per minute
export const FATIGUE_RECOVERY_RATE = 0.005; // per minute when walking
export const FATIGUE_THRESHOLD_LOW = 0.5; // below this: -15% speed
export const FATIGUE_THRESHOLD_CRITICAL = 0.25; // below this: -30% speed
export const FATIGUE_SPEED_PENALTY_LOW = 0.15;
export const FATIGUE_SPEED_PENALTY_CRITICAL = 0.30;
export const FATIGUE_ATTR_PENALTY_LOW = 0.10;
export const FATIGUE_ATTR_PENALTY_CRITICAL = 0.20;

// Referee
export const ADVANTAGE_WINDOW = 3.0; // seconds
export const OFFSIDE_TOLERANCE = 0.3; // meters (benefit of doubt)

// Weather
export const WIND_MAX_SPEED = 8; // m/s
export const RAIN_ACCURACY_PENALTY = 0.1; // -10% passing accuracy
export const SNOW_VISIBILITY_FACTOR = 0.7;

// Rendering
export const CAMERA_LERP_SPEED = 0.05;
export const MINIMAP_SIZE = 0.15; // fraction of canvas width
export const MINIMAP_PADDING = 10; // pixels

// Attribute scale
export const ATTR_MIN = 1;
export const ATTR_MAX = 20;

// Seeded random
export const DEFAULT_SEED = 42;
