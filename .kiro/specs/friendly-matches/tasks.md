# Implementation Plan: Товарищеские матчи (User-Arranged Friendlies)

## Overview

Implement user-arranged friendly matches as an extension to the existing calendar system. The feature reuses the existing `calendar_events` table and `MatchEngine.simulate_match`, adds a new `FriendlyMatchService` with validation logic, exposes three new API endpoints (`POST/DELETE /api/calendar/{career_id}/friendly`, `GET /api/calendar/tour-venues`, `GET /api/clubs/searchable`), and adds a `Friendly_Dialog` modal to the frontend calendar screen with date picker, opponent search/filter, match-type radio group, conditional tour-venue select, kick-off time, and description input. The same simulate endpoint that powers official matches handles friendlies. Implementation language: Python 3 (FastAPI + async SQLAlchemy + Hypothesis), JavaScript (vanilla) for the frontend.

## Tasks

- [x] 1. Tour venues data module
  - [x] 1.1 Create `app/data/tour_venues.py`
    - Define `TOUR_VENUES` constant as a list of `(id, city, country, stadium_name)` tuples for the 8 venues listed in Requirement 4.2
    - Implement `get_tour_venues() -> list[dict]` returning JSON-friendly dicts
    - Implement `get_tour_venue_by_id(venue_id: int) -> dict | None` for single lookup
    - _Requirements: 4.1, 4.2_

  - [x]* 1.2 Write unit test for `get_tour_venue_by_id` returning correct lookup
    - Test each of the 8 venues retrievable by id
    - Test unknown id returns None
    - _Requirements: 4.1, 4.2_

- [x] 2. FriendlyMatchService skeleton and pure helpers
  - [x] 2.1 Create `app/services/friendly_match_service.py` with module structure
    - Define `KICK_OFF_REGEX`, `VALID_MATCH_TYPES`, `PRESEASON_START_MMDD`, `PRESEASON_END_MMDD` constants
    - Define `FriendlyCreateRequest` dataclass with fields: `event_date`, `opponent_club_id`, `match_type`, `kick_off_time`, `tour_venue_id`, `description_suffix`
    - Define `FriendlyCreateResult` dataclass with fields per design + `warnings: list[str]`
    - Define `ValidationError(Exception)` with `message: str` and `http_status: int = 422`
    - Define `FriendlyMatchService` class accepting `AsyncSession` in `__init__`
    - _Requirements: 6.1, 6.8_

  - [x] 2.2 Implement `_validate_match_type(match_type: str) -> None`
    - Raise `ValidationError(422, "Неверный тип матча")` if not in `VALID_MATCH_TYPES`
    - _Requirements: 3.1_

  - [x] 2.3 Implement `_validate_kick_off(kick_off_time: str) -> None`
    - Raise `ValidationError(422, "Неверный формат времени начала")` if regex does not match
    - _Requirements: 13.4, 13.5_

  - [x] 2.4 Implement `_validate_opponent(opponent_club_id: int, player_club_id: int) -> None`
    - Raise `ValidationError(422, "Неверный соперник")` if id < 1 or > `len(CLUBS)`
    - Raise `ValidationError(422, "Нельзя играть против самого себя")` if equals player's club
    - _Requirements: 2.1_

  - [x] 2.5 Implement `_validate_tour_venue(match_type, tour_venue_id) -> dict | None`
    - When match_type == "commercial_tour", lookup via `get_tour_venue_by_id`; raise `ValidationError(422, "Для коммерческого тура необходимо выбрать площадку")` if id missing or not found
    - When match_type != "commercial_tour", return `None`
    - _Requirements: 3.8, 4.1_

  - [x] 2.6 Implement `_resolve_home_away(match_type, player_club_id, opponent_club_id) -> tuple[int, int]`
    - Return `(opponent_club_id, player_club_id)` when match_type == "away"
    - Return `(player_club_id, opponent_club_id)` for all other valid match types
    - _Requirements: 3.4, 3.5, 3.6, 3.7_

  - [x] 2.7 Implement `_build_description(match_type, home_name, away_name, venue, suffix) -> str`
    - Base: `f"Товарищеский матч: {home_name} – {away_name}"`
    - Append `" (закрытый)"` for closed_door
    - Append `f" — {venue['city']}"` for commercial_tour
    - Append `f" [{suffix}]"` when suffix is non-empty
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 2.8 Implement `_build_travel_data(match_type, venue) -> dict`
    - Return `{"match_subtype": match_type}` for home/away
    - Return `{"match_subtype": "closed_door", "venue": "training_ground"}` for closed_door
    - Return `{"match_subtype": "commercial_tour", "city": ..., "country": ..., "stadium_name": ...}` for commercial_tour
    - _Requirements: 6.5, 6.6, 6.7_

  - [x]* 2.9 Write property test for match-type to home/away mapping
    - **Property 3: Match-type to home/away mapping is deterministic**
    - **Validates: Requirements 3.4, 3.5, 3.6, 3.7**

  - [x]* 2.10 Write property test for description format
    - **Property 5: Description format covers all match subtypes**
    - **Validates: Requirements 6.2, 6.3, 6.4**

  - [x]* 2.11 Write property test for travel_data JSON round-trip
    - **Property 6: travel_data round-trip preserves match subtype data**
    - **Validates: Requirements 6.5, 6.6, 6.7**

  - [x]* 2.12 Write property test for kick-off format validation
    - **Property 10: Kick-off time format validation is regex-equivalent**
    - **Validates: Requirements 13.4, 13.5**

  - [x]* 2.13 Write property test for commercial_tour requires venue
    - **Property 4: commercial_tour requires a tour venue**
    - **Validates: Requirements 3.8**

- [x] 3. FriendlyMatchService — DB-aware helpers
  - [x] 3.1 Implement `_get_player_club_id(career_id: int) -> int`
    - Read `careers.club_id`; raise `ValidationError(422, "Карьера не найдена")` if missing
    - _Requirements: 2.1_

  - [x] 3.2 Implement `_resolve_season_window(career_id: int) -> tuple[date, date]`
    - SELECT MIN(event_date) and MAX(event_date) from `calendar_events` for this career, excluding cancelled
    - Fallback: `(today, today + 365 days)` when no events exist yet
    - _Requirements: 5.1_

  - [x] 3.3 Implement `_existing_events_around(career_id, event_date) -> list[dict]`
    - SELECT events for the career within ±2 days of `event_date`, excluding cancelled
    - Return list of dicts with id, event_date, event_type, priority, is_locked
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 3.4 Implement `_check_window(event_date, season_start, season_end) -> list[str]`
    - Raise `ValidationError(422, "Дата вне игрового сезона")` if outside [season_start, season_end]
    - Append `"Дата вне предсезонного окна"` to warnings if outside July 15 – August 10 of the start year (and not inside an international event window — that adjustment happens in `_check_conflicts`)
    - Return the warnings list
    - _Requirements: 5.1, 5.7, 5.8, 12.1, 12.4_

  - [x] 3.5 Implement `_check_conflicts(event_date, existing) -> list[str]`
    - Iterate `existing` events in priority order and apply blocking rules from Property 9
    - Raise the first matching `ValidationError` with the matching message
    - When `event_date` falls inside an `event_type="international"` event range, append `"Часть игроков на международных матчах"` to warnings
    - Return warnings
    - _Requirements: 5.2, 5.3, 5.4, 5.5, 5.6, 12.2, 12.3_

- [x] 4. CalendarEngine.add_friendly_match
  - [x] 4.1 Add `add_friendly_match` method to `app/services/calendar_engine.py`
    - Accept `career_id`, `event_date`, `home_club_id`, `away_club_id`, `kick_off_time`, `description`, `travel_data` (dict)
    - Serialize travel_data with `json.dumps(travel_data, ensure_ascii=False)`
    - INSERT into `calendar_events` with `event_type='match'`, `priority=2`, `is_locked=0`, `is_cancelled=0`
    - Read back the new id via `SELECT last_insert_rowid()`
    - Return a dict matching the existing event shape used by `/api/calendar/{career_id}/day`
    - _Requirements: 6.1, 11.1, 11.2, 11.3, 11.5_

- [x] 5. FriendlyMatchService — orchestration
  - [x] 5.1 Implement `create_friendly(career_id, request) -> FriendlyCreateResult`
    - Call validation helpers in order: `_validate_match_type`, `_validate_kick_off`, `_get_player_club_id`, `_validate_opponent`, `_validate_tour_venue`
    - Call `_resolve_season_window` and `_existing_events_around`
    - Collect warnings from `_check_window` and `_check_conflicts`
    - Resolve home/away ids via `_resolve_home_away`
    - Look up home and away club names from `CLUBS` (1-based)
    - Build description and travel_data via the pure helpers
    - Call `CalendarEngine(self.session).add_friendly_match(...)` to persist
    - Return `FriendlyCreateResult` with all fields populated
    - _Requirements: 1.4, 5, 6, 12.3_

  - [x] 5.2 Implement `cancel_friendly(career_id, event_id) -> int`
    - SELECT the row by `(id=event_id, career_id, is_cancelled=0)`
    - Apply the four cases from Property 11
    - On success, UPDATE `is_cancelled=1` and commit
    - Return `event_id`
    - _Requirements: 7.5, 8.2, 8.3, 8.4, 8.5, 11.6_

  - [x]* 5.3 Write property test for friendly creation round-trip
    - **Property 7: Friendly creation round-trip preserves request data**
    - **Validates: Requirements 4.3, 6.1, 6.8, 11.1, 11.2, 11.3, 11.4, 13.3**

  - [x]* 5.4 Write property test for date-window classification
    - **Property 8: Date-window classification is exhaustive and consistent**
    - **Validates: Requirements 5.1, 5.7, 5.8, 12.1, 12.4**

  - [x]* 5.5 Write property test for blocking-event rejection
    - **Property 9: Conflicting blocking events cause rejection with a specific message**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6**

  - [x]* 5.6 Write property test for cancel friendly correctness
    - **Property 11: Cancel friendly is correct under all event states**
    - **Validates: Requirements 7.5, 8.2, 8.3, 8.4, 8.5, 11.6**

- [x] 6. Checkpoint — Service tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. API routes
  - [x] 7.1 Add `FriendlyCreatePayload` Pydantic model and `POST /api/calendar/{career_id}/friendly` endpoint to `app/api/routes/calendar.py`
    - Parse `event_date` as ISO date; on parse failure return HTTP 422 with `"Неверный формат даты"`
    - Instantiate `FriendlyMatchService` and call `create_friendly`
    - Catch `ValidationError` and re-raise as `HTTPException(ve.http_status, ve.message)`
    - Return JSON with id, event_date, kick_off_time, club ids, description, travel_data, warnings
    - _Requirements: 1.4, 1.5, 1.6, 6.8_

  - [x] 7.2 Add `DELETE /api/calendar/{career_id}/friendly/{event_id}` endpoint
    - Call `FriendlyMatchService.cancel_friendly`
    - Catch `ValidationError` and re-raise as `HTTPException(ve.http_status, ve.message)`
    - Return `{"success": True, "event_id": cancelled_id}`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 7.3 Add `GET /api/calendar/tour-venues` endpoint
    - Return `{"venues": get_tour_venues()}`
    - _Requirements: 4.1, 4.4_

  - [x] 7.4 Add `GET /api/clubs/searchable` endpoint to `app/api/routes/clubs.py`
    - Accept `exclude_career_id: int | None = Query(default=None, ge=1)`
    - When provided, look up the career's `club_id` and skip that index in the response
    - Iterate `CLUBS` with 1-based ids; return id, name, league
    - _Requirements: 2.1, 2.6_

  - [x]* 7.5 Write property test for searchable clubs exclusion
    - **Property 1: Searchable clubs API excludes the player's own club**
    - **Validates: Requirements 2.1, 2.6**

  - [x]* 7.6 Write integration test for create-then-simulate flow
    - Create a friendly via POST /friendly
    - Call existing `POST /api/calendar/{career_id}/match/{event_id}/simulate`
    - Assert response has scores and the event is locked
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x]* 7.7 Write integration test for create-then-list flow
    - Create a friendly via POST /friendly
    - GET /api/calendar/{career_id}/month for the matching month
    - Assert the new event appears with priority=2 and event_type=match
    - _Requirements: 11.4_

- [x] 8. Frontend — opponent picker and tour venue loading
  - [x] 8.1 Add API client methods to `frontend/src/api-client.js`
    - `fetchSearchableClubs(careerId)` -> GET /api/clubs/searchable?exclude_career_id=...
    - `fetchTourVenues()` -> GET /api/calendar/tour-venues
    - `createFriendly(careerId, payload)` -> POST /api/calendar/{cid}/friendly
    - `cancelFriendly(careerId, eventId)` -> DELETE /api/calendar/{cid}/friendly/{eid}
    - _Requirements: 1.4, 2.1, 4.1, 8.1_

  - [x] 8.2 Implement opponent filter pure function `filterOpponents(clubs, query, leagueFilter)`
    - Return clubs whose name (lowercased) contains query (lowercased)
    - When `leagueFilter !== "Все лиги"`, additionally require `club.league === leagueFilter`
    - _Requirements: 2.2, 2.4, 2.5_

  - [x] 8.3 Implement tour venue option formatter `formatTourVenue(venue)`
    - Return `f"{venue.city}, {venue.country} — {venue.stadium_name}"`
    - _Requirements: 4.4_

  - [x]* 8.4 Write property test for opponent filter intersection
    - **Property 2: Client-side opponent filter is the intersection of search query and league filter**
    - **Validates: Requirements 2.2, 2.4, 2.5**
    - Note: implement using fast-check or a Hypothesis port, OR mark as PROPERTY-style unit test with table-driven cases if PBT not available in the frontend test stack

- [x] 9. Frontend — Friendly_Dialog component
  - [x] 9.1 Add the dialog DOM markup and styles
    - In the modular UI: create `frontend/src/ui/components/FriendlyDialog.js`
    - In the legacy single-file UI: append a `<dialog id="friendly-dialog">` block to `frontend/index.html` with the layout from the design
    - Include date input, opponent search input, league select, opponent select (radio list), match-type radio group, tour-venue select (initially hidden), kick-off select with 6 default options ("12:00", "15:00", "16:30", "18:00", "20:00", "21:00"), description textarea, Cancel + Create buttons, warnings banner placeholder
    - Style with the project's existing card/button classes; use `#1E88E5` accent for the dialog border
    - _Requirements: 1.1, 1.2, 13.1, 13.2_

  - [x] 9.2 Wire up dialog data loading on open
    - On open: call `fetchSearchableClubs(careerId)` and `fetchTourVenues()` in parallel
    - Populate the league filter with unique leagues from clubs, plus "Все лиги" as default
    - Populate the tour-venue select with `formatTourVenue(v)` per venue
    - _Requirements: 2.1, 2.3, 4.1, 4.4_

  - [x] 9.3 Wire up dialog interactivity
    - Bind search input and league filter to update the visible opponent list using `filterOpponents`
    - Bind match-type radio change to show/hide the tour-venue select
    - Disable Create button when no opponent selected; show inline message "Выберите соперника"
    - Show inline message "Для коммерческого тура необходимо выбрать площадку" when match_type=commercial_tour and no venue selected
    - On Cancel click: close dialog without sending any request
    - _Requirements: 1.3, 2.2, 2.4, 2.5, 2.7, 3.2, 3.3, 3.8_

  - [x] 9.4 Wire up dialog submit
    - On Create click: build payload, call `createFriendly`, on 201 close dialog and emit `calendar:refresh` event
    - On 4xx: render inline error from `detail` next to the offending field if identifiable, otherwise at the bottom of the dialog
    - On warnings array non-empty: show yellow banner with each warning, render a "Подтвердить" button that closes the dialog
    - On network error: show toast "Ошибка соединения. Попробуйте позже."
    - _Requirements: 1.4, 1.5, 1.6, 12.5_

- [x] 10. Frontend — calendar screen integration
  - [x] 10.1 Add the top-level "+ Товарищеский матч" button to the calendar screen
    - Bind click to open the dialog with no pre-filled date
    - _Requirements: 10.1_

  - [x] 10.2 Modify the day-detail panel to include "Запланировать товарищеский на эту дату"
    - Action shown when the day has no event for this career
    - Click opens the dialog with the date pre-filled and the date input visually highlighted
    - _Requirements: 10.2, 10.3, 10.4_

  - [x] 10.3 Modify the day-detail panel to render friendly events with their visual treatment
    - Prefix description with "🤝"
    - Show "🌐 {city}" suffix for commercial_tour
    - Show "🚪 Закрытый матч" suffix for closed_door
    - When `is_locked=False` and `priority=2` and `event_type=match`: show "▶ Играть матч", "⏭ Пропустить (авто)", "Отменить" buttons
    - When `is_locked=True`: hide all three action buttons and show only the recorded score
    - "Отменить" prompts a confirmation "Отменить товарищеский матч?" before calling `cancelFriendly`
    - _Requirements: 7.1, 7.2, 8.7, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 10.4 Wire up the calendar grid to refresh on `calendar:refresh` events
    - Re-fetch the current month's events when the dialog reports success or a friendly is cancelled
    - _Requirements: 1.5, 8.2_

- [x] 11. Checkpoint — Frontend integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Documentation
  - [x] 12.1 Update `README.md` (or create a short note in `.kiro/specs/friendly-matches/`) describing how to use the dialog
    - List the four match types and what each does
    - Document the API endpoints
    - Note the out-of-scope items: commercial revenue for tours, weather/travel planning for friendly venues, FFP eligibility checks
    - _Requirements: documentation only, not tied to a specific acceptance criterion_

- [x] 13. Final checkpoint — Full feature integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP.
- The implementation language is Python 3 for the backend and vanilla JavaScript for the frontend; both are already established in the project. No language selection is required because the design uses concrete Python/JS code rather than pseudocode.
- Each task references specific requirements for traceability.
- Property tests use Hypothesis on the backend; the frontend opponent-filter property test can use `fast-check` if available, or a table-driven property-style test otherwise.
- Property test tag format: `# Feature: friendly-matches, Property {N}: {short title}`.
- All property tests SHALL run with `max_examples=100` minimum.
- Out-of-scope (not implemented in this spec): commercial revenue for tours, weather generation for friendlies, travel planning between home city and tour venue, friendly TV slots, FFP/eligibility checks. These are documented in the design and may be added in a follow-up spec.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8"] },
    { "id": 2, "tasks": ["2.9", "2.10", "2.11", "2.12", "2.13", "3.1", "3.2", "3.3", "3.4", "3.5"] },
    { "id": 3, "tasks": ["4.1"] },
    { "id": 4, "tasks": ["5.1", "5.2"] },
    { "id": 5, "tasks": ["5.3", "5.4", "5.5", "5.6"] },
    { "id": 6, "tasks": ["7.1", "7.2", "7.3", "7.4"] },
    { "id": 7, "tasks": ["7.5", "7.6", "7.7"] },
    { "id": 8, "tasks": ["8.1", "8.2", "8.3"] },
    { "id": 9, "tasks": ["8.4", "9.1", "9.2", "9.3", "9.4"] },
    { "id": 10, "tasks": ["10.1", "10.2", "10.3", "10.4"] },
    { "id": 11, "tasks": ["12.1"] }
  ]
}
```
