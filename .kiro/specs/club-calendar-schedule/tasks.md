# Implementation Plan: Club Calendar & Schedule

## Overview

Implement a full-season calendar system for the Football Manager 26 game. The system auto-generates a structured season calendar on career creation, handles scheduling conflicts with priority-based placement, provides weather/travel/reminder services, and renders an interactive monthly grid UI. Implementation uses Python/FastAPI backend with SQLite and vanilla JS frontend.

## Tasks

- [x] 1. Database schema and models
  - [x] 1.1 Add calendar tables to `run_local.py` `create_tables()`
    - Add `calendar_events` table with all columns (id, career_id, event_date, event_type, competition_id, home_club_id, away_club_id, is_locked, priority, kick_off_time, weather_data, description, travel_data, original_date, reschedule_reason, is_cancelled, template_id, created_at, updated_at)
    - Add `league_configs` table with all columns (id, country, league_name, has_winter_break, winter_break_start, winter_break_end, mandatory_fixture_dates, blackout_dates, custom_milestones, season_start_date, season_end_date, european_competition, created_at)
    - Add `recurring_templates` table with all columns (id, career_id, name, day_assignments, is_active, created_at, updated_at)
    - Add indexes: (career_id, event_date), (career_id, event_type), (career_id, priority)
    - Add CHECK constraint for priority 0–10
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

  - [x] 1.2 Create ORM model `app/models/calendar_event.py`
    - Define `CalendarEvent` SQLAlchemy model with all mapped columns matching the design
    - Include `__table_args__` with indexes and CheckConstraint
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

  - [x] 1.3 Create ORM model `app/models/league_config.py`
    - Define `LeagueConfig` SQLAlchemy model with all mapped columns
    - _Requirements: 18.1, 18.5_

  - [x] 1.4 Create ORM model `app/models/recurring_template.py`
    - Define `RecurringTemplate` SQLAlchemy model with all mapped columns
    - Include index on career_id
    - _Requirements: 14.1, 14.2_

- [x] 2. League configuration data
  - [x] 2.1 Create `app/data/league_configs.py` with static league data for 10 leagues
    - England (Premier League): no winter break, mandatory Boxing Day (12-26) and New Year (01-01), blackout 12-25
    - Germany (Bundesliga): winter break Jan 1–31, blackout 12-25
    - Spain (La Liga): winter break Jan 1–31, blackout 12-25
    - Italy (Serie A): no winter break, blackout 12-25
    - France (Ligue 1): no winter break, blackout 12-25
    - Netherlands (Eredivisie): winter break Dec 23–Jan 14, blackout 12-25
    - Portugal (Primeira Liga): no winter break, blackout 12-25
    - Turkey (Süper Lig): winter break Jan 1–31, blackout 12-25
    - Scotland (Premiership): no winter break, mandatory 12-26, 01-02, blackout 12-25
    - Belgium (Pro League): winter break Dec 26–Jan 14, blackout 12-25
    - Include season_start_date, season_end_date, custom_milestones per league
    - Provide a `get_league_config(country: str) -> dict` helper function
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 1.9, 1.10_

- [x] 3. CalendarEngine service — core generation
  - [x] 3.1 Create `app/services/calendar_engine.py` with class skeleton and supporting dataclasses
    - Define `SeasonBlock`, `Conflict`, `ConflictReport`, `OverloadWarning`, `RecalculationResult`, `KickOffSlot` dataclasses
    - Define `CalendarEngine.__init__` accepting AsyncSession
    - _Requirements: 1.2_

  - [x] 3.2 Implement `CalendarEngine.generate_season()` — season block creation and milestones
    - Create 5 season blocks: Pre-season (Jul 15–Aug 10), First Half (Aug 10–Dec 31), Winter Break (Jan 1–31), Second Half (Feb 1–May 31), Season Finish (Jun 1–14)
    - Generate milestone events: summer window open (Jul 1), season start (Jul 15), summer window close (Aug 31), winter window open (Jan 1), winter window close (Jan 31), last league matchday, cup final, custom milestones from league config
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.12, 16.1, 16.4_

  - [x] 3.3 Implement priority-based event placement in `generate_season()`
    - Place international windows (priority 10, locked) for Sep, Oct, Nov, Mar
    - Place European competition dates (priority 8) on Tue/Wed (CL) or Thu (EL)
    - Generate league matchdays (priority 6) every Saturday Aug 10–May 15, skipping international windows and winter break
    - Place domestic cup rounds (priority 4) on midweek Tue/Wed/Thu
    - Fill pre-season friendlies (priority 2) on free dates Jul 20–Aug 8
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 15.4_

  - [x] 3.4 Implement kick-off time assignment logic
    - Default league matches: Saturday 15:00
    - TV slot selection: Friday 20:00, Saturday 12:30, Sunday 16:30 with revenue multiplier
    - European matches: 21:00
    - Domestic cup: 20:00
    - Store kick_off_time on every match event
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 3.5 Implement pre-season event generation
    - Schedule training camp events 2–3 weeks before first league matchday
    - Schedule player return-from-international-duty at start of pre-season
    - Schedule medical examinations during first week of pre-season
    - Schedule Super Cup match in last week before first league matchday
    - _Requirements: 1.5, 1.6, 1.7, 1.11_

  - [x] 3.6 Implement personal events generation
    - Add contract expiry events for squad players expiring this season
    - Add player birthday events for first-team players
    - Add promise deadline events when applicable
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 3.7 Implement pre-match day schedule generation
    - For each match, generate pre-match day events: morning light warmup, afternoon tactical theory
    - For away matches, add evening hotel check-in event
    - Prevent normal training on pre-match days
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [ ]* 3.8 Write property tests for season structure (Properties 1, 4, 6, 7)
    - **Property 1: Season structure invariant** — 5 non-overlapping contiguous blocks, Jul 15 to Jun 14
    - **Property 4: Friendly non-conflict** — no other event on same date as friendly
    - **Property 6: Winter break enforcement** — zero league matches during winter break
    - **Property 7: Blackout date enforcement** — no matches on Dec 25 or blackout dates
    - **Validates: Requirements 1.1, 1.2, 1.8, 1.9, 1.12, 2.5, 18.3, 18.4, 18.5**

  - [ ]* 3.9 Write property tests for priority and scheduling (Properties 2, 3, 5, 8)
    - **Property 2: Priority ordering preservation** — lower priority never overwrites higher
    - **Property 3: Day-of-week constraints** — European Tue/Wed/Thu, league Fri-Mon, cup Tue/Wed/Thu
    - **Property 5: 48-hour match separation** — no two matches within 48h for same club
    - **Property 8: Kick-off time assignment** — correct times per match type
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.8, 2.9, 3.8, 4.1, 4.2, 4.4, 4.5, 4.6**

- [x] 4. CalendarEngine — conflict detection and rescheduling
  - [x] 4.1 Implement `detect_conflict()` and `detect_overload()`
    - Check same club + same date conflicts
    - Check 48-hour rule between matches
    - Detect 3+ matches within 7-day window
    - Return `Conflict` or `OverloadWarning` objects
    - _Requirements: 3.1, 3.6, 3.8_

  - [x] 4.2 Implement `reschedule_event()` and `handle_european_thursday_shift()`
    - Find nearest free slot within 7 days
    - Move league match to Sun/Mon when European match is on Thursday
    - Move league match to midweek when cup conflicts
    - Log original_date, new_date, reason
    - Refuse to reschedule locked events (is_locked=True)
    - Escalate to player-manager if no slot found within 7 days
    - _Requirements: 3.2, 3.3, 3.4, 3.7, 3.8, 3.9, 3.10, 6.3_

  - [x] 4.3 Implement holiday fixture locking
    - Mark mandatory fixture dates (Boxing Day, New Year) as is_locked=True, priority=9
    - Prevent rescheduling of locked events
    - _Requirements: 18.2, 18.6_

  - [ ]* 4.4 Write property tests for conflict resolution (Properties 9, 10, 11, 13, 21)
    - **Property 9: Conflict resolution with suggestion** — rejected placement returns suggested free date
    - **Property 10: Rescheduling audit trail** — rescheduled events have non-null original_date and reason
    - **Property 11: Locked event immutability** — reschedule refuses to move locked events
    - **Property 13: Overload detection** — 3+ matches in 7 days returns non-empty warnings
    - **Property 21: Holiday fixture locking** — mandatory fixtures have is_locked=True, priority=9
    - **Validates: Requirements 3.2, 3.5, 3.6, 3.7, 6.3, 17.1, 17.3, 18.6**

- [x] 5. Checkpoint — Core engine tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. WeatherGenerator service
  - [x] 6.1 Create `app/services/weather_generator.py`
    - Define `WeatherData` and `CityClimate` dataclasses
    - Implement `CLIMATE_PROFILES` dict with profiles for major football cities (London, Manchester, Munich, Madrid, Barcelona, Milan, Paris, Amsterdam, Lisbon, Istanbul, Glasgow, Brussels)
    - Implement `generate_weather(city, country, month, stadium_type)` returning `WeatherData`
    - Temperature within city's min/max range for month
    - Snow only for cold climates in Nov–Mar
    - Rain probability proportional to historical data
    - Pitch condition: "artificial" only if stadium_type is "artificial"; "frozen" in cold+winter; "muddy" if heavy rain; "wet" if rain; "dry" otherwise
    - Implement `get_climate_profile(city, country)` with fallback to country default
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 5.6, 5.7_

  - [ ]* 6.2 Write property test for weather generation (Property 14)
    - **Property 14: Weather generation bounds** — temperature in range, snow only cold+Nov-Mar, artificial pitch iff artificial stadium
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.6, 5.7**

- [x] 7. TravelPlanner service
  - [x] 7.1 Create `app/services/travel_planner.py`
    - Define `TravelPlan` dataclass
    - Implement `TravelPlanner` class with constants (BUS_THRESHOLD_KM=300, ARRIVAL_BUFFER_HOURS=3, POST_MATCH_HOURS=2)
    - Implement `plan_travel(home_city, away_city, kick_off_time, home_country, away_country)` returning `TravelPlan`
    - Bus if distance < 300km, plane otherwise
    - Departure = kick_off - travel_time - 3h buffer
    - Return = kick_off + 2h match + 2h post-match
    - Implement `estimate_distance(city_a, city_b, country_a, country_b)` with lookup table and fallback
    - Implement `validate_override(new_departure, kick_off_time, distance_km, transport_mode)` returning bool
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.6, 13.7_

  - [ ]* 7.2 Write property tests for travel planning (Properties 15, 16)
    - **Property 15: Travel timing validity** — bus if <300km, plane otherwise; arrival ≥3h before kick-off; return ≈ kick_off+4h
    - **Property 16: Travel override validation** — rejects override if arrival would be after kick-off
    - **Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.7**

- [x] 8. ReminderService
  - [x] 8.1 Create `app/services/reminder_service.py`
    - Define `Reminder` dataclass
    - Implement `ReminderService.__init__` accepting AsyncSession
    - Implement `generate_reminders_for_week(career_id, current_date)` — check next 7 days for: matches (2 days before → tactics review), transfer deadlines (7 days before), draws (1 day before), promise deadlines (within 7 days)
    - Prevent duplicate reminders for same event+type
    - Implement `dismiss_reminder(reminder_id)`
    - Implement `get_active_reminders(career_id)`
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

  - [ ]* 8.2 Write property test for reminder uniqueness (Property 19)
    - **Property 19: Reminder uniqueness** — calling generate_reminders_for_week multiple times never creates duplicates
    - **Validates: Requirements 11.6**

- [x] 9. Calendar API routes
  - [x] 9.1 Create `app/api/routes/calendar.py` with all endpoints
    - `GET /api/calendar/{career_id}/month` — query params: year, month, types (comma-separated), team (first_team/youth/loaned) → returns events list + next milestone countdown
    - `GET /api/calendar/{career_id}/day` — query param: date → returns detailed events for that day
    - `POST /api/calendar/{career_id}/template` — create/update recurring template
    - `GET /api/calendar/{career_id}/template` — get current templates
    - `DELETE /api/calendar/{career_id}/template/{template_id}` — delete template
    - `POST /api/calendar/{career_id}/template/{template_id}/apply` — apply template to month (query: month, year)
    - `PUT /api/calendar/{career_id}/event/{event_id}/travel-override` — override travel departure/mode
    - `GET /api/calendar/{career_id}/reminders` — get active reminders
    - `POST /api/calendar/{career_id}/reminders/{reminder_id}/dismiss` — dismiss reminder
    - `GET /api/calendar/{career_id}/international-break` — query param: date → called-up players and fixtures
    - Exclude cancelled events from all GET queries (is_cancelled=False)
    - _Requirements: 6.8, 7.1, 8.1, 9.1, 9.2, 9.3, 9.4, 9.5, 13.6, 14.2, 14.3_

  - [x] 9.2 Register calendar router in `app/main.py`
    - Import and include the calendar router with prefix `/api`
    - _Requirements: 6.5, 6.6_

  - [ ]* 9.3 Write unit tests for calendar API endpoints
    - Test GET month returns correct events filtered by type and team
    - Test GET day returns detailed event data including weather and travel
    - Test template CRUD operations
    - Test travel override validation (reject invalid, accept valid)
    - Test reminder dismiss
    - Test cancelled events excluded from results
    - _Requirements: 6.8, 9.5_

  - [ ]* 9.4 Write property test for soft deletion exclusion (Property 20)
    - **Property 20: Soft deletion exclusion** — events with is_cancelled=True never appear in query results
    - **Validates: Requirements 6.8**

- [x] 10. Checkpoint — Backend services and API complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Integration with career creation
  - [x] 11.1 Modify `app/api/routes/careers.py` `create_career()` to auto-generate calendar
    - After career is created, call `CalendarEngine.generate_season()` with the career's club, year, and league config
    - Seed league_configs table if empty (from static data in `app/data/league_configs.py`)
    - Generate weather data for all match events
    - Generate travel plans for all away matches
    - _Requirements: 1.1, 2.1, 5.1, 13.1_

- [x] 12. Frontend Calendar UI — monthly grid
  - [x] 12.1 Add Calendar UI section to `frontend/index.html`
    - Create monthly grid layout: 7-column grid (Mon–Sun), header with month/year and prev/next navigation
    - Render day cells with color-coded event dots per the design color scheme
    - Highlight current in-game day with distinct border
    - Display multiple event indicators per day
    - Display milestone banners as visual dividers
    - Display countdown to next milestone in header
    - Responsive layout for mobile (no horizontal scroll)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [x] 12.2 Implement day detail panel
    - On day click, show slide-in panel with all events for that day
    - Match events: opponent, kick-off time, stadium, competition, weather forecast
    - Training events: type, load (light/normal/heavy), participating squad
    - Deadline events: description, countdown timer
    - International call-up: player name, national team, match details
    - Medical events: player name, examination type, results
    - Navigation links to match preparation and training configuration screens
    - Pre-match day events grouped visually
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 12.6_

  - [x] 12.3 Implement filter panel and team selector
    - Toggle filters: matches, training, international breaks, transfer windows, medical, days off
    - Team selector dropdown: First Team, Youth Team, Loaned Players
    - Youth Team shows only youth squad events
    - Loaned Players shows loan return dates and loaned player match schedules
    - Persist filter/team state in session
    - Show "no events match filter" message when all hidden
    - Update grid immediately on filter change (no page reload)
    - Personal events displayed with distinct icon style
    - Contract expiry within 30 days highlighted with warning indicator
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 10.4, 10.6_

- [x] 13. Recurring templates — CRUD and apply
  - [x] 13.1 Implement template management UI
    - Weekly grid showing day-by-day assignments (Mon–Sun)
    - Create, edit, delete templates via API
    - Apply template to a selected month
    - Skip days with matches, international breaks, or locked events
    - Allow override of individual generated events without affecting template
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [x] 13.2 Implement template application logic in CalendarEngine
    - `apply_template(career_id, template_id, year, month)` — generate individual events for each applicable day
    - Skip days with higher-priority or locked events
    - Set template_id on generated events for traceability
    - _Requirements: 14.3, 14.4, 14.5_

  - [ ]* 13.3 Write property test for template priority respect (Property 18)
    - **Property 18: Template respects priority** — template events never placed on days with matches, international breaks, or locked events
    - **Validates: Requirements 14.3, 14.4**

- [x] 14. Auto-update logic — cup elimination and rescheduling
  - [x] 14.1 Implement `on_cup_elimination(career_id, competition_id)`
    - Mark all future cup fixtures as is_cancelled=True
    - Free associated dates for other events
    - Notify player-manager via ReminderService
    - _Requirements: 3.5, 17.1_

  - [x] 14.2 Implement `on_new_round_qualified(career_id, competition_id, round_dates, opponent_id)`
    - Add new fixture dates to calendar
    - Check for conflicts and reschedule if needed
    - _Requirements: 17.2_

  - [x] 14.3 Implement suspension and unavailability marking
    - On red card or accumulated yellows, mark player unavailable for relevant future match dates
    - On international duty, mark player unavailable for club selection
    - Apply 2-day recovery period after international return
    - _Requirements: 15.3, 15.5, 17.4_

  - [x] 14.4 Implement weather postponement rescheduling
    - When match postponed due to weather, find nearest available date and reschedule
    - Notify player-manager of all automatic changes
    - _Requirements: 17.6, 17.7_

  - [ ]* 14.5 Write property test for cup elimination cleanup (Property 12)
    - **Property 12: Cup elimination cleanup** — all future events for eliminated competition marked is_cancelled=True
    - **Validates: Requirements 3.5, 17.1**

- [x] 15. Integration with advance-week
  - [x] 15.1 Modify `app/api/routes/careers.py` `advance_week()` to trigger calendar recalculation
    - Call `CalendarEngine.recalculate_week(career_id, current_date)` on each week advance
    - Call `ReminderService.generate_reminders_for_week(career_id, current_date)`
    - Handle overload warnings and present to player-manager
    - Update weather for upcoming matches
    - Check milestone dates and trigger notifications
    - _Requirements: 11.7, 15.7, 16.5, 17.3, 17.5_

  - [x] 15.2 Implement international break synchronization
    - Display national team match dates for called-up players
    - Mark international duty days with flag icon in UI
    - Show called-up players list when international break selected
    - Handle injury during international duty (update status, notify)
    - _Requirements: 15.1, 15.2, 15.3, 15.5, 15.6, 15.7_

  - [ ]* 15.3 Write property test for pre-match day schedule (Property 17)
    - **Property 17: Pre-match day schedule** — day before match has prep events, no normal training; away matches have hotel check-in
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**

  - [ ]* 15.4 Write property test for season milestones completeness (Property 22)
    - **Property 22: Season milestones completeness** — all required milestone events exist in generated calendar
    - **Validates: Requirements 16.1, 16.4**

- [x] 16. Final checkpoint — Full integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The design uses Python (FastAPI + SQLAlchemy + hypothesis) throughout — no language selection needed
- Weather and travel data are stored as JSON strings in Text columns for SQLite compatibility
- All query methods must exclude is_cancelled=True events (soft deletion)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "2.1"] },
    { "id": 1, "tasks": ["3.1", "6.1", "7.1"] },
    { "id": 2, "tasks": ["3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "6.2", "7.2"] },
    { "id": 3, "tasks": ["3.8", "3.9", "4.1", "8.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "8.2"] },
    { "id": 5, "tasks": ["4.4", "9.1", "9.2"] },
    { "id": 6, "tasks": ["9.3", "9.4", "11.1"] },
    { "id": 7, "tasks": ["12.1", "13.1", "13.2"] },
    { "id": 8, "tasks": ["12.2", "12.3", "13.3"] },
    { "id": 9, "tasks": ["14.1", "14.2", "14.3", "14.4"] },
    { "id": 10, "tasks": ["14.5", "15.1", "15.2"] },
    { "id": 11, "tasks": ["15.3", "15.4"] }
  ]
}
```
