/**
 * SettingsScreen.js - User settings and configuration UI
 *
 * Features:
 * - Language selection (en, ru, es, de, fr)
 * - Match simulation speed (1x, 2x, 4x, 10x)
 * - Sound effects toggle
 * - Background music toggle
 * - Notification preferences (match, transfer, training, contract)
 * - Dark/Light/Auto theme toggle
 * - Reset to defaults
 * - App version display and privacy policy link
 * - Immediate application of settings changes
 * - Persistence to server
 */

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'ru', label: 'Русский' },
  { code: 'es', label: 'Español' },
  { code: 'de', label: 'Deutsch' },
  { code: 'fr', label: 'Français' },
];

const MATCH_SPEEDS = [
  { value: 1, label: '1x (Slow)' },
  { value: 2, label: '2x (Normal)' },
  { value: 4, label: '4x (Fast)' },
  { value: 10, label: '10x (Instant)' },
];

const THEMES = [
  { value: 'auto', label: 'Auto (System)' },
  { value: 'dark', label: 'Dark' },
  { value: 'light', label: 'Light' },
];

const DEFAULT_SETTINGS = {
  language: 'en',
  match_speed: 2,
  sound_effects: true,
  background_music: true,
  notifications_match: true,
  notifications_transfer: true,
  notifications_training: true,
  notifications_contract: true,
  theme: 'auto',
};

export class SettingsScreen {
  constructor(options = {}) {
    this.apiClient = options.apiClient || null;
    this.onNavigate = options.onNavigate || null;
    this.element = null;
    this.settings = { ...DEFAULT_SETTINGS };
    this.appVersion = options.appVersion || '0.1.0';
    this.privacyPolicyUrl = options.privacyPolicyUrl || '/privacy';
    this._saveTimeout = null;
  }

  /**
   * Render the settings screen
   * @param {Object} [data] - Pre-loaded settings data
   * @returns {HTMLElement}
   */
  render(data = {}) {
    if (data.settings) {
      this.settings = { ...DEFAULT_SETTINGS, ...data.settings };
    }

    const screen = document.createElement('div');
    screen.className = 'screen settings-screen';
    screen.setAttribute('data-scrollable', '');

    screen.innerHTML = `
      <header class="screen__header">
        <h1 class="screen__title">Settings</h1>
      </header>

      <!-- Language Selection -->
      <section class="settings-screen__section" aria-label="Language">
        <div class="card">
          <div class="card-header">🌐 Language</div>
          <div class="card-body">
            <select id="settings-language" class="settings-screen__select" aria-label="Select language">
              ${LANGUAGES.map(
                (l) =>
                  `<option value="${l.code}" ${this.settings.language === l.code ? 'selected' : ''}>${l.label}</option>`
              ).join('')}
            </select>
          </div>
        </div>
      </section>

      <!-- Match Simulation Speed -->
      <section class="settings-screen__section" aria-label="Match Speed">
        <div class="card">
          <div class="card-header">⚡ Match Simulation Speed</div>
          <div class="card-body">
            <div class="settings-screen__speed-options" role="radiogroup" aria-label="Match speed">
              ${MATCH_SPEEDS.map(
                (s) =>
                  `<button class="settings-screen__speed-btn ${this.settings.match_speed === s.value ? 'settings-screen__speed-btn--active' : ''}"
                    data-speed="${s.value}" role="radio" aria-checked="${this.settings.match_speed === s.value}">
                    ${s.label}
                  </button>`
              ).join('')}
            </div>
          </div>
        </div>
      </section>

      <!-- Sound Settings -->
      <section class="settings-screen__section" aria-label="Sound">
        <div class="card">
          <div class="card-header">🔊 Sound</div>
          <div class="card-body">
            ${this._renderToggle('sound_effects', 'Sound Effects', this.settings.sound_effects)}
            ${this._renderToggle('background_music', 'Background Music', this.settings.background_music)}
          </div>
        </div>
      </section>

      <!-- Notification Preferences -->
      <section class="settings-screen__section" aria-label="Notifications">
        <div class="card">
          <div class="card-header">🔔 Notifications</div>
          <div class="card-body">
            ${this._renderToggle('notifications_match', 'Match Notifications', this.settings.notifications_match)}
            ${this._renderToggle('notifications_transfer', 'Transfer Notifications', this.settings.notifications_transfer)}
            ${this._renderToggle('notifications_training', 'Training Notifications', this.settings.notifications_training)}
            ${this._renderToggle('notifications_contract', 'Contract Notifications', this.settings.notifications_contract)}
          </div>
        </div>
      </section>

      <!-- Theme -->
      <section class="settings-screen__section" aria-label="Theme">
        <div class="card">
          <div class="card-header">🎨 Theme</div>
          <div class="card-body">
            <div class="settings-screen__theme-options" role="radiogroup" aria-label="Theme selection">
              ${THEMES.map(
                (t) =>
                  `<button class="settings-screen__theme-btn ${this.settings.theme === t.value ? 'settings-screen__theme-btn--active' : ''}"
                    data-theme="${t.value}" role="radio" aria-checked="${this.settings.theme === t.value}">
                    ${t.label}
                  </button>`
              ).join('')}
            </div>
          </div>
        </div>
      </section>

      <!-- Reset -->
      <section class="settings-screen__section" aria-label="Reset">
        <div class="card">
          <div class="card-body">
            <button id="settings-reset" class="settings-screen__reset-btn" aria-label="Reset all settings to defaults">
              🔄 Reset to Defaults
            </button>
          </div>
        </div>
      </section>

      <!-- App Info -->
      <section class="settings-screen__section settings-screen__section--footer" aria-label="App Info">
        <div class="settings-screen__app-info">
          <span class="settings-screen__version">Version ${this.appVersion}</span>
          <a href="${this.privacyPolicyUrl}" class="settings-screen__privacy-link" target="_blank" rel="noopener noreferrer">
            Privacy Policy
          </a>
        </div>
      </section>
    `;

    this.element = screen;
    this._bindEvents();
    return screen;
  }

  /**
   * Destroy and clean up
   */
  destroy() {
    if (this._saveTimeout) {
      clearTimeout(this._saveTimeout);
    }
    this.element = null;
  }

  /**
   * Bind event listeners for all interactive elements
   */
  _bindEvents() {
    if (!this.element) return;

    // Language select
    const langSelect = this.element.querySelector('#settings-language');
    if (langSelect) {
      langSelect.addEventListener('change', (e) => {
        this._updateSetting('language', e.target.value);
      });
    }

    // Match speed buttons
    const speedBtns = this.element.querySelectorAll('.settings-screen__speed-btn');
    speedBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        const speed = parseInt(btn.dataset.speed, 10);
        this._updateSetting('match_speed', speed);
        // Update active state
        speedBtns.forEach((b) => {
          b.classList.remove('settings-screen__speed-btn--active');
          b.setAttribute('aria-checked', 'false');
        });
        btn.classList.add('settings-screen__speed-btn--active');
        btn.setAttribute('aria-checked', 'true');
      });
    });

    // Toggle switches
    const toggles = this.element.querySelectorAll('.settings-screen__toggle-input');
    toggles.forEach((toggle) => {
      toggle.addEventListener('change', (e) => {
        this._updateSetting(e.target.dataset.key, e.target.checked);
      });
    });

    // Theme buttons
    const themeBtns = this.element.querySelectorAll('.settings-screen__theme-btn');
    themeBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        this._updateSetting('theme', btn.dataset.theme);
        themeBtns.forEach((b) => {
          b.classList.remove('settings-screen__theme-btn--active');
          b.setAttribute('aria-checked', 'false');
        });
        btn.classList.add('settings-screen__theme-btn--active');
        btn.setAttribute('aria-checked', 'true');
        this._applyTheme(btn.dataset.theme);
      });
    });

    // Reset button
    const resetBtn = this.element.querySelector('#settings-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this._resetSettings());
    }
  }

  /**
   * Update a single setting, apply immediately, and persist
   */
  _updateSetting(key, value) {
    this.settings[key] = value;
    this._applySettingImmediately(key, value);
    this._debouncedSave();
  }

  /**
   * Apply a setting change immediately (no waiting for server)
   */
  _applySettingImmediately(key, value) {
    if (key === 'theme') {
      this._applyTheme(value);
    }
    // Other immediate effects can be added here
    // (e.g., muting audio, changing language in UI)
  }

  /**
   * Apply theme to the document
   */
  _applyTheme(theme) {
    const root = document.documentElement;
    root.removeAttribute('data-theme');
    if (theme === 'dark' || theme === 'light') {
      root.setAttribute('data-theme', theme);
    }
    // 'auto' removes the attribute, letting system preference take over
  }

  /**
   * Debounced save to server (300ms delay to batch rapid changes)
   */
  _debouncedSave() {
    if (this._saveTimeout) {
      clearTimeout(this._saveTimeout);
    }
    this._saveTimeout = setTimeout(() => this._saveToServer(), 300);
  }

  /**
   * Persist settings to server
   */
  async _saveToServer() {
    if (!this.apiClient) return;

    try {
      await this.apiClient.updateSettings(this.settings);
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  }

  /**
   * Reset all settings to defaults
   */
  async _resetSettings() {
    this.settings = { ...DEFAULT_SETTINGS };

    // Re-render the screen content
    if (this.element) {
      const parent = this.element.parentNode;
      const newElement = this.render({ settings: this.settings });
      if (parent) {
        parent.replaceChild(newElement, this.element);
      }
    }

    // Apply theme immediately
    this._applyTheme(DEFAULT_SETTINGS.theme);

    // Persist reset to server
    if (this.apiClient) {
      try {
        await this.apiClient.resetSettings();
      } catch (error) {
        console.error('Failed to reset settings on server:', error);
      }
    }
  }

  /**
   * Render a toggle switch
   */
  _renderToggle(key, label, checked) {
    return `
      <div class="settings-screen__toggle-row">
        <label class="settings-screen__toggle-label" for="toggle-${key}">${label}</label>
        <label class="settings-screen__toggle-switch">
          <input type="checkbox" id="toggle-${key}" class="settings-screen__toggle-input"
            data-key="${key}" ${checked ? 'checked' : ''} aria-label="${label}">
          <span class="settings-screen__toggle-slider"></span>
        </label>
      </div>
    `;
  }
}
