/**
 * SearchBar.js - Global search with autocomplete
 */

export class SearchBar {
  /**
   * @param {Object} options
   * @param {Function} options.onSearch - Callback with search query
   * @param {Function} [options.onSelect] - Callback when result is selected
   * @param {string} [options.placeholder] - Input placeholder text
   * @param {number} [options.debounceMs=300] - Debounce delay
   */
  constructor(options = {}) {
    this.onSearch = options.onSearch || null;
    this.onSelect = options.onSelect || null;
    this.placeholder = options.placeholder || 'Search players, staff, competitions...';
    this.debounceMs = options.debounceMs ?? 300;
    this.element = null;
    this._results = [];
    this._debounceTimer = null;
    this._isOpen = false;
    this._selectedIndex = -1;
  }

  /**
   * Render the search bar
   * @returns {HTMLElement}
   */
  render() {
    const wrapper = document.createElement('div');
    wrapper.className = 'search-bar';
    wrapper.setAttribute('role', 'combobox');
    wrapper.setAttribute('aria-expanded', 'false');
    wrapper.setAttribute('aria-haspopup', 'listbox');

    wrapper.innerHTML = `
      <div class="search-bar__input-wrapper">
        <span class="search-bar__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
        </span>
        <input
          type="search"
          class="search-bar__input"
          placeholder="${this.placeholder}"
          aria-label="Search"
          aria-autocomplete="list"
          aria-controls="search-results"
          autocomplete="off"
        />
        <button class="search-bar__clear hidden" aria-label="Clear search" type="button">✕</button>
      </div>
      <ul class="search-bar__results hidden" id="search-results" role="listbox" aria-label="Search results"></ul>
    `;

    this._bindEvents(wrapper);
    this.element = wrapper;
    return wrapper;
  }

  /**
   * Set search results
   * @param {Array<{id: string, text: string, subtitle?: string, icon?: string}>} results
   */
  setResults(results) {
    this._results = results;
    this._selectedIndex = -1;
    this._renderResults();
  }

  /**
   * Clear the search
   */
  clear() {
    if (!this.element) return;
    const input = this.element.querySelector('.search-bar__input');
    if (input) input.value = '';
    this._results = [];
    this._closeDropdown();
  }

  /**
   * Focus the input
   */
  focus() {
    const input = this.element?.querySelector('.search-bar__input');
    if (input) input.focus();
  }

  destroy() {
    if (this._debounceTimer) clearTimeout(this._debounceTimer);
    this.element = null;
  }

  // --- Private ---

  _bindEvents(wrapper) {
    const input = wrapper.querySelector('.search-bar__input');
    const clearBtn = wrapper.querySelector('.search-bar__clear');

    input.addEventListener('input', () => {
      const query = input.value.trim();
      clearBtn.classList.toggle('hidden', query.length === 0);

      if (this._debounceTimer) clearTimeout(this._debounceTimer);

      if (query.length < 2) {
        this._closeDropdown();
        return;
      }

      this._debounceTimer = setTimeout(() => {
        if (this.onSearch) this.onSearch(query);
      }, this.debounceMs);
    });

    input.addEventListener('keydown', (e) => {
      if (!this._isOpen) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          this._moveSelection(1);
          break;
        case 'ArrowUp':
          e.preventDefault();
          this._moveSelection(-1);
          break;
        case 'Enter':
          e.preventDefault();
          if (this._selectedIndex >= 0 && this._results[this._selectedIndex]) {
            this._selectResult(this._results[this._selectedIndex]);
          }
          break;
        case 'Escape':
          this._closeDropdown();
          break;
      }
    });

    input.addEventListener('focus', () => {
      if (this._results.length > 0) this._openDropdown();
    });

    clearBtn.addEventListener('click', () => {
      input.value = '';
      clearBtn.classList.add('hidden');
      this._results = [];
      this._closeDropdown();
      input.focus();
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!wrapper.contains(e.target)) {
        this._closeDropdown();
      }
    });
  }

  _renderResults() {
    if (!this.element) return;
    const list = this.element.querySelector('.search-bar__results');
    if (!list) return;

    if (this._results.length === 0) {
      list.innerHTML = '<li class="search-bar__no-results">No results found</li>';
      this._openDropdown();
      return;
    }

    list.innerHTML = this._results
      .map(
        (r, i) => `
      <li class="search-bar__result-item${i === this._selectedIndex ? ' search-bar__result-item--selected' : ''}"
          role="option"
          data-index="${i}"
          aria-selected="${i === this._selectedIndex}">
        ${r.icon ? `<span class="search-bar__result-icon">${r.icon}</span>` : ''}
        <div class="search-bar__result-text">
          <span class="search-bar__result-title">${r.text}</span>
          ${r.subtitle ? `<span class="search-bar__result-subtitle">${r.subtitle}</span>` : ''}
        </div>
      </li>`
      )
      .join('');

    // Bind click on results
    const items = list.querySelectorAll('.search-bar__result-item');
    items.forEach((item) => {
      item.addEventListener('click', () => {
        const idx = parseInt(item.dataset.index, 10);
        this._selectResult(this._results[idx]);
      });
    });

    this._openDropdown();
  }

  _openDropdown() {
    if (!this.element) return;
    const list = this.element.querySelector('.search-bar__results');
    list.classList.remove('hidden');
    this.element.setAttribute('aria-expanded', 'true');
    this._isOpen = true;
  }

  _closeDropdown() {
    if (!this.element) return;
    const list = this.element.querySelector('.search-bar__results');
    list.classList.add('hidden');
    this.element.setAttribute('aria-expanded', 'false');
    this._isOpen = false;
    this._selectedIndex = -1;
  }

  _moveSelection(direction) {
    const newIndex = this._selectedIndex + direction;
    if (newIndex < 0 || newIndex >= this._results.length) return;
    this._selectedIndex = newIndex;
    this._renderResults();
  }

  _selectResult(result) {
    this._closeDropdown();
    if (this.onSelect) this.onSelect(result);
  }
}
