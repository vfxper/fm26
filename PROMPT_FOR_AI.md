# ПРОМПТ ДЛЯ ДРУГОЙ ИИ: ИСПРАВИТЬ ИГРУ

## КОНТЕКСТ
Проект: Football Manager 26 — браузерная игра (Telegram Mini App + PWA).
Стек: Python 3.12 + FastAPI + SQLite (локально) / PostgreSQL (прод) + HTML/JS фронтенд.
Путь: `C:\Users\sin3\Documents\fm26\fm26\`

## ЧТО РАБОТАЕТ
- API сервер запускается: `python run_local.py` → http://localhost:8000
- Фронтенд: `cd frontend && python -m http.server 3000` → http://localhost:3000
- 51 REST API endpoint написан
- Swagger docs: http://localhost:8000/docs

## ЧТО СЛОМАНО (КРИТИЧЕСКИЕ БАГИ)

### БАГ 1: База данных пустая
SQLite файл `fm26_local.db` создаётся, но в нём нет данных.
Нужно загрузить 34,644 игроков из `2600球员属性.csv` (UTF-8-BOM, comma delimiter).
Файл: `C:\Users\sin3\Documents\fm26\fm26\2600球员属性.csv`
Скрипт загрузки: `app/services/player_loader.py` (уже написан для PostgreSQL, нужно адаптировать для SQLite).

**Что сделать:**
1. Создать `seed_local.py` который читает CSV и вставляет в SQLite
2. Также создать 20 клубов (Real Madrid, Barcelona, Man City, etc.)
3. Распределить игроков по клубам (по полю `club` из CSV)

### БАГ 2: Нет экрана выбора клуба
При первом запуске игрок должен выбрать клуб. Сейчас карьера создаётся с `club_id=1` который не существует.

**Что сделать:**
1. В `frontend/index.html` добавить экран "Выбор клуба" перед главным экраном
2. Показать список клубов из API: `GET /api/clubs` (нужно создать endpoint)
3. После выбора — `POST /api/careers` с выбранным `club_id`
4. При создании карьеры — автоматически добавить игроков клуба в `squad_players`

### БАГ 3: CORS блокирует запросы
Фронт на :3000, API на :8000. CORS не пропускает.

**Что сделать:**
В `app/main.py` в CORSMiddleware добавить `allow_origins=["*"]` или `["http://localhost:3000"]`.
Или в `run_local.py` патчить settings.CORS_ORIGINS.

### БАГ 4: Поиск игроков не работает
`GET /api/players/search?q=ronaldo` возвращает пустой результат потому что таблица `players` пуста (см. Баг 1).

### БАГ 5: Симуляция матча падает
`POST /api/careers/{id}/matches/simulate` — "Failed to fetch" потому что:
- Нет fixtures (расписания матчей) в БД
- Нет squad_players (состава)
- CORS блокирует

**Что сделать:**
При создании карьеры автоматически генерировать расписание на сезон (38 матчей лиги).

### БАГ 6: Тактика не редактируется
Экран тактики показывает статичные значения. Нет кнопок для изменения.

**Что сделать:**
Добавить dropdown/кнопки для выбора формации, ментальности, прессинга.
При изменении — `PUT /api/careers/{id}/tactics/0` с новыми значениями.

### БАГ 7: Состав пуст
`GET /api/careers/{id}/squad` возвращает пустой массив.

**Что сделать:**
При `POST /api/careers` (создание карьеры) — автоматически заполнять `squad_players` игроками выбранного клуба из таблицы `players`.

## ПОРЯДОК ИСПРАВЛЕНИЯ
1. Создать `seed_local.py` — загрузить CSV в SQLite (игроки + клубы)
2. Исправить CORS в `app/main.py`
3. Добавить endpoint `GET /api/clubs`
4. В `POST /api/careers` — автозаполнение состава + генерация расписания
5. В `frontend/index.html` — экран выбора клуба
6. В `frontend/index.html` — редактируемая тактика
7. Тест: запустить, выбрать клуб, увидеть состав, симулировать матч

## КЛЮЧЕВЫЕ ФАЙЛЫ
- `run_local.py` — запуск локального сервера
- `app/main.py` — FastAPI приложение
- `app/api/routes/` — все API endpoints
- `app/services/career_service.py` — логика карьеры
- `app/services/match_simulator.py` — симуляция матчей
- `frontend/index.html` — UI игры
- `2600球员属性.csv` — данные 34,644 игроков

## CSV ФОРМАТ (первые колонки)
Колонка 0: Name, 1: Age, 2: Nationality, 3: Club, 4: Position, 5: CA, 6: PA, ...
Encoding: utf-8-sig (BOM), delimiter: comma
Всего ~50 колонок с атрибутами (passing, shooting, tackling, etc.)
