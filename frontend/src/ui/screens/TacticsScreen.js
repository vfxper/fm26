/**
 * TacticsScreen.js - Formation display, tactic settings
 */

const FORMATIONS = [
  '4-4-2', '4-3-3', '4-2-3-1', '3-5-2', '5-3-2',
  '4-5-1', '3-4-3', '4-1-4-1', '4-3-2-1', '5-4-1',
  '3-6-1', '4-4-1-1', '4-2-2-2', '3-4-1-2', '4-3-1-2',
];

const MENTALITIES = ['Defensive', 'Cautious', 'Balanced', 'Positive', 'Attacking', 'Very Attacking'];
const PRESSING = ['Low', 'Medium', 'High', 'Gegenpressing'];
const LINE_HEIGHT = ['Deep', 'Standard', 'High', 'Very High'];
const WIDTH = ['Narrow', 'Standard', 'Wide'];
const TEMPO = ['Slow', 'Standard', 'Fast'];

export class TacticsScreen {
  constructor(options = {}) {
    this.apiClient = options.apiClient || null;
    this.onSave = options.onSave || null;
    this.element = null;
  }

  /**
   * Render the tactics screen
   * @param {Object} [data]
   * @returns {HTMLElement}
   */
  render(data = {}) {
    const tactic = data.tactic || {};

    const screen = document.createElement('div');
    screen.className = 'screen tactics-screen';
    screen.setAttribute('data-scrollable', '');

    screen.innerHTML = `
      <header class="screen__header">
        <h1 class="screen__title">Tactics</h1>
      </header>

      <section class="tactics-screen__formation-section">
        <div class="card">
          <div class="card-header">Formation</div>
          <div class="card-body">
            <div class="tactics-screen__pitch" id="tactics-pitch" aria-label="Formation pitch view">
              <canvas id="tactics-canvas" width="300" height="400"></canvas>
            </div>
            <div class="tactics-screen__formation-select">
              <select class="input" id="formation-select" aria-label="Select formation">
                ${FORMATIONS.map((f) => `<option value="${f}" ${f === tactic.formation ? 'selected' : ''}>${f}</option>`).join('')}
              </select>
            </div>
          </div>
        </div>
      </section>

      <section class="tactics-screen__settings-section">
        <div class="card">
          <div class="card-header">Team Instructions</div>
          <div class="card-body">
            ${this._renderSetting('Mentality', 'mentality', MENTALITIES, tactic.mentality || 'Balanced')}
            ${this._renderSetting('Pressing', 'pressing', PRESSING, tactic.pressing || 'Medium')}
            ${this._renderSetting('Defensive Line', 'line_height', LINE_HEIGHT, tactic.line_height || 'Standard')}
            ${this._renderSetting('Width', 'width', WIDTH, tactic.width || 'Standard')}
            ${this._renderSetting('Tempo', 'tempo', TEMPO, tactic.tempo || 'Standard')}
          </div>
        </div>
      </section>

      <section class="tactics-screen__presets-section">
        <div class="card">
          <div class="card-header">Tactic Presets</div>
          <div class="card-body">
            <div class="tactics-screen__presets" id="tactic-presets">
              ${this._renderPresets(data.presets || [])}
            </div>
            <button class="btn tactics-screen__save-btn" id="save-tactic-btn" aria-label="Save current tactic">
              Save Tactic
            </button>
          </div>
        </div>
      </section>
    `;

    this._bindEvents(screen);
    this.element = screen;

    // Draw formation on canvas after render
    requestAnimationFrame(() => this._drawFormation(tactic.formation || '4-4-2'));

    return screen;
  }

  destroy() {
    this.element = null;
  }

  _renderSetting(label, id, options, current) {
    return `
      <div class="tactics-screen__setting">
        <label class="tactics-screen__setting-label" for="tactic-${id}">${label}</label>
        <select class="input tactics-screen__setting-select" id="tactic-${id}" aria-label="${label}">
          ${options.map((o) => `<option value="${o}" ${o === current ? 'selected' : ''}>${o}</option>`).join('')}
        </select>
      </div>
    `;
  }

  _renderPresets(presets) {
    if (presets.length === 0) {
      return '<p class="tactics-screen__empty">No saved presets</p>';
    }
    return presets
      .map(
        (p) => `
      <button class="btn btn-secondary tactics-screen__preset-btn" data-preset-id="${p.id}">
        ${p.name}
      </button>`
      )
      .join('');
  }

  _bindEvents(screen) {
    const formationSelect = screen.querySelector('#formation-select');
    if (formationSelect) {
      formationSelect.addEventListener('change', () => {
        this._drawFormation(formationSelect.value);
      });
    }

    const saveBtn = screen.querySelector('#save-tactic-btn');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => {
        if (this.onSave) {
          this.onSave(this._collectTacticData(screen));
        }
      });
    }
  }

  _collectTacticData(screen) {
    return {
      formation: screen.querySelector('#formation-select')?.value,
      mentality: screen.querySelector('#tactic-mentality')?.value,
      pressing: screen.querySelector('#tactic-pressing')?.value,
      line_height: screen.querySelector('#tactic-line_height')?.value,
      width: screen.querySelector('#tactic-width')?.value,
      tempo: screen.querySelector('#tactic-tempo')?.value,
    };
  }

  _drawFormation(formation) {
    const canvas = this.element?.querySelector('#tactics-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Draw pitch background
    ctx.fillStyle = 'var(--pitch-green, #2d5016)';
    ctx.fillStyle = '#2d5016';
    ctx.fillRect(0, 0, w, h);

    // Draw pitch lines
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.lineWidth = 1;
    ctx.strokeRect(10, 10, w - 20, h - 20);
    ctx.beginPath();
    ctx.moveTo(10, h / 2);
    ctx.lineTo(w - 10, h / 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, 30, 0, Math.PI * 2);
    ctx.stroke();

    // Parse formation and draw player positions
    const positions = this._getFormationPositions(formation, w, h);
    positions.forEach((pos) => {
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#2d5016';
      ctx.font = '9px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(pos.label, pos.x, pos.y);
    });
  }

  _getFormationPositions(formation, w, h) {
    const parts = formation.split('-').map(Number);
    const positions = [];
    const margin = 30;
    const usableH = h - margin * 2;

    // GK always at bottom
    positions.push({ x: w / 2, y: h - margin, label: 'GK' });

    // Distribute lines from back to front
    const totalLines = parts.length;
    parts.forEach((count, lineIdx) => {
      const y = h - margin - ((lineIdx + 1) / (totalLines + 1)) * usableH;
      for (let i = 0; i < count; i++) {
        const x = margin + ((i + 1) / (count + 1)) * (w - margin * 2);
        positions.push({ x, y, label: '' });
      }
    });

    return positions;
  }
}
