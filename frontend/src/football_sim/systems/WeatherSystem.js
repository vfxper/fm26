/**
 * WeatherSystem - Weather simulation and its effects on gameplay
 * Rain, snow, fog, wind, heat, time of day
 */
import { Vector2 } from '../core/Vector2.js';
import { WIND_MAX_SPEED, RAIN_ACCURACY_PENALTY } from '../core/Constants.js';

export const WeatherType = {
  CLEAR: 'clear',
  CLOUDY: 'cloudy',
  RAIN_LIGHT: 'rain_light',
  RAIN_HEAVY: 'rain_heavy',
  SNOW: 'snow',
  FOG: 'fog',
  HAIL: 'hail',
};

export const TimeOfDay = {
  AFTERNOON: 'afternoon',   // 14:00-17:00, full sun
  EVENING: 'evening',       // 17:00-20:00, low sun, shadows
  NIGHT: 'night',           // 20:00+, floodlights
};

export class WeatherSystem {
  constructor(rng) {
    this.rng = rng;
    
    // Current conditions
    this.weatherType = WeatherType.CLEAR;
    this.timeOfDay = TimeOfDay.AFTERNOON;
    this.temperature = 18; // Celsius
    
    // Wind
    this.windDirection = 0; // radians
    this.windSpeed = 0;    // m/s
    this.windGustTimer = 0;
    this.windGustStrength = 0;
    this.currentWind = new Vector2(0, 0);
    
    // Rain
    this.rainIntensity = 0; // 0-1
    this.rainAccumulation = 0; // affects pitch
    
    // Snow
    this.snowIntensity = 0;
    this.snowAccumulation = 0;
    
    // Fog
    this.fogDensity = 0; // 0-1 (affects visibility)
    
    // Visibility factor (1 = perfect, 0 = zero visibility)
    this.visibility = 1.0;
    
    // Effects on gameplay
    this.passingPenalty = 0;    // 0-0.3
    this.shootingPenalty = 0;   // 0-0.2
    this.speedPenalty = 0;      // 0-0.15
    this.fatigueFactor = 1.0;   // 1.0-1.4
  }

  /**
   * Initialize weather for a match
   */
  initialize(config = {}) {
    this.weatherType = config.weather || WeatherType.CLEAR;
    this.timeOfDay = config.timeOfDay || TimeOfDay.AFTERNOON;
    this.temperature = config.temperature || 18;
    this.windSpeed = config.windSpeed || 0;
    this.windDirection = config.windDirection || 0;
    
    this._applyWeatherEffects();
  }

  /**
   * Update weather each physics tick
   * @param {number} dt - Delta time
   */
  update(dt) {
    // Wind gusts
    this.windGustTimer -= dt;
    if (this.windGustTimer <= 0) {
      // New gust
      this.windGustTimer = this.rng.range(2, 8);
      this.windGustStrength = this.rng.range(-0.3, 0.3) * this.windSpeed;
    }
    
    // Calculate current wind vector with gusts
    const effectiveSpeed = this.windSpeed + this.windGustStrength;
    this.currentWind.x = Math.cos(this.windDirection) * effectiveSpeed;
    this.currentWind.y = Math.sin(this.windDirection) * effectiveSpeed;
    
    // Accumulate rain/snow
    if (this.rainIntensity > 0) {
      this.rainAccumulation += this.rainIntensity * dt * 0.001;
    }
    if (this.snowIntensity > 0) {
      this.snowAccumulation += this.snowIntensity * dt * 0.0005;
    }
  }

  /**
   * Get wind force vector for ball physics
   * @returns {Vector2} Wind force
   */
  getWindForce() {
    return this.currentWind.clone();
  }

  /**
   * Get passing accuracy penalty (0-0.3)
   */
  getPassingPenalty() {
    return this.passingPenalty;
  }

  /**
   * Get shooting accuracy penalty
   */
  getShootingPenalty() {
    return this.shootingPenalty;
  }

  /**
   * Get player speed penalty
   */
  getSpeedPenalty() {
    return this.speedPenalty;
  }

  /**
   * Get fatigue multiplier
   */
  getFatigueFactor() {
    return this.fatigueFactor;
  }

  /**
   * Get render data for visual effects
   */
  getRenderData() {
    return {
      weatherType: this.weatherType,
      timeOfDay: this.timeOfDay,
      rainIntensity: this.rainIntensity,
      snowIntensity: this.snowIntensity,
      fogDensity: this.fogDensity,
      windDirection: this.windDirection,
      windSpeed: this.windSpeed,
      visibility: this.visibility,
      temperature: this.temperature,
    };
  }

  _applyWeatherEffects() {
    switch (this.weatherType) {
      case WeatherType.CLEAR:
        this.rainIntensity = 0;
        this.snowIntensity = 0;
        this.fogDensity = 0;
        this.visibility = 1.0;
        this.passingPenalty = 0;
        this.shootingPenalty = 0;
        this.speedPenalty = 0;
        break;
        
      case WeatherType.RAIN_LIGHT:
        this.rainIntensity = 0.3;
        this.visibility = 0.9;
        this.passingPenalty = 0.05;
        this.shootingPenalty = 0.03;
        this.speedPenalty = 0.02;
        break;
        
      case WeatherType.RAIN_HEAVY:
        this.rainIntensity = 0.8;
        this.visibility = 0.7;
        this.passingPenalty = 0.15;
        this.shootingPenalty = 0.1;
        this.speedPenalty = 0.05;
        break;
        
      case WeatherType.SNOW:
        this.snowIntensity = 0.5;
        this.visibility = 0.6;
        this.passingPenalty = 0.2;
        this.shootingPenalty = 0.1;
        this.speedPenalty = 0.1;
        this.fatigueFactor = 1.2;
        break;
        
      case WeatherType.FOG:
        this.fogDensity = 0.6;
        this.visibility = 0.4;
        this.passingPenalty = 0.1; // Can't see far
        this.shootingPenalty = 0.15;
        break;
        
      case WeatherType.CLOUDY:
        this.visibility = 0.95;
        break;
    }
    
    // Temperature effects
    if (this.temperature > 30) {
      this.fatigueFactor = 1.3;
      this.speedPenalty += 0.03;
    } else if (this.temperature < 5) {
      this.fatigueFactor = 1.1;
    }
    
    // Wind effects on passing
    if (this.windSpeed > 4) {
      this.passingPenalty += (this.windSpeed / WIND_MAX_SPEED) * 0.1;
    }
  }
}
