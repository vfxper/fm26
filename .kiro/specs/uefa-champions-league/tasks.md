# Implementation Plan: UEFA Champions League

## Overview

Implement the UEFA Champions League competition simulation following the modern (2024/25+) format: 36-club Swiss-system league phase, 8-team knockout playoff round, two-legged Round of 16 / Quarter Finals / Semi Finals, single-leg Final at a fixed neutral venue. Reuse existing `MatchEngine` for simulation and the existing `calendar_events` table + `POST /api/calendar/{career_id}/match/{event_id}/simulate` endpoint for the player's match interaction. Implementation is in Python (matching the rest of the codebase) with FastAPI + SQLAlchemy + raw SQL for SQLite compatibility, plus an Alembic migration for the four new tables.

## Tasks

- [x] 1. Database schema: new tables and migration
  - [x] 1.1 Add four UCL tables to `run_local.py` `create_tables()`
    - Add `competition_rounds` table: id, competition_id (FK competitions, CASCADE), round_type, round_order, start_date, end_date, is_completed, created_at
    - Add `ucl_participants` table: id, competition_id (FK competitions, CASCADE), club_id (nullable), club_name, country, seed, final_rank
    - Add `ucl_standings` table: id, competition_id (FK competitions, CASCADE), participant_id (FK ucl_participants, CASCADE), played, won, drawn, lost, goals_for, goals_against, goal_difference, points, rank
    - Add `ucl_ties` table: id, competition_id (FK competitions, CASCADE), round_id (FK competition_rounds, CASCADE), home_participant_id, away_participant_id, leg1_home_score, leg1_away_score, leg2_home_score, leg2_away_score, aggregate_home, aggregate_away, winner_participant_id, winner_decided_by, bracket_position
    - Add indexes: `idx_comp_rounds_comp`, `idx_comp_rounds_comp_order` (unique), `idx_ucl_part_comp`, `idx_ucl_part_comp_seed` (unique), `idx_ucl_stand_comp`, `idx_ucl_stand_comp_part` (unique), `idx_ucl_tie_comp`, `idx_ucl_tie_round`, `idx_ucl_tie_round_pos` (unique)
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 1.2 Create Alembic migration `alembic/versions/20260520_*-add_ucl_tables.py`
    - `upgrade()` creates all four tables with the same schema as task 1.1
    - `upgrade()` creates the same indexes
    - `downgrade()` drops all indexes and tables in reverse order
    - Down-revision must point to the latest existing migration
    - _Requirements: 9.5_

- [x] 2. ORM models for the four new tables
  - [x] 2.1 Create `app/models/competition_round.py` with `CompetitionRound` model
    - Mapped columns matching the schema in task 1.1
    - `__table_args__` includes the two indexes
    - _Requirements: 9.1_

  - [x] 2.2 Create `app/models/ucl_participant.py` with `UCLParticipant` model
    - Mapped columns matching the schema; `club_id` nullable; `seed` and `country` not null
    - `__table_args__` includes both indexes
    - _Requirements: 9.2, 1.4_

  - [x] 2.3 Create `app/models/ucl_standing.py` with `UCLStanding` model
    - Mapped columns matching the schema; all counters default to 0; `rank` nullable
    - `__table_args__` includes both indexes
    - _Requirements: 9.3, 3.1_

  - [x] 2.4 Create `app/models/ucl_tie.py` with `UCLTie` model
    - Mapped columns matching the schema; all score columns nullable until played
    - `winner_decided_by` constrained to one of `aggregate`, `extra_time`, `penalties`, `single_match`
    - `__table_args__` includes the three indexes
    - _Requirements: 9.4, 5.3_

- [x] 3. UCL static configuration data
  - [x] 3.1 Create `app/data/ucl_config.py` with all UCL constants
    - `UCL_PARTICIPANTS: list[tuple[str, int | None, str]]` of exactly 36 entries; each entry is `(display_name, club_id_or_None, country)`; `assert len(UCL_PARTICIPANTS) == 36`
    - `UCL_LEAGUE_PHASE_TARGETS` — 8 tuples `(month, week_of_month, weekday)` for league phase target dates
    - `UCL_KO_PLAYOFF_BASE_MONTH = 2`, `UCL_KO_PLAYOFF_LEG_GAP_DAYS = 7`
    - `UCL_R16_LEG1_MONTH = 3`, `UCL_QF_LEG1_MONTH = 4`, `UCL_SF_LEG1_MONTH = 4`
    - `UCL_FINAL_VENUE = "Puskás Aréna, Budapest"`
    - `get_final_date(year: int) -> date` returns last Saturday of May for the given year
    - `UCL_R16_BRACKET_MAP: dict[int, int]` mapping seed (1-8) to playoff-winner index (1-8)
    - For clubs that exist in `app.data.club_budgets.CLUBS`, look up the 1-based index and store; for clubs not in CLUBS (Bodø/Glimt, Kairat, Qarabağ, Copenhagen, Olympiacos, Pafos, Slavia Prague, Club Brugge, Union Saint-Gilloise) use `None`
    - _Requirements: 1.2, 1.3, 1.4, 6.2, 6.3_

- [x] 4. UCLGenerator core: skeleton, dataclasses, and competition setup
  - [x] 4.1 Create `app/services/ucl_generator.py` with class skeleton
    - Define `UCLScheduleError(Exception)`
    - Define `Participant`, `StandingRow`, `TieResult` dataclasses matching the design
    - Define `UCLGenerator.__init__(session, rng=None)` accepting an optional `random.Random` for determinism
    - _Requirements: 10.3, 12.1_

  - [x] 4.2 Implement `generate_competition(career_id, year, player_club_id)` setup steps
    - Idempotency check: query `competitions` by `(career_id is implicit via not stored — store via name+season+country)` actually store `season=year` and `name='Champions League'`; if a row already exists, return its `id` without creating duplicates
    - Insert one `competitions` row with `competition_type='continental_cup'`, `name='Champions League'`, `season=year`, `country='Europe'`, `num_teams=36`
    - Insert 36 `ucl_participants` rows from `UCL_PARTICIPANTS`, assigning seed 1-36 in order
    - Insert 6 `competition_rounds` rows: `league_phase` (order=1), `knockout_playoff` (2), `round_of_16` (3), `quarter_final` (4), `semi_final` (5), `final` (6)
    - Initialise 36 `ucl_standings` rows (all counters 0, rank NULL)
    - Return the new `competition_id`
    - _Requirements: 1.1, 1.5, 3.1, 9.6, 10.4_

  - [x] 4.3 Implement `_resolve_participant_club_id(participant_id) -> int | None`
    - Helper: given a `ucl_participants.id`, return `club_id` (1-based CLUBS index) or None
    - Used by calendar event creation to populate `home_club_id` / `away_club_id`
    - _Requirements: 1.3, 1.4_

- [x] 5. UCLGenerator: Swiss-system league phase pairings
  - [x] 5.1 Implement `build_swiss_pairings(participants) -> list[list[tuple[int, int]]]`
    - Split 36 participants into 4 pots of 9 by seed (pot 1: seeds 1-9, pot 2: 10-18, pot 3: 19-27, pot 4: 28-36)
    - For each participant, draw 2 opponents from each of the 4 pots: 1 home, 1 away
    - Ensure no duplicate opponents per participant; ensure 8 distinct opponents total
    - Use a graph-coloring assignment to spread the 8 pairings of each participant across 8 matchdays so no participant appears twice on a matchday
    - Validate post-conditions before returning: every participant has exactly 8 distinct opponents, 4 home, 4 away; each matchday has exactly 18 matches; total 144 matches
    - Raise `UCLScheduleError` if any post-condition fails
    - Use `self.rng` for all random choices to support determinism
    - Return 8 lists of `(home_participant_id, away_participant_id)` tuples
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 10.3, 12.1_

  - [x] 5.2 Implement `assign_matchdays_to_dates(matchdays, year, blocked_ranges) -> list[date]`
    - For each entry in `UCL_LEAGUE_PHASE_TARGETS`, compute the target date for the season (year for September-December, year+1 for January)
    - If the target date falls within any FIFA international window or any range in `blocked_ranges`, shift by ±1 day up to ±2 days; if still blocked, shift up to ±7 days within Tuesday/Wednesday only
    - Ensure the assigned date weekday is Tuesday (1) or Wednesday (2)
    - Return the 8 chosen dates in matchday order
    - _Requirements: 2.5, 2.6, 2.7_

  - [x]* 5.3 Write property test for Swiss-system pairing invariants
    - **Property 1: Swiss-system pairing invariants**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

  - [x]* 5.4 Write property test for schedule date constraints
    - **Property 2: Schedule date constraints**
    - **Validates: Requirements 2.5, 2.6, 2.7, 2.8, 5.2**

  - [x]* 5.5 Write property test for schedule determinism
    - **Property 12: Schedule determinism**
    - **Validates: Requirement 10.3**

- [x] 6. UCLGenerator: insert league phase calendar events
  - [x] 6.1 Implement `_insert_league_phase_events(competition_id, pairings, dates, player_club_id)`
    - For each matchday i (1-8) and each pairing `(home_pid, away_pid)`:
      - Resolve `home_club_id` and `away_club_id` via `_resolve_participant_club_id`
      - Build description via `_build_event_description(round_type='league_phase', matchday=i, ...)` — Russian for player's club, English otherwise
      - Insert `calendar_events` row with `event_type='match'`, `priority=8`, `kick_off_time='21:00'`, `competition_id=competition_id`, `event_date=dates[i-1]`, `is_locked=0`, `is_cancelled=0`
    - Skip dates that already have a `priority>=10` event for the player's club (Requirement 12.5); reschedule per task 5.2 fallback
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 12.5_

  - [x] 6.2 Implement `_build_event_description(round_type, matchday, leg, player_club_id, home_club_name, away_club_name, is_player_home, opponent_name, neutral_venue=None)`
    - For matches involving player's club: `f"Лига чемпионов, {round_label}: vs {opponent_name} {tag}"` where tag is `(H)` or `(A)` and `round_label` maps `league_phase`+matchday→`"тур N"`, `knockout_playoff`+leg→`"квалификация плей-офф (матч N)"`, `round_of_16`+leg→`"1/8 финала (матч N)"`, `quarter_final`+leg→`"1/4 финала (матч N)"`, `semi_final`+leg→`"1/2 финала (матч N)"`, `final`→`"финал"`
    - For non-player matches: `f"Champions League {english_round_label}: {home_club_name} vs {away_club_name}"`
    - For final: `f"Лига чемпионов, финал: {home_club_name} vs {away_club_name} ({neutral_venue})"`
    - Returns the description string
    - _Requirements: 7.4, 7.5, 7.6_

  - [x]* 6.3 Write property test for calendar event invariants
    - **Property 8: Calendar event invariants**
    - **Validates: Requirements 7.1, 7.2, 7.3**

  - [x]* 6.4 Write property test for description round-trip
    - **Property 9: Description round-trip**
    - **Validates: Requirements 7.4, 7.5, 7.6, 7.7**

  - [x]* 6.5 Write property test for locked-date avoidance
    - **Property 11: Locked-date avoidance**
    - **Validates: Requirement 12.5**

- [x] 7. Checkpoint — League phase generation works end-to-end
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. UCLGenerator: standings updates
  - [x] 8.1 Implement `update_standing(competition_id, home_pid, away_pid, home_score, away_score)`
    - Fetch both standings rows for the participants
    - Increment `played +1`; for the winner increment `won +1` and add 3 points; for the loser increment `lost +1`; for a draw increment `drawn +1` and add 1 point each
    - Add `home_score` to home's `goals_for` and to away's `goals_against`; mirror for away score
    - Recompute `goal_difference = goals_for - goals_against`
    - Recompute ranks 1-36 across all 36 standings rows by sorting `(points DESC, goal_difference DESC, goals_for DESC, club_name ASC)` and writing the rank column
    - Wrap all updates in a single transaction with the calendar event update (Requirement 9.6)
    - _Requirements: 3.2, 3.3, 9.6_

  - [x] 8.2 Implement `get_league_phase_table(competition_id) -> list[StandingRow]`
    - Query `ucl_standings` joined with `ucl_participants` for the competition
    - Order by `(points DESC, goal_difference DESC, goals_for DESC, club_name ASC)`
    - Return list of `StandingRow` dataclasses
    - _Requirements: 3.4_

  - [x]* 8.3 Write property test for standings consistency
    - **Property 3: Standings consistency**
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5**

- [x] 9. UCLGenerator: knockout phase setup
  - [x] 9.1 Implement `finalize_league_phase(competition_id)`
    - Recompute final ranks 1-36 and write to `ucl_participants.final_rank`
    - Mark `competition_rounds.league_phase` row as `is_completed=true`
    - Pair ranks [9-16] with ranks [17-24]: bracket_position 1 pairs rank 9 with rank 24, position 2 pairs 10 with 23, etc. (or per a documented mapping); the high-seeded participant becomes `home_participant_id` (plays leg 2 at home)
    - Update the 8 `ucl_ties` placeholder rows for `knockout_playoff` round with the resolved `home_participant_id` and `away_participant_id`
    - Schedule first leg and second leg dates (mid-February target, separated by `UCL_KO_PLAYOFF_LEG_GAP_DAYS = 7`)
    - Insert 16 `calendar_events` rows for the knockout playoff (8 first legs + 8 second legs)
    - _Requirements: 3.5, 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 9.2 Implement `build_round_of_16(competition_id)`
    - Verify all 8 `knockout_playoff` ties have winners; raise if not
    - Pair ranks [1-8] with the 8 playoff winners using `UCL_R16_BRACKET_MAP` (seed 1 vs lowest playoff winner, seed 2 vs next-lowest, etc.); high-seed plays leg 2 at home
    - Update 8 `round_of_16` placeholder ties with `home_participant_id` and `away_participant_id`
    - Schedule first leg and second leg dates (early March target, separated by 7 days)
    - Insert 16 `calendar_events` rows
    - _Requirements: 4.7, 5.1, 5.2_

  - [x] 9.3 Implement `advance_bracket(competition_id, from_round)`
    - Generic helper: when all ties of `from_round` have winners, pair them per bracket_position to populate `to_round` placeholders
    - Schedule first leg and second leg dates per `UCL_QF_LEG1_MONTH` / `UCL_SF_LEG1_MONTH`
    - Insert calendar events for the new round (8 events for QF, 4 events for SF)
    - For the special case `from_round='semi_final' → to_round='final'`, insert 1 single-leg calendar event on `get_final_date(year+1)` with the neutral venue in the description
    - _Requirements: 4.6, 5.1, 5.2, 5.6, 6.1, 6.2, 6.3_

  - [x]* 9.4 Write property test for qualifier classification by rank
    - **Property 4: Qualifier classification by rank**
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [x]* 9.5 Write property test for knockout bracket pairing invariants
    - **Property 5: Knockout bracket pairing invariants**
    - **Validates: Requirements 4.4, 4.7, 5.1**

  - [x]* 9.6 Write property test for bracket winner advancement
    - **Property 6: Bracket winner advancement**
    - **Validates: Requirements 4.6, 5.6**

  - [x]* 9.7 Write property test for final scheduling
    - **Property 10: Final scheduled on last Saturday of May**
    - **Validates: Requirement 6.2**

- [x] 10. UCLGenerator: tie resolution and result persistence
  - [x] 10.1 Implement `_resolve_tie(tie) -> TieResult`
    - Compute `aggregate_home = leg1_home_score + leg2_away_score`
    - Compute `aggregate_away = leg1_away_score + leg2_home_score`
    - If `aggregate_home > aggregate_away`: winner is `home_participant_id`, `winner_decided_by='aggregate'`
    - If `aggregate_away > aggregate_home`: winner is `away_participant_id`, `winner_decided_by='aggregate'`
    - If aggregates are equal: simulate 30-min extra time during second leg by sampling additional minutes from MatchEngine output (or via a simplified ET goal-probability function), then a penalty shootout if still tied; set `winner_decided_by='extra_time'` or `'penalties'`
    - Do NOT apply the away-goals rule (Requirement 5.7)
    - Return a `TieResult` dataclass
    - _Requirements: 5.3, 5.4, 5.5, 5.7_

  - [x] 10.2 Implement `persist_match_result(competition_id, calendar_event_id, home_pid, away_pid, home_score, away_score, round_type, leg)`
    - For `round_type='league_phase'`: call `update_standing` and return None
    - For knockout rounds: load the corresponding `ucl_ties` row; if `leg==1`, set `leg1_home_score`/`leg1_away_score`; if `leg==2`, set `leg2_home_score`/`leg2_away_score`; if both legs played, call `_resolve_tie`, update `aggregate_home`, `aggregate_away`, `winner_participant_id`, `winner_decided_by`, then call `advance_bracket(competition_id, round_type)` if all ties of the round are now decided
    - For `round_type='final'`: handle as a single match; if drawn, simulate ET + penalties; call `crown_champion(competition_id, winner)` on completion
    - All updates wrapped in a single transaction (Requirement 9.6)
    - If only one leg played, log a warning per Requirement 12.3 and return None
    - _Requirements: 6.5, 6.6, 8.2, 8.5, 9.6, 12.3_

  - [x] 10.3 Implement `crown_champion(competition_id, winner_participant_id)`
    - Update `competitions.is_completed = true` for the row
    - Optionally store the champion's `participant_id` in a new column on `competitions` or as a notes/JSON field — use the existing `to_dict` patterns
    - Mark `competition_rounds.final` row as `is_completed=true`
    - _Requirements: 6.6_

  - [x]* 10.4 Write property test for two-legged tie resolution
    - **Property 7: Two-legged tie resolution**
    - **Validates: Requirements 5.3, 5.4, 5.5, 5.7, 6.5, 8.5**

- [x] 11. Checkpoint — Knockout bracket and tie resolution work
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Integration: extend the existing simulate endpoint to persist UCL state
  - [x] 12.1 Modify `simulate_match_event` in `app/api/routes/calendar.py`
    - After `MatchEngine.simulate_match` returns and the calendar event description is updated, query the `competition_id` from the calendar event
    - If `competition_id` is set and the corresponding `competitions` row has `competition_type='continental_cup'` and `name='Champions League'`:
      - Resolve `home_participant_id` and `away_participant_id` from `ucl_participants` using `(competition_id, club_id or club_name)`
      - Determine `round_type` and `leg` by inspecting the description (`"тур N"`, `"квалификация плей-офф (матч N)"`, `"1/8 финала (матч N)"`, `"1/4 финала (матч N)"`, `"1/2 финала (матч N)"`, `"финал"`) — write a helper `_parse_ucl_round_from_description(description)`
      - Call `UCLGenerator(db).persist_match_result(...)` with the parsed values
    - Wrap the UCL persistence call in try/except — on failure, return HTTP 500 with the original error and DO NOT modify the standings/ties (Requirement 12.4); the calendar event description update SHALL remain intact since it was committed earlier
    - _Requirements: 8.1, 8.2, 8.4, 12.4_

  - [x] 12.2 Add HTTP 400 handling for unresolved opponent
    - In `simulate_match_event`, after parsing opponent name from description, if `opponent_club_id == 0` AND the event is a UCL event, raise `HTTPException(400, "Opponent club not found in CLUBS list")`
    - For non-UCL events keep the existing fallback behaviour to avoid regressing league simulation
    - _Requirements: 12.2_

  - [x]* 12.3 Write integration tests for UCL simulation flow
    - Test simulating a league phase match updates `ucl_standings` correctly
    - Test simulating both legs of a knockout tie computes the aggregate and writes a winner
    - Test simulating the final crowns a champion
    - Test that a 500 error from `MatchEngine` returns HTTP 500 and does not modify standings
    - Test that an unresolved opponent returns HTTP 400
    - _Requirements: 8.1, 8.2, 8.4, 12.2, 12.4_

- [x] 13. Integration: hook UCLGenerator into career creation
  - [x] 13.1 Modify `create_career` in `app/api/routes/careers.py`
    - After the existing `CalendarEngine.generate_season(...)` block (around line 193-200), add a new try/except that calls `UCLGenerator(db).generate_competition(career_id, year=2025, player_club_id=request.club_id)`
    - On exception, log a warning and continue (mirrors the existing pattern)
    - _Requirements: 10.1, 10.2_

  - [x]* 13.2 Write unit test for idempotent generation
    - Call `generate_competition` twice for the same career_id+year; assert only one `competitions` row exists and the same `id` is returned
    - _Requirements: 10.4_

- [x] 14. Frontend: verify UCL events render correctly (no code changes expected)
  - [x] 14.1 Manually verify in `frontend/index.html` that the existing day-detail panel renders UCL events with the same buttons as league matches
    - The existing `onDayClick` already injects `▶ Играть матч` and `⏭ Пропустить (авто)` for any `event_type === 'match'`
    - Confirm UCL events have `event_type='match'` so no JS changes are needed
    - The `▶ Играть матч` button already shows the alert `"Движок в разработке, попробуйте через несколько дней"` — confirm UCL events get the same alert
    - The `⏭ Пропустить (авто)` button already calls `simulateMatchEvent(ev.id)` which posts to the simulate endpoint — confirm score and minute-by-minute events render via `showMatchResult(data)`
    - This task is non-coding (verification only) and should be confirmed by reading the existing frontend and matching it against the requirements; no code is committed unless a regression is found
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 15. Final checkpoint — Full UCL flow works end-to-end
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP — they are property tests, integration tests, or unit tests.
- Each task references specific requirements for traceability.
- Checkpoints ensure incremental validation.
- Property tests validate universal correctness properties from the design document; each property test runs ≥100 iterations via Hypothesis.
- The frontend (task 14) is verification-only — no code changes expected because the existing calendar tab already handles `event_type='match'` events generically.
- Task 12.2 (HTTP 400 for unresolved opponent) intentionally limits the new behaviour to UCL events to avoid regressing the existing league-match simulation path.
- The existing simulate endpoint already commits the calendar event description update before any UCL persistence runs — this is intentional so that on UCL persistence failure the user still sees the score in their calendar (Requirement 12.4 covers the standings/ties rollback case).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "3.1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3"] },
    { "id": 3, "tasks": ["5.1", "5.2"] },
    { "id": 4, "tasks": ["5.3", "5.4", "5.5", "6.1", "6.2"] },
    { "id": 5, "tasks": ["6.3", "6.4", "6.5"] },
    { "id": 6, "tasks": ["8.1", "8.2"] },
    { "id": 7, "tasks": ["8.3", "9.1", "9.2", "9.3"] },
    { "id": 8, "tasks": ["9.4", "9.5", "9.6", "9.7"] },
    { "id": 9, "tasks": ["10.1", "10.2", "10.3"] },
    { "id": 10, "tasks": ["10.4", "12.1", "12.2"] },
    { "id": 11, "tasks": ["12.3", "13.1"] },
    { "id": 12, "tasks": ["13.2", "14.1"] }
  ]
}
```
