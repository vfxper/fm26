/**
 * TransfersScreen.js - Transfer market, shortlist, budget
 */

export class TransfersScreen {
  constructor(options = {}) {
    this.apiClient = options.apiClient || null;
    this.onPlayerSelect = options.onPlayerSelect || null;
    this.onBid = options.onBid || null;
    this.element = null;
    this._activeTab = 'market';
  }

  /**
   * Render the transfers screen
   * @param {Object} [data]
   * @returns {HTMLElement}
   */
  render(data = {}) {
    const screen = document.createElement('div');
    screen.className = 'screen transfers-screen';
    screen.setAttribute('data-scrollable', '');

    screen.innerHTML = `
      <header class="screen__header">
        <h1 class="screen__title">Transfers</h1>
      </header>

      <section class="transfers-screen__budget" aria-label="Transfer budget">
        <div class="card">
          <div class="card-body transfers-screen__budget-row">
            <div class="transfers-screen__budget-item">
              <span class="transfers-screen__budget-label">Budget</span>
              <span class="transfers-screen__budget-value">${this._formatMoney(data.budget || 0)}</span>
            </div>
            <div class="transfers-screen__budget-item">
              <span class="transfers-screen__budget-label">Wage Budget</span>
              <span class="transfers-screen__budget-value">${this._formatMoney(data.wageBudget || 0)}/wk</span>
            </div>
            <div class="transfers-screen__budget-item">
              <span class="transfers-screen__budget-label">Window</span>
              <span class="transfers-screen__budget-value transfers-screen__budget-value--${data.windowOpen ? 'open' : 'closed'}">
                ${data.windowOpen ? 'Open' : 'Closed'}
              </span>
            </div>
          </div>
        </div>
      </section>

      <div class="transfers-screen__tabs" role="tablist" aria-label="Transfer sections">
        <button class="transfers-screen__tab transfers-screen__tab--active" role="tab" data-tab="market" aria-selected="true">Market</button>
        <button class="transfers-screen__tab" role="tab" data-tab="shortlist" aria-selected="false">Shortlist</button>
        <button class="transfers-screen__tab" role="tab" data-tab="history" aria-selected="false">History</button>
      </div>

      <div class="transfers-screen__content" id="transfers-content">
        ${this._renderMarket(data.market || [])}
      </div>
    `;

    this._bindEvents(screen, data);
    this.element = screen;
    return screen;
  }

  destroy() {
    this.element = null;
  }

  _renderMarket(players) {
    if (players.length === 0) {
      return `
        <div class="transfers-screen__empty">
          <p>No players available</p>
          <p class="transfers-screen__hint">Use search to find transfer targets</p>
        </div>`;
    }
    return `
      <div class="transfers-screen__list" role="list">
        ${players.map((p) => this._renderPlayerRow(p)).join('')}
      </div>`;
  }

  _renderShortlist(players) {
    if (players.length === 0) {
      return '<div class="transfers-screen__empty"><p>Shortlist is empty</p></div>';
    }
    return `
      <div class="transfers-screen__list" role="list">
        ${players.map((p) => this._renderPlayerRow(p, true)).join('')}
      </div>`;
  }

  _renderHistory(transfers) {
    if (transfers.length === 0) {
      return '<div class="transfers-screen__empty"><p>No transfer history</p></div>';
    }
    return `
      <div class="transfers-screen__list" role="list">
        ${transfers
          .map(
            (t) => `
          <div class="transfers-screen__history-item" role="listitem">
            <div class="transfers-screen__history-player">${t.playerName}</div>
            <div class="transfers-screen__history-details">
              <span>${t.type === 'buy' ? '← Bought' : '→ Sold'}</span>
              <span>${this._formatMoney(t.fee)}</span>
            </div>
          </div>`
          )
          .join('')}
      </div>`;
  }

  _renderPlayerRow(player, showBidBtn = false) {
    return `
      <div class="transfers-screen__player-row" role="listitem" data-player-id="${player.id}" tabindex="0">
        <div class="transfers-screen__player-info">
          <span class="transfers-screen__player-name">${player.name}</span>
          <span class="transfers-screen__player-meta">${player.position} · ${player.age} · ${player.club || 'Free'}</span>
        </div>
        <div class="transfers-screen__player-value">
          <span>${this._formatMoney(player.value || 0)}</span>
          ${showBidBtn ? '<button class="btn btn-small transfers-screen__bid-btn" data-player-id="' + player.id + '">Bid</button>' : ''}
        </div>
      </div>`;
  }

  _formatMoney(amount) {
    if (amount >= 1_000_000) return `£${(amount / 1_000_000).toFixed(1)}M`;
    if (amount >= 1_000) return `£${(amount / 1_000).toFixed(0)}K`;
    return `£${amount}`;
  }

  _bindEvents(screen, data) {
    // Tab switching
    const tabs = screen.querySelectorAll('.transfers-screen__tab');
    tabs.forEach((tab) => {
      tab.addEventListener('click', () => {
        tabs.forEach((t) => {
          t.classList.remove('transfers-screen__tab--active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('transfers-screen__tab--active');
        tab.setAttribute('aria-selected', 'true');

        const tabId = tab.dataset.tab;
        this._activeTab = tabId;
        const content = screen.querySelector('#transfers-content');

        switch (tabId) {
          case 'market':
            content.innerHTML = this._renderMarket(data.market || []);
            break;
          case 'shortlist':
            content.innerHTML = this._renderShortlist(data.shortlist || []);
            break;
          case 'history':
            content.innerHTML = this._renderHistory(data.history || []);
            break;
        }
        this._bindContentEvents(screen);
      });
    });

    this._bindContentEvents(screen);
  }

  _bindContentEvents(screen) {
    // Player row clicks
    const rows = screen.querySelectorAll('.transfers-screen__player-row');
    rows.forEach((row) => {
      row.addEventListener('click', (e) => {
        if (e.target.closest('.transfers-screen__bid-btn')) return;
        if (this.onPlayerSelect) {
          this.onPlayerSelect(row.dataset.playerId);
        }
      });
    });

    // Bid buttons
    const bidBtns = screen.querySelectorAll('.transfers-screen__bid-btn');
    bidBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        if (this.onBid) {
          this.onBid(btn.dataset.playerId);
        }
      });
    });
  }
}
