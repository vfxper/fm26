/**
 * HomeScreen.js - Dashboard with upcoming match, league position, recent results, notifications
 */

export class HomeScreen {
  constructor(options = {}) {
    this.apiClient = options.apiClient || null;
    this.onNavigate = options.onNavigate || null;
    this.element = null;
  }

  /**
   * Render the home dashboard
   * @param {Object} [data] - Pre-loaded data
   * @returns {HTMLElement}
   */
  render(data = {}) {
    const screen = document.createElement('div');
    screen.className = 'screen home-screen';
    screen.setAttribute('data-scrollable', '');

    screen.innerHTML = `
      <header class="screen__header">
        <h1 class="screen__title">Dashboard</h1>
      </header>

      <section class="home-screen__section" aria-label="Upcoming Match">
        <div class="card home-screen__match-card">
          <div class="card-header">Next Match</div>
          <div class="card-body home-screen__match-preview" id="home-next-match">
            <div class="home-screen__match-teams">
              <span class="home-screen__team home-screen__team--home">${data.nextMatch?.homeTeam || 'Your Team'}</span>
              <span class="home-screen__vs">vs</span>
              <span class="home-screen__team home-screen__team--away">${data.nextMatch?.awayTeam || 'Opponent'}</span>
            </div>
            <div class="home-screen__match-info">
              <span>${data.nextMatch?.competition || 'League'}</span>
              <span>${data.nextMatch?.date || 'Matchday 1'}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="home-screen__section" aria-label="League Position">
        <div class="card home-screen__league-card">
          <div class="card-header">League Standing</div>
          <div class="card-body">
            <div class="home-screen__standing">
              <div class="home-screen__position">${data.leaguePosition || '-'}</div>
              <div class="home-screen__standing-details">
                <span class="home-screen__stat">P: ${data.played || 0}</span>
                <span class="home-screen__stat">W: ${data.won || 0}</span>
                <span class="home-screen__stat">D: ${data.drawn || 0}</span>
                <span class="home-screen__stat">L: ${data.lost || 0}</span>
                <span class="home-screen__stat home-screen__stat--pts">Pts: ${data.points || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="home-screen__section" aria-label="Recent Results">
        <div class="card">
          <div class="card-header">Recent Results</div>
          <div class="card-body" id="home-recent-results">
            ${this._renderRecentResults(data.recentResults || [])}
          </div>
        </div>
      </section>

      <section class="home-screen__section" aria-label="Notifications">
        <div class="card">
          <div class="card-header">Notifications</div>
          <div class="card-body" id="home-notifications">
            ${this._renderNotifications(data.notifications || [])}
          </div>
        </div>
      </section>
    `;

    this.element = screen;
    return screen;
  }

  /**
   * Destroy and clean up
   */
  destroy() {
    this.element = null;
  }

  _renderRecentResults(results) {
    if (results.length === 0) {
      return '<p class="home-screen__empty">No recent results</p>';
    }
    return results
      .map(
        (r) => `
      <div class="home-screen__result">
        <span class="home-screen__result-teams">${r.home} ${r.homeScore}-${r.awayScore} ${r.away}</span>
        <span class="home-screen__result-badge home-screen__result-badge--${r.outcome}">${r.outcome[0].toUpperCase()}</span>
      </div>`
      )
      .join('');
  }

  _renderNotifications(notifications) {
    if (notifications.length === 0) {
      return '<p class="home-screen__empty">No new notifications</p>';
    }
    return notifications
      .map(
        (n) => `
      <div class="home-screen__notification">
        <span class="home-screen__notification-icon">${n.icon || '📢'}</span>
        <span class="home-screen__notification-text">${n.text}</span>
      </div>`
      )
      .join('');
  }
}
