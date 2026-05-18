/**
 * Localization System (Task 39)
 * Supports: Russian, English, Spanish, Portuguese, German
 */

const translations = {
  ru: {
    // Navigation
    'nav.home': 'Главная',
    'nav.squad': 'Состав',
    'nav.tactics': 'Тактика',
    'nav.transfers': 'Трансферы',
    'nav.match': 'Матч',
    
    // Dashboard
    'dashboard.title': 'Панель управления',
    'dashboard.next_match': 'Следующий матч',
    'dashboard.league_position': 'Позиция в лиге',
    'dashboard.budget': 'Бюджет',
    'dashboard.morale': 'Мораль команды',
    
    // Squad
    'squad.title': 'Состав команды',
    'squad.player': 'Игрок',
    'squad.position': 'Позиция',
    'squad.age': 'Возраст',
    'squad.rating': 'Рейтинг',
    'squad.morale': 'Мораль',
    'squad.fitness': 'Форма',
    'squad.contract': 'Контракт',
    'squad.wage': 'Зарплата',
    
    // Tactics
    'tactics.title': 'Тактика',
    'tactics.formation': 'Формация',
    'tactics.mentality': 'Ментальность',
    'tactics.pressing': 'Прессинг',
    'tactics.defensive_line': 'Линия обороны',
    'tactics.width': 'Ширина',
    'tactics.tempo': 'Темп',
    
    // Match
    'match.simulate': 'Симулировать матч',
    'match.live': 'Смотреть матч',
    'match.result': 'Результат',
    'match.stats': 'Статистика',
    'match.events': 'События',
    'match.half_time': 'Перерыв',
    'match.full_time': 'Конец матча',
    'match.goal': 'ГОЛ!',
    
    // Transfers
    'transfers.search': 'Поиск игроков',
    'transfers.bid': 'Сделать предложение',
    'transfers.budget': 'Трансферный бюджет',
    'transfers.window': 'Трансферное окно',
    'transfers.history': 'История трансферов',
    
    // Common
    'common.save': 'Сохранить',
    'common.load': 'Загрузить',
    'common.back': 'Назад',
    'common.confirm': 'Подтвердить',
    'common.cancel': 'Отмена',
    'common.settings': 'Настройки',
    'common.season': 'Сезон',
    'common.week': 'Неделя',
  },

  en: {
    'nav.home': 'Home',
    'nav.squad': 'Squad',
    'nav.tactics': 'Tactics',
    'nav.transfers': 'Transfers',
    'nav.match': 'Match',
    'dashboard.title': 'Dashboard',
    'dashboard.next_match': 'Next Match',
    'dashboard.league_position': 'League Position',
    'dashboard.budget': 'Budget',
    'dashboard.morale': 'Team Morale',
    'squad.title': 'Squad',
    'squad.player': 'Player',
    'squad.position': 'Position',
    'squad.age': 'Age',
    'squad.rating': 'Rating',
    'squad.morale': 'Morale',
    'squad.fitness': 'Fitness',
    'squad.contract': 'Contract',
    'squad.wage': 'Wage',
    'tactics.title': 'Tactics',
    'tactics.formation': 'Formation',
    'tactics.mentality': 'Mentality',
    'tactics.pressing': 'Pressing',
    'tactics.defensive_line': 'Defensive Line',
    'tactics.width': 'Width',
    'tactics.tempo': 'Tempo',
    'match.simulate': 'Simulate Match',
    'match.live': 'Watch Match',
    'match.result': 'Result',
    'match.stats': 'Statistics',
    'match.events': 'Events',
    'match.half_time': 'Half Time',
    'match.full_time': 'Full Time',
    'match.goal': 'GOAL!',
    'transfers.search': 'Search Players',
    'transfers.bid': 'Make Offer',
    'transfers.budget': 'Transfer Budget',
    'transfers.window': 'Transfer Window',
    'transfers.history': 'Transfer History',
    'common.save': 'Save',
    'common.load': 'Load',
    'common.back': 'Back',
    'common.confirm': 'Confirm',
    'common.cancel': 'Cancel',
    'common.settings': 'Settings',
    'common.season': 'Season',
    'common.week': 'Week',
  },

  es: {
    'nav.home': 'Inicio',
    'nav.squad': 'Plantilla',
    'nav.tactics': 'Táctica',
    'nav.transfers': 'Fichajes',
    'nav.match': 'Partido',
    'dashboard.title': 'Panel',
    'match.goal': '¡GOL!',
    'match.full_time': 'Final',
    'common.save': 'Guardar',
    'common.cancel': 'Cancelar',
  },

  pt: {
    'nav.home': 'Início',
    'nav.squad': 'Elenco',
    'nav.tactics': 'Tática',
    'nav.transfers': 'Transferências',
    'nav.match': 'Partida',
    'match.goal': 'GOL!',
    'common.save': 'Salvar',
  },

  de: {
    'nav.home': 'Start',
    'nav.squad': 'Kader',
    'nav.tactics': 'Taktik',
    'nav.transfers': 'Transfers',
    'nav.match': 'Spiel',
    'match.goal': 'TOR!',
    'common.save': 'Speichern',
  },
};

let currentLang = 'ru';

export function setLanguage(lang) {
  if (translations[lang]) {
    currentLang = lang;
    document.documentElement.lang = lang;
    // Dispatch event for reactive updates
    window.dispatchEvent(new CustomEvent('language-changed', { detail: { lang } }));
  }
}

export function t(key, params = {}) {
  let text = translations[currentLang]?.[key] || translations['en']?.[key] || key;
  // Replace {param} placeholders
  for (const [k, v] of Object.entries(params)) {
    text = text.replace(`{${k}}`, v);
  }
  return text;
}

export function getLanguage() {
  return currentLang;
}

export function getAvailableLanguages() {
  return [
    { code: 'ru', name: 'Русский' },
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Español' },
    { code: 'pt', name: 'Português' },
    { code: 'de', name: 'Deutsch' },
  ];
}
