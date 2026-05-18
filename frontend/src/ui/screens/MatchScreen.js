/**
 * MatchScreen.js - Match viewer integration with canvas renderer
 */

export class MatchScreen {
  constructor(options = {}) {
    this.apiClient = options.apiClient || null;
    this.matchRenderer = options.matchRenderer || null;
    this.onStartMatch = options.onStartMatch || null;
    this.element = null;
  }

  /**
   * Render the match screen
   * @param {Object} [data]
   * @returns {HTMLElement}
   */
  render(data = {}) {
    const screen = document.createElement('div');
    screen.className = 'screen match-screen';
    screen.setAttribute('data-scrollable', '');

    const hasActiveMatch = data.activeMatch != null;

    screen.innerHTML = `
      <header class="screen__header">
        <h1 class="screen__title">Match</h1>
      </header>

      ${hasActiveMatch ? this._renderActiveMatch(data.activeMatch) : this._renderUpcoming(data)}
    `;

    this._bindEvents(screen, data);
    this.element = screen;
    return screen;
  }

  destroy() {
    this.element = null;
  }

  _renderActiveMatch(match) {
    return `
      <section class="match-screen__live">
        <div class="match-screen__scoreboard">
          <div class="match-screen__team-name">${match.homeTeam}</div>
          <div class="match-screen__score">${match.homeScore ?? 0} - ${match.awayScore ?? 0}</div>
          <div class="match-screen__team-name">${match.awayTeam}</div>
        </div>
        <div class="match-screen__time">${match.minute ?? 0}'</div>
        <div class="match-screen__canvas-container">
          <canvas id="match-live-canvas" class="match-screen__canvas" aria-label="Live match view"></canvas>
        </div>
        <div class="match-screen__controls">
          <button class="btn btn-small match-screen__speed-btn" data-speed="1" aria-label="1x speed">1x</button>
          <button class="btn btn-small match-screen__speed-btn" data-speed="2" aria-label="2x speed">2x</button>
          <button class="btn btn-small match-screen__speed-btn" data-speed="4" aria-label="4x speed">4x</button>
          <button class="btn btn-small match-screen__speed-btn" data-speed="0" aria-label="Instant">⏩</button>
          <button class="btn btn-small match-screen__pause-btn" aria-label="Pause match">⏸</button>
        </div>
        <div class="match-screen__commentary" id="match-commentary" aria-live="polite" aria-label="Match commentary">
        </div>
      </section>
    `;
  }

  _renderUpcoming(data) {
    const upcoming = data.upcomingMatches || [];
    return `
      <section class="match-screen__upcoming">
        <div class="card">
          <div class="card-header">Upcoming Matches</div>
          <div class="card-body">
            ${upcoming.length === 0
              ? '<p class="match-screen__empty">No upcoming matches</p>'
              : upcoming
                  .map(
                    (m) => `
                <div class="match-screen__fixture" data-match-id="${m.id}">
                  <div class="match-screen__fixture-teams">
                    <span>${m.homeTeam}</span>
                    <span class="match-screen__fixture-vs">vs</span>
                    <span>${m.awayTeam}</span>
                  </div>
                  <div class="match-screen__fixture-info">
                    <span>${m.competition}</span>
                    <span>${m.date}</span>
                  </div>
                  ${m.isNext ? '<button class="btn match-screen__play-btn" data-match-id="' + m.id + '">Play Match</button>' : ''}
                </div>`
                  )
                  .join('')}
          </div>
        </div>
      </section>

      <section class="match-screen__results">
        <div class="card">
          <div class="card-header">Recent Results</div>
          <div class="card-body">
            ${(data.recentResults || []).length === 0
              ? '<p class="match-screen__empty">No results yet</p>'
              : (data.recentResults || [])
                  .map(
                    (r) => `
                <div class="match-screen__result-row">
                  <span>${r.homeTeam} ${r.homeScore}-${r.awayScore} ${r.awayTeam}</span>
                </div>`
                  )
                  .join('')}
          </div>
        </div>
      </section>
    `;
  }

  _bindEvents(screen, data) {
    // Play match button
    const playBtns = screen.querySelectorAll('.match-screen__play-btn');
    playBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        if (this.onStartMatch) {
          this.onStartMatch(btn.dataset.matchId);
        }
      });
    });

    // Speed buttons
    const speedBtns = screen.querySelectorAll('.match-screen__speed-btn');
    speedBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        speedBtns.forEach((b) => b.classList.remove('match-screen__speed-btn--active'));
        btn.classList.add('match-screen__speed-btn--active');
        if (this.matchRenderer) {
          this.matchRenderer.setSpeed(parseInt(btn.dataset.speed, 10));
        }
      });
    });

    // Pause button
    const pauseBtn = screen.querySelector('.match-screen__pause-btn');
    if (pauseBtn) {
      pauseBtn.addEventListener('click', () => {
        if (this.matchRenderer) {
          this.matchRenderer.togglePause();
          pauseBtn.textContent = this.matchRenderer.isPaused ? '▶' : '⏸';
        }
      });
    }
  }
}
