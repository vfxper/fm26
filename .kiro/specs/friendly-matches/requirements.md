# Requirements Document

## Feature: Товарищеские матчи (User-Arranged Friendlies)

## Introduction

Функция «Товарищеские матчи» позволяет игроку-менеджеру самостоятельно планировать товарищеские матчи между своим клубом и любым другим клубом в системе. Текущий календарь автоматически генерирует только несколько предсезонных товарищеских матчей с placeholder-именами; эта функция даёт пользователю полный контроль: выбор соперника, даты, места проведения (домашний / выездной / нейтральный коммерческий тур / закрытый матч на тренировочной базе), времени начала и описания. Система должна валидировать конфликты с существующими событиями более высокого приоритета (международные перерывы, лига, кубки, еврокубки, заблокированные матчи), сохранять матч как `CalendarEvent` с `event_type=match`, `priority=2` и поддерживать отмену (мягкое удаление). Запланированный товарищеский матч обрабатывается теми же кнопками «▶ Играть матч» (заглушка-симуляция «Движок в разработке») и «⏭ Пропустить (авто)» (использует существующий `MatchEngine`), что и обычные матчи.

Бэкенд: Python / FastAPI / async SQLAlchemy / SQLite. Фронтенд: vanilla JS / HTML в `frontend/index.html`. Локализация интерфейса и описаний событий — русский.

---

## Glossary

- **Friendly_Match** — запись `CalendarEvent` с `event_type="match"` и `priority=2`, представляющая товарищеский матч, созданный пользователем.
- **Friendly_Service** — серверный модуль `app/services/friendly_match_service.py`, отвечающий за создание, валидацию и отмену товарищеских матчей. Расширение существующего `CalendarEngine` методом `add_friendly_match`.
- **Friendly_API** — набор HTTP-эндпоинтов под `/api/calendar/{career_id}/friendly` для CRUD-операций с товарищескими матчами.
- **Friendly_Dialog** — модальное окно фронтенда для создания товарищеского матча.
- **Match_Type** — тип товарищеского матча: `home` (домашний), `away` (выездной), `commercial_tour` (коммерческий тур, нейтральная площадка), `closed_door` (закрытый матч без зрителей).
- **Tour_Venue** — место проведения коммерческого тура (например, Майами, Нью-Йорк, Токио). Список фиксирован в `app/data/tour_venues.py`.
- **Conflict_Validator** — функция, проверяющая, можно ли разместить товарищеский матч на указанной дате без конфликта с событиями более высокого приоритета.
- **Window_Validator** — функция, проверяющая, что дата товарищеского матча попадает в разрешённое временное окно (предсезонка июль–начало августа или международный перерыв).
- **Career** — карьерная сессия пользователя (запись в таблице `careers`).
- **Player_Club** — клуб, за который играет пользователь в текущей карьере.
- **Opponent_Club** — клуб, выбранный пользователем в качестве соперника. Идентифицируется по `club_id` (1-based индекс из `CLUBS`).
- **Mandatory_Fixture** — событие с `is_locked=True` (международный перерыв, заблокированный официальный матч). Не может быть перезаписано или конфликтовать с товарищеским.
- **MatchEngine** — существующий модуль `app/services/match_engine.py`, симулирующий результат матча.
- **CalendarEngine** — существующий модуль `app/services/calendar_engine.py`, управляющий событиями календаря.
- **CLUBS** — список клубов из `app/data/club_budgets.py` в формате `(name, scouting_budget, transfer_budget, league)`.
- **Friendly_Description** — текстовое описание товарищеского матча на русском языке, сохраняемое в поле `description` события.
- **Friendly_Identifier** — численный `id` записи `calendar_events`. Используется для отмены и симуляции.
- **Soft_Cancellation** — отмена матча установкой `is_cancelled=True` без удаления записи из БД.

---

## Requirements

### Requirement 1: Создание товарищеского матча через диалог

**User Story:** Как менеджер клуба, я хочу открыть диалог планирования товарищеского матча из календаря, чтобы выбрать соперника и условия встречи самостоятельно.

#### Acceptance Criteria

1. WHEN the player-manager clicks the "Запланировать товарищеский" button on the calendar screen, THE Friendly_Dialog SHALL display a modal form with fields for date, opponent, match type, kick-off time, and (conditional) tour venue.
2. THE Friendly_Dialog SHALL display the form fields in the following order: date picker, opponent search/select, match type radio group, tour venue select (visible only when match type is `commercial_tour`), kick-off time picker, optional description input.
3. WHEN the player-manager clicks the "Отмена" button in the Friendly_Dialog, THE Friendly_Dialog SHALL close without sending any request.
4. WHEN the player-manager clicks the "Создать" button in the Friendly_Dialog, THE Friendly_Dialog SHALL submit a `POST /api/calendar/{career_id}/friendly` request with all selected values as JSON.
5. WHEN the Friendly_API returns a successful response, THE Friendly_Dialog SHALL close, the calendar grid SHALL refresh to display the new event, and a success toast SHALL appear with the text "Товарищеский матч запланирован".
6. WHEN the Friendly_API returns a validation error, THE Friendly_Dialog SHALL display the error message inline next to the offending field and SHALL keep the dialog open with previously entered values preserved.

---

### Requirement 2: Поиск и фильтрация соперников

**User Story:** Как менеджер клуба, я хочу искать клуб-соперник по названию или фильтровать по лиге, чтобы быстро найти нужного оппонента среди большого списка.

#### Acceptance Criteria

1. WHEN the Friendly_Dialog is opened, THE Friendly_API SHALL provide a list of all clubs from `CLUBS` via `GET /api/clubs/searchable` (excluding the player's own club) with fields `id`, `name`, `league`, `country`.
2. THE Friendly_Dialog SHALL display a search input above the opponent select that filters the visible options by case-insensitive substring match on `name`.
3. THE Friendly_Dialog SHALL display a league filter dropdown above the opponent select with options "Все лиги" plus each unique league from the response.
4. WHEN the player-manager selects a league filter, THE Friendly_Dialog SHALL hide all clubs whose `league` does not match the selected value.
5. WHEN both a search query and a league filter are active, THE Friendly_Dialog SHALL display only clubs that satisfy both conditions.
6. THE Friendly_API endpoint `GET /api/clubs/searchable` SHALL accept an optional `exclude_career_id` query parameter and SHALL exclude the player's club from the results when the parameter is provided.
7. THE Friendly_Dialog SHALL prevent submission while no opponent is selected and SHALL display the message "Выберите соперника" next to the opponent field.

---

### Requirement 3: Тип матча и место проведения

**User Story:** Как менеджер клуба, я хочу выбирать тип товарищеского матча (домашний, выездной, коммерческий тур, закрытый), чтобы планировать как обычные сборы, так и зарубежные турне.

#### Acceptance Criteria

1. THE Friendly_Dialog SHALL display match type as a radio group with exactly four options: "Домашний", "Выездной", "Коммерческий тур", "Закрытый (без зрителей)".
2. WHEN the player-manager selects "Коммерческий тур", THE Friendly_Dialog SHALL show the tour venue select field populated from `GET /api/calendar/tour-venues`.
3. WHEN the player-manager selects any match type other than "Коммерческий тур", THE Friendly_Dialog SHALL hide the tour venue select field.
4. WHEN the match type is `home`, THE Friendly_Service SHALL set `home_club_id` to the player's club and `away_club_id` to the opponent club.
5. WHEN the match type is `away`, THE Friendly_Service SHALL set `home_club_id` to the opponent club and `away_club_id` to the player's club.
6. WHEN the match type is `commercial_tour`, THE Friendly_Service SHALL set `home_club_id` to the player's club, `away_club_id` to the opponent club, and SHALL store the tour venue and host city in the event's `travel_data` JSON field.
7. WHEN the match type is `closed_door`, THE Friendly_Service SHALL set `home_club_id` to the player's club, `away_club_id` to the opponent club, and SHALL append the suffix " (закрытый)" to the description.
8. IF the match type is `commercial_tour` AND no tour venue is provided, THEN THE Friendly_API SHALL return HTTP 422 with the error message "Для коммерческого тура необходимо выбрать площадку".

---

### Requirement 4: Список площадок для коммерческого тура

**User Story:** Как менеджер клуба, я хочу выбрать площадку коммерческого тура из готового списка, чтобы получить реалистичный международный матч.

#### Acceptance Criteria

1. THE Friendly_API SHALL expose `GET /api/calendar/tour-venues` returning a JSON array of objects with fields `id`, `city`, `country`, `stadium_name`.
2. THE tour venues list SHALL include at minimum these eight entries: Майами (USA, Hard Rock Stadium), Нью-Йорк (USA, MetLife Stadium), Лос-Анджелес (USA, SoFi Stadium), Токио (Japan, National Stadium), Сингапур (Singapore, National Stadium), Эр-Рияд (Saudi Arabia, King Fahd International Stadium), Сидней (Australia, Stadium Australia), Мехико (Mexico, Estadio Azteca).
3. THE Friendly_Service SHALL persist the selected venue's `city`, `country`, and `stadium_name` inside `travel_data` JSON when match type is `commercial_tour`.
4. WHEN the Friendly_Dialog displays the tour venue select, THE Friendly_Dialog SHALL render each option as "{city}, {country} — {stadium_name}".

---

### Requirement 5: Валидация даты и временного окна

**User Story:** Как менеджер клуба, я хочу, чтобы система запрещала ставить товарищеские матчи на даты, занятые более важными событиями, чтобы избежать поломок календаря.

#### Acceptance Criteria

1. WHEN the player-manager submits a friendly with a date earlier than the season start date or later than the season end date, THE Friendly_API SHALL return HTTP 422 with the error message "Дата вне игрового сезона".
2. WHEN the player-manager submits a friendly with a date that already has an event with `priority >= 4` for the same career, THE Friendly_API SHALL return HTTP 422 with the error message "На эту дату уже запланирован официальный матч".
3. WHEN the player-manager submits a friendly with a date that already has an event with `is_locked=True` for the same career, THE Friendly_API SHALL return HTTP 422 with the error message "Дата заблокирована (международный перерыв или мандатный матч)".
4. WHEN the player-manager submits a friendly with a date that falls within an `event_type="international"` window, THE Friendly_API SHALL return HTTP 422 with the error message "Дата попадает на международный перерыв".
5. WHEN the player-manager submits a friendly within 48 hours of another existing match for the player's club, THE Friendly_API SHALL return HTTP 422 with the error message "Между матчами должно быть не менее 48 часов".
6. WHEN the player-manager submits a friendly with a date that already has another non-cancelled friendly for the same career, THE Friendly_API SHALL return HTTP 422 with the error message "На эту дату уже запланирован товарищеский матч".
7. WHERE the date falls within the pre-season window (July 15 – August 10) OR within an international break gap (the days adjacent to but not inside an international window), THE Friendly_API SHALL accept the date.
8. WHEN the player-manager submits a friendly outside the recommended pre-season window, THE Friendly_API SHALL accept the date if no other validation fails AND SHALL include the warning string "Дата вне предсезонного окна" in the response body under the `warnings` array.

---

### Requirement 6: Создание события в календаре

**User Story:** Как менеджер клуба, я хочу, чтобы созданный товарищеский матч появлялся в календаре с понятным русским описанием, чтобы я и интерфейс могли его узнать.

#### Acceptance Criteria

1. WHEN the Friendly_Service creates a friendly, THE Friendly_Service SHALL insert one row into `calendar_events` with `event_type="match"`, `priority=2`, `is_locked=False`, `is_cancelled=False`, the chosen `event_date` and `kick_off_time`.
2. WHEN the Friendly_Service creates a friendly, THE Friendly_Service SHALL set the `description` field to the format "Товарищеский матч: {home_name} – {away_name}" using the resolved home and away club names.
3. WHEN the match type is `closed_door`, THE Friendly_Service SHALL append " (закрытый)" to the description, producing "Товарищеский матч: {home_name} – {away_name} (закрытый)".
4. WHEN the match type is `commercial_tour`, THE Friendly_Service SHALL append " — {city}" to the description, producing "Товарищеский матч: {home_name} – {away_name} — {city}".
5. WHEN the Friendly_Service creates a friendly with match type `commercial_tour`, THE Friendly_Service SHALL serialize the venue data as JSON and store it in the `travel_data` column with the structure `{"match_subtype": "commercial_tour", "city": "...", "country": "...", "stadium_name": "..."}`.
6. WHEN the Friendly_Service creates a friendly with match type `closed_door`, THE Friendly_Service SHALL serialize subtype data as JSON and store it in the `travel_data` column with the structure `{"match_subtype": "closed_door", "venue": "training_ground"}`.
7. WHEN the Friendly_Service creates a friendly with match type `home` or `away`, THE Friendly_Service SHALL serialize subtype data as JSON and store it in the `travel_data` column with the structure `{"match_subtype": "home"}` or `{"match_subtype": "away"}` respectively.
8. WHEN the Friendly_API returns the created event, THE response SHALL include the integer `id` of the new `calendar_events` row, the resolved `description`, the chosen `event_date`, the chosen `kick_off_time`, the `home_club_id`, the `away_club_id`, and the parsed `travel_data` object.

---

### Requirement 7: Симуляция и пропуск товарищеского матча

**User Story:** Как менеджер клуба, я хочу запускать симуляцию или авто-пропуск товарищеского матча через те же кнопки, что и для официальных, чтобы интерфейс оставался единообразным.

#### Acceptance Criteria

1. WHEN the player-manager clicks "▶ Играть матч" on a friendly event in the day-detail panel, THE frontend SHALL call `POST /api/calendar/{career_id}/match/{event_id}/simulate` (the existing simulate endpoint).
2. WHEN the player-manager clicks "⏭ Пропустить (авто)" on a friendly event in the day-detail panel, THE frontend SHALL call `POST /api/calendar/{career_id}/match/{event_id}/simulate` (the existing simulate endpoint).
3. WHEN the existing simulate endpoint receives a friendly event (`priority=2`), THE existing simulate endpoint SHALL invoke `MatchEngine.simulate_match(home_club_id, away_club_id, home_name, away_name)` resolving names from `CLUBS` using the club ids stored on the event.
4. WHEN the simulation completes for a friendly, THE existing simulate endpoint SHALL update the event's `description` to "{home_name} {home_score} – {away_score} {away_name}" and SHALL set `is_locked=True` to mark the match as played.
5. WHEN a friendly event has `is_locked=True`, THE Friendly_API DELETE endpoint SHALL return HTTP 409 with the error message "Нельзя отменить уже сыгранный матч".

---

### Requirement 8: Отмена запланированного товарищеского матча

**User Story:** Как менеджер клуба, я хочу отменить запланированный товарищеский матч, чтобы освободить дату для других событий или планов.

#### Acceptance Criteria

1. THE Friendly_API SHALL expose `DELETE /api/calendar/{career_id}/friendly/{event_id}` for cancelling a friendly match.
2. WHEN the Friendly_API receives a DELETE request for an existing friendly with `is_locked=False`, THE Friendly_Service SHALL set `is_cancelled=True` on the event and SHALL return HTTP 200 with body `{"success": true, "event_id": <id>}`.
3. WHEN the Friendly_API receives a DELETE request for an event that does not exist or does not belong to the supplied `career_id`, THE Friendly_API SHALL return HTTP 404 with the error message "Товарищеский матч не найден".
4. WHEN the Friendly_API receives a DELETE request for an event whose `event_type != "match"` OR `priority != 2`, THE Friendly_API SHALL return HTTP 400 with the error message "Это не товарищеский матч".
5. WHEN the Friendly_API receives a DELETE request for an event with `is_locked=True`, THE Friendly_API SHALL return HTTP 409 with the error message "Нельзя отменить уже сыгранный матч".
6. WHEN a friendly event has `is_cancelled=True`, THE existing `GET /api/calendar/{career_id}/month` and `GET /api/calendar/{career_id}/day` endpoints SHALL exclude it from results.
7. WHEN the player-manager clicks the "Отменить" button on a friendly event in the day-detail panel, THE frontend SHALL show a confirmation prompt "Отменить товарищеский матч?" and SHALL call DELETE only after the player-manager confirms.

---

### Requirement 9: Отображение товарищеских матчей в календаре

**User Story:** Как менеджер клуба, я хочу визуально отличать товарищеские матчи от официальных, чтобы быстро ориентироваться в расписании.

#### Acceptance Criteria

1. WHEN the calendar grid displays a day containing a friendly event, THE frontend SHALL render the friendly event marker in blue (`#1E88E5`) per the existing color scheme.
2. WHEN the day-detail panel shows a friendly event, THE day-detail panel SHALL display the icon "🤝" before the match description.
3. WHEN the day-detail panel shows a friendly event with match subtype `commercial_tour`, THE day-detail panel SHALL display the host city beneath the description with a globe icon "🌐 {city}".
4. WHEN the day-detail panel shows a friendly event with match subtype `closed_door`, THE day-detail panel SHALL display the suffix label "🚪 Закрытый матч" beneath the description.
5. WHEN the day-detail panel shows a friendly event with `is_locked=False`, THE day-detail panel SHALL display the "Отменить" button alongside the "▶ Играть матч" and "⏭ Пропустить (авто)" buttons.
6. WHEN the day-detail panel shows a friendly event with `is_locked=True`, THE day-detail panel SHALL hide the "Отменить", "▶ Играть матч", and "⏭ Пропустить (авто)" buttons and SHALL display the recorded score from the description.

---

### Requirement 10: Точка входа из интерфейса календаря

**User Story:** Как менеджер клуба, я хочу открывать диалог создания товарищеского из конкретной даты или из общей кнопки, чтобы планировать встречи быстро и контекстно.

#### Acceptance Criteria

1. THE calendar screen SHALL display a top-level button "+ Товарищеский матч" that opens the Friendly_Dialog with no pre-selected date.
2. WHEN the player-manager clicks an empty day cell in the monthly grid, THE calendar screen SHALL include a "Запланировать товарищеский на эту дату" action in the day-detail panel.
3. WHEN the player-manager activates the per-day action from Acceptance Criterion 10.2, THE Friendly_Dialog SHALL open with the date field pre-filled to that day's date and the date field SHALL remain editable.
4. WHEN the Friendly_Dialog opens with a pre-filled date, THE date field SHALL be visually highlighted to indicate the source of the value.

---

### Requirement 11: Согласованность с существующим календарём

**User Story:** Как разработчик, я хочу, чтобы товарищеские матчи использовали ту же модель и API, что и автогенерируемые события, чтобы не дублировать логику.

#### Acceptance Criteria

1. THE Friendly_Service SHALL persist friendlies in the existing `calendar_events` table without adding new columns.
2. THE Friendly_Service SHALL use `priority=2` for all user-created friendlies to be consistent with auto-generated pre-season friendlies.
3. THE Friendly_Service SHALL set `event_type="match"` for all friendlies to make them indexable by the existing month/day query endpoints.
4. WHEN the player-manager queries the calendar via `GET /api/calendar/{career_id}/month`, THE response SHALL include user-created friendlies alongside auto-generated events, ordered by `event_date` then `priority` desc.
5. THE Friendly_Service SHALL be implemented as a method `add_friendly_match` on the existing `CalendarEngine` class to keep service responsibilities cohesive.
6. WHERE auto-generated pre-season placeholder friendlies exist with `description="Pre-season friendly"` and no opponent club, THE Friendly_Service SHALL NOT modify or delete them; the player-manager SHALL be able to cancel auto-generated friendlies via the same DELETE endpoint provided their `priority=2`, `event_type="match"`, and `is_locked=False`.

---

### Requirement 12: Расширение диапазона разрешённых дат

**User Story:** Как менеджер клуба, я хочу планировать товарищеские не только в предсезонке, но и во время международных перерывов, чтобы загружать команду играми тогда, когда основные игроки уехали в сборные.

#### Acceptance Criteria

1. THE Friendly_API SHALL accept dates within the pre-season window July 15 – August 10 of the season's start year.
2. THE Friendly_API SHALL accept dates within international break gaps, defined as days between the start and end of an `event_type="international"` event in the same career.
3. WHEN the player-manager attempts to schedule a friendly inside a FIFA international window where their key players are away, THE Friendly_API SHALL accept the request AND SHALL include the warning string "Часть игроков на международных матчах" in the response `warnings` array.
4. THE Friendly_API SHALL accept dates outside both the pre-season window and international break windows if and only if no validation rule from Requirement 5 is violated.
5. WHEN the response of `POST /api/calendar/{career_id}/friendly` includes a non-empty `warnings` array, THE Friendly_Dialog SHALL display each warning as a yellow-toned banner inside the dialog before closing, requiring an additional "Подтвердить" click before the actual creation request is finalized.

---

### Requirement 13: Время начала матча

**User Story:** Как менеджер клуба, я хочу выбирать удобное время начала товарищеского матча, чтобы планировать его вокруг других событий.

#### Acceptance Criteria

1. THE Friendly_Dialog SHALL display the kick-off time field as a select with the values "12:00", "15:00", "16:30", "18:00", "20:00", "21:00".
2. THE Friendly_Dialog SHALL set the default kick-off time selection to "18:00".
3. WHEN the player-manager submits a friendly without a kick-off time, THE Friendly_API SHALL set the `kick_off_time` field to "18:00".
4. WHEN the player-manager submits a friendly with a kick-off time string not matching the format `HH:MM`, THE Friendly_API SHALL return HTTP 422 with the error message "Неверный формат времени начала".
5. THE Friendly_API SHALL accept any kick-off time string matching the regex `^([01]\d|2[0-3]):[0-5]\d$` to allow custom times.
