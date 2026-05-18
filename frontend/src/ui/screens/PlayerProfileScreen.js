/**
 * PlayerProfileScreen.js - Full player profile with all 18 sub-features
 * 21.16.1  Player name, age, nationality, position
 * 21.16.2  Player photo/avatar placeholder
 * 21.16.3  Current Ability (CA) display
 * 21.16.4  Potential Ability (PA) display (if scouted)
 * 21.16.5  Technical attributes section
 * 21.16.6  Mental attributes section
 * 21.16.7  Physical attributes section
 * 21.16.8  Attribute bars (1-20 scale with color coding)
 * 21.16.9  Radar chart for attribute visualization
 * 21.16.10 Contract information (expiry, wage, clause)
 * 21.16.11 Player form/morale indicator
 * 21.16.12 Injury status display
 * 21.16.13 Match statistics summary
 * 21.16.14 Transfer history
 * 21.16.15 Player traits/characteristics
 * 21.16.16 Action buttons (offer contract, transfer list, etc.)
 * 21.16.17 Comparison mode toggle
 * 21.16.18 Player development history chart
 */

import { AttributeBar } from '../components/AttributeBar.js';
import { RadarChart } from '../components/RadarChart.js';

export class PlayerProfileScreen {
  constructor(options = {}) {
    this.apiClient = options.apiClient || null;
    this.onAction = options.onAction || null;
    this.onBack = options.onBack || null;
    this.element = null;
    this._comparisonMode = false;
  }

  /**
   * Render the player profile
   * @param {Object} data - Player data
   * @returns {HTMLElement}
   */
  render(data = {}) {
    const player = data.player || {};

    const screen = document.createElement('div');
    screen.className = 'screen player-profile-screen';
    screen.setAttribute('data-scrollable', '');

    screen.innerHTML = `
      <header class="screen__header player-profile-screen__header">
        <button class="player-profile-screen__back-btn" aria-label="Go back">←</button>
        <h1 class="screen__title">${player.name || 'Player'}</h1>
        <button class="player-profile-screen__compare-btn" aria-label="Toggle comparison mode">⇄</button>
      </header>

      <!-- 21.16.1 & 21.16.2: Identity section -->
      <section class="player-profile-screen__identity" aria-label="Player identity">
        <div class="player-profile-screen__avatar" aria-hidden="true">
          <div class="player-profile-screen__avatar-placeholder">${(player.name || 'P')[0]}</div>
        </div>
        <div class="player-profile-screen__identity-info">
          <h2 class="player-profile-screen__name">${player.name || 'Unknown'}</h2>
          <p class="player-profile-screen__meta">
            ${player.age || '?'} yrs · ${player.nationality || 'Unknown'} · ${player.position || 'N/A'}
          </p>
          <p class="player-profile-screen__club">${player.club || 'Free Agent'}</p>
        </div>
      </section>

      <!-- 21.16.3 & 21.16.4: Ability section -->
      <section class="player-profile-screen__ability" aria-label="Player ability">
        <div class="player-profile-screen__ability-item">
          <span class="player-profile-screen__ability-label">CA</span>
          <span class="player-profile-screen__ability-value">${player.ca ?? '-'}</span>
        </div>
        ${player.pa != null ? `
        <div class="player-profile-screen__ability-item">
          <span class="player-profile-screen__ability-label">PA</span>
          <span class="player-profile-screen__ability-value player-profile-screen__ability-value--pa">${player.pa}</span>
        </div>` : `
        <div class="player-profile-screen__ability-item player-profile-screen__ability-item--hidden">
          <span class="player-profile-screen__ability-label">PA</span>
          <span class="player-profile-screen__ability-value">?</span>
        </div>`}
      </section>

      <!-- 21.16.11: Form/Morale -->
      ${this._renderFormMorale(player)}

      <!-- 21.16.12: Injury status -->
      ${this._renderInjuryStatus(player)}

      <!-- 21.16.9: Radar chart -->
      <section class="player-profile-screen__radar" aria-label="Attribute radar chart">
        <div class="card">
          <div class="card-header">Attribute Overview</div>
          <div class="card-body">
            <canvas id="player-radar-chart" width="280" height="280" aria-label="Radar chart showing player attributes"></canvas>
          </div>
        </div>
      </section>

      <!-- 21.16.5: Technical attributes -->
      <section class="player-profile-screen__attributes" aria-label="Technical attributes">
        <div class="card">
          <div class="card-header">Technical</div>
          <div class="card-body player-profile-screen__attr-grid" id="attrs-technical">
          </div>
        </div>
      </section>

      <!-- 21.16.6: Mental attributes -->
      <section class="player-profile-screen__attributes" aria-label="Mental attributes">
        <div class="card">
          <div class="card-header">Mental</div>
          <div class="card-body player-profile-screen__attr-grid" id="attrs-mental">
          </div>
        </div>
      </section>

      <!-- 21.16.7: Physical attributes -->
      <section class="player-profile-screen__attributes" aria-label="Physical attributes">
        <div class="card">
          <div class="card-header">Physical</div>
          <div class="card-body player-profile-screen__attr-grid" id="attrs-physical">
          </div>
        </div>
      </section>

      <!-- 21.16.10: Contract information -->
      ${this._renderContract(player)}

      <!-- 21.16.13: Match statistics -->
      ${this._renderMatchStats(player)}

      <!-- 21.16.14: Transfer history -->
      ${this._renderTransferHistory(player)}

      <!-- 21.16.15: Traits -->
      ${this._renderTraits(player)}

      <!-- 21.16.18: Development history -->
      ${this._renderDevelopmentHistory(player)}

      <!-- 21.16.16: Action buttons -->
      <section class="player-profile-screen__actions" aria-label="Player actions">
        <div class="player-profile-screen__action-grid">
          <button class="btn player-profile-screen__action-btn" data-action="offer-contract">Offer Contract</button>
          <button class="btn btn-secondary player-profile-screen__action-btn" data-action="transfer-list">Transfer List</button>
          <button class="btn btn-secondary player-profile-screen__action-btn" data-action="loan-list">Loan List</button>
          <button class="btn btn-secondary player-profile-screen__action-btn" data-action="interact">Interact</button>
        </div>
      </section>
    `;

    this._bindEvents(screen, player);

    // Render attribute bars and radar chart after DOM insertion
    requestAnimationFrame(() => {
      this._renderAttributeBars(screen, player);
      this._renderRadarChart(screen, player);
    });

    this.element = screen;
    return screen;
  }

  destroy() {
    this.element = null;
  }

  // --- Sections ---

  _renderFormMorale(player) {
    const morale = player.morale ?? null;
    if (morale == null) return '';
    const moraleClass = morale >= 70 ? 'high' : morale >= 40 ? 'medium' : 'low';
    return `
      <section class="player-profile-screen__morale" aria-label="Player morale">
        <div class="player-profile-screen__morale-bar">
          <span class="player-profile-screen__morale-label">Morale</span>
          <div class="player-profile-screen__morale-track">
            <div class="player-profile-screen__morale-fill player-profile-screen__morale-fill--${moraleClass}" style="width:${morale}%"></div>
          </div>
          <span class="player-profile-screen__morale-value">${morale}</span>
        </div>
      </section>`;
  }

  _renderInjuryStatus(player) {
    if (!player.injury) return '';
    return `
      <section class="player-profile-screen__injury" aria-label="Injury status">
        <div class="card player-profile-screen__injury-card">
          <span class="player-profile-screen__injury-icon">🏥</span>
          <div class="player-profile-screen__injury-info">
            <span class="player-profile-screen__injury-type">${player.injury.type}</span>
            <span class="player-profile-screen__injury-return">Return: ${player.injury.returnDate || 'Unknown'}</span>
          </div>
        </div>
      </section>`;
  }

  _renderContract(player) {
    const contract = player.contract || {};
    return `
      <section class="player-profile-screen__contract" aria-label="Contract information">
        <div class="card">
          <div class="card-header">Contract</div>
          <div class="card-body">
            <div class="player-profile-screen__contract-grid">
              <div class="player-profile-screen__contract-item">
                <span class="player-profile-screen__contract-label">Expiry</span>
                <span class="player-profile-screen__contract-value">${contract.expiry || 'N/A'}</span>
              </div>
              <div class="player-profile-screen__contract-item">
                <span class="player-profile-screen__contract-label">Wage</span>
                <span class="player-profile-screen__contract-value">${contract.wage ? '£' + contract.wage.toLocaleString() + '/wk' : 'N/A'}</span>
              </div>
              <div class="player-profile-screen__contract-item">
                <span class="player-profile-screen__contract-label">Release Clause</span>
                <span class="player-profile-screen__contract-value">${contract.releaseClause ? '£' + contract.releaseClause.toLocaleString() : 'None'}</span>
              </div>
            </div>
          </div>
        </div>
      </section>`;
  }

  _renderMatchStats(player) {
    const stats = player.stats || {};
    return `
      <section class="player-profile-screen__stats" aria-label="Match statistics">
        <div class="card">
          <div class="card-header">Season Stats</div>
          <div class="card-body">
            <div class="player-profile-screen__stats-grid">
              <div class="player-profile-screen__stat-item">
                <span class="player-profile-screen__stat-value">${stats.appearances ?? 0}</span>
                <span class="player-profile-screen__stat-label">Apps</span>
              </div>
              <div class="player-profile-screen__stat-item">
                <span class="player-profile-screen__stat-value">${stats.goals ?? 0}</span>
                <span class="player-profile-screen__stat-label">Goals</span>
              </div>
              <div class="player-profile-screen__stat-item">
                <span class="player-profile-screen__stat-value">${stats.assists ?? 0}</span>
                <span class="player-profile-screen__stat-label">Assists</span>
              </div>
              <div class="player-profile-screen__stat-item">
                <span class="player-profile-screen__stat-value">${stats.avgRating ? stats.avgRating.toFixed(1) : '-'}</span>
                <span class="player-profile-screen__stat-label">Avg Rating</span>
              </div>
            </div>
          </div>
        </div>
      </section>`;
  }

  _renderTransferHistory(player) {
    const history = player.transferHistory || [];
    if (history.length === 0) return '';
    return `
      <section class="player-profile-screen__transfer-history" aria-label="Transfer history">
        <div class="card">
          <div class="card-header">Transfer History</div>
          <div class="card-body">
            ${history
              .map(
                (t) => `
              <div class="player-profile-screen__transfer-row">
                <span class="player-profile-screen__transfer-clubs">${t.from} → ${t.to}</span>
                <span class="player-profile-screen__transfer-fee">${t.fee ? '£' + t.fee.toLocaleString() : 'Free'}</span>
              </div>`
              )
              .join('')}
          </div>
        </div>
      </section>`;
  }

  _renderTraits(player) {
    const traits = player.traits ? player.traits.split(',').map((t) => t.trim()).filter(Boolean) : [];
    if (traits.length === 0) return '';
    return `
      <section class="player-profile-screen__traits" aria-label="Player traits">
        <div class="card">
          <div class="card-header">Traits</div>
          <div class="card-body">
            <div class="player-profile-screen__traits-list">
              ${traits.map((t) => `<span class="player-profile-screen__trait-tag">${t}</span>`).join('')}
            </div>
          </div>
        </div>
      </section>`;
  }

  _renderDevelopmentHistory(player) {
    const history = player.developmentHistory || [];
    if (history.length === 0) return '';
    return `
      <section class="player-profile-screen__development" aria-label="Development history">
        <div class="card">
          <div class="card-header">Development</div>
          <div class="card-body">
            <div class="player-profile-screen__dev-chart" id="dev-history-chart">
              ${history
                .map(
                  (h) => `
                <div class="player-profile-screen__dev-point">
                  <span class="player-profile-screen__dev-season">${h.season}</span>
                  <span class="player-profile-screen__dev-ca">${h.ca}</span>
                </div>`
                )
                .join('')}
            </div>
          </div>
        </div>
      </section>`;
  }

  // --- Attribute rendering ---

  _renderAttributeBars(screen, player) {
    const technical = {
      Corners: player.corners, Crossing: player.crossing, Dribbling: player.dribbling,
      Finishing: player.finishing, 'First Touch': player.first_touch, 'Free Kicks': player.free_kicks,
      Heading: player.heading, 'Long Shots': player.long_shots, Marking: player.marking,
      Passing: player.passing, Penalty: player.penalty, Tackling: player.tackling, Technique: player.technique,
    };

    const mental = {
      Aggression: player.aggression, Anticipation: player.anticipation, Bravery: player.bravery,
      Composure: player.composure, Concentration: player.concentration, Decisions: player.decisions,
      Determination: player.determination, Flair: player.flair, Leadership: player.leadership,
      'Off the Ball': player.off_the_ball, Positioning: player.positioning, Teamwork: player.teamwork,
      Vision: player.vision, 'Work Rate': player.work_rate,
    };

    const physical = {
      Acceleration: player.acceleration, Agility: player.agility, Balance: player.balance,
      Jumping: player.jumping, Stamina: player.stamina, Pace: player.pace,
      Strength: player.strength,
    };

    this._fillAttrContainer(screen.querySelector('#attrs-technical'), technical);
    this._fillAttrContainer(screen.querySelector('#attrs-mental'), mental);
    this._fillAttrContainer(screen.querySelector('#attrs-physical'), physical);
  }

  _fillAttrContainer(container, attrs) {
    if (!container) return;
    container.innerHTML = '';
    Object.entries(attrs).forEach(([name, value]) => {
      const bar = new AttributeBar({ name, value: value ?? 0, max: 20 });
      container.appendChild(bar.render());
    });
  }

  _renderRadarChart(screen, player) {
    const canvas = screen.querySelector('#player-radar-chart');
    if (!canvas) return;

    const radarData = {
      labels: ['Pace', 'Shooting', 'Passing', 'Dribbling', 'Defending', 'Physical'],
      values: [
        Math.round(((player.pace || 0) + (player.acceleration || 0)) / 2),
        Math.round(((player.finishing || 0) + (player.long_shots || 0)) / 2),
        Math.round(((player.passing || 0) + (player.vision || 0)) / 2),
        Math.round(((player.dribbling || 0) + (player.technique || 0)) / 2),
        Math.round(((player.tackling || 0) + (player.marking || 0)) / 2),
        Math.round(((player.strength || 0) + (player.stamina || 0)) / 2),
      ],
      max: 20,
    };

    const chart = new RadarChart(canvas, radarData);
    chart.draw();
  }

  // --- Events ---

  _bindEvents(screen, player) {
    // Back button
    const backBtn = screen.querySelector('.player-profile-screen__back-btn');
    if (backBtn) {
      backBtn.addEventListener('click', () => {
        if (this.onBack) this.onBack();
      });
    }

    // Compare button (21.16.17)
    const compareBtn = screen.querySelector('.player-profile-screen__compare-btn');
    if (compareBtn) {
      compareBtn.addEventListener('click', () => {
        this._comparisonMode = !this._comparisonMode;
        compareBtn.classList.toggle('player-profile-screen__compare-btn--active', this._comparisonMode);
      });
    }

    // Action buttons (21.16.16)
    const actionBtns = screen.querySelectorAll('.player-profile-screen__action-btn');
    actionBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        if (this.onAction) {
          this.onAction(btn.dataset.action, player);
        }
      });
    });
  }
}
