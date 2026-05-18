/**
 * SquadScreen.js - Squad list with player cards, filters, sorting
 */

export class SquadScreen {
  constructor(options = {}) {
    this.apiClient = options.apiClient || null;
    this.onPlayerSelect = options.onPlayerSelect || null;
    this.element = null;
    this._sortField = 'position';
    this._sortDir = 'asc';
    this._filter = 'all';
  }

  /**
   * Render the squad management screen
   * @param {Object} [data]
   * @returns {HTMLElement}
   */
  render(data = {}) {
    const players = data.players || [];

    const screen = document.createElement('div');
    screen.className = 'screen squad-screen';
    screen.setAttribute('data-scrollable', '');

    screen.innerHTML = `
      <header class="screen__header">
        <h1 class="screen__title">Squad</h1>
        <span class="screen__subtitle">${players.length} players</span>
      </header>

      <div class="squad-screen__controls">
        <div class="squad-screen__filters" role="group" aria-label="Position filter">
          <button class="squad-screen__filter-btn squad-screen__filter-btn--active" data-filter="all">All</button>
          <button class="squad-screen__filter-btn" data-filter="GK">GK</button>
          <button class="squad-screen__filter-btn" data-filter="DEF">DEF</button>
          <button class="squad-screen__filter-btn" data-filter="MID">MID</button>
          <button class="squad-screen__filter-btn" data-filter="FWD">FWD</button>
        </div>
        <div class="squad-screen__sort">
          <select class="squad-screen__sort-select" aria-label="Sort players">
            <option value="position">Position</option>
            <option value="name">Name</option>
            <option value="ca">Ability</option>
            <option value="age">Age</option>
            <option value="morale">Morale</option>
          </select>
        </div>
      </div>

      <div class="squad-screen__list" id="squad-list" role="list" aria-label="Squad players">
        ${this._renderPlayerList(players)}
      </div>
    `;

    // Bind events
    this._bindEvents(screen, players);

    this.element = screen;
    return screen;
  }

  destroy() {
    this.element = null;
  }

  _renderPlayerList(players) {
    const filtered = this._applyFilter(players);
    const sorted = this._applySort(filtered);

    if (sorted.length === 0) {
      return '<p class="squad-screen__empty">No players found</p>';
    }

    return sorted
      .map(
        (p) => `
      <div class="squad-screen__player-card" role="listitem" data-player-id="${p.id}" tabindex="0" aria-label="${p.name}, ${p.position}">
        <div class="squad-screen__player-pos">${p.position || 'N/A'}</div>
        <div class="squad-screen__player-info">
          <span class="squad-screen__player-name">${p.name}</span>
          <span class="squad-screen__player-meta">${p.age || '?'} yrs · ${p.nationality || ''}</span>
        </div>
        <div class="squad-screen__player-rating">
          <span class="squad-screen__player-ca">${p.ca || '-'}</span>
        </div>
      </div>`
      )
      .join('');
  }

  _applyFilter(players) {
    if (this._filter === 'all') return players;
    return players.filter((p) => {
      const pos = (p.position || '').toUpperCase();
      switch (this._filter) {
        case 'GK': return pos.includes('GK');
        case 'DEF': return pos.includes('D');
        case 'MID': return pos.includes('M') || pos.includes('AM') || pos.includes('DM');
        case 'FWD': return pos.includes('ST') || pos.includes('F');
        default: return true;
      }
    });
  }

  _applySort(players) {
    const dir = this._sortDir === 'asc' ? 1 : -1;
    return [...players].sort((a, b) => {
      const aVal = a[this._sortField] ?? '';
      const bVal = b[this._sortField] ?? '';
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return (aVal - bVal) * dir;
      }
      return String(aVal).localeCompare(String(bVal)) * dir;
    });
  }

  _bindEvents(screen, players) {
    // Filter buttons
    const filterBtns = screen.querySelectorAll('.squad-screen__filter-btn');
    filterBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        filterBtns.forEach((b) => b.classList.remove('squad-screen__filter-btn--active'));
        btn.classList.add('squad-screen__filter-btn--active');
        this._filter = btn.dataset.filter;
        const list = screen.querySelector('#squad-list');
        list.innerHTML = this._renderPlayerList(players);
        this._bindPlayerCards(screen);
      });
    });

    // Sort select
    const sortSelect = screen.querySelector('.squad-screen__sort-select');
    if (sortSelect) {
      sortSelect.addEventListener('change', () => {
        this._sortField = sortSelect.value;
        const list = screen.querySelector('#squad-list');
        list.innerHTML = this._renderPlayerList(players);
        this._bindPlayerCards(screen);
      });
    }

    // Player cards
    this._bindPlayerCards(screen);
  }

  _bindPlayerCards(screen) {
    const cards = screen.querySelectorAll('.squad-screen__player-card');
    cards.forEach((card) => {
      card.addEventListener('click', () => {
        const playerId = card.dataset.playerId;
        if (this.onPlayerSelect) {
          this.onPlayerSelect(playerId);
        }
      });
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          card.click();
        }
      });
    });
  }
}
