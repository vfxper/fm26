# Requirements Document

## Introduction

UEFA Champions League — модуль симуляции главного европейского клубного турнира в Football Manager 26. Турнир использует современный формат сезона 2024/25+: лиговую фазу (Swiss-system) с 36 участниками в единой таблице, плей-офф квалификацию, плей-офф (1/8, 1/4, 1/2 финала) с двухматчевыми противостояниями, и финал в одном матче на нейтральной площадке. Модуль создаёт календарные события для всех матчей турнира, использует существующий `MatchEngine` для симуляции, отображает события в существующей вкладке календаря фронтенда и сохраняет результаты, турнирные таблицы и сетку плей-офф в БД. Бэкенд: Python/FastAPI + SQLite + Alembic, фронтенд: HTML/JS.

---

## Glossary

- **UCL_Generator** — серверный Python-модуль (`app/services/ucl_generator.py`), генерирующий состав турнира, расписание лиговой фазы (Swiss-system) и сетку плей-офф.
- **UCL_Competition** — запись в таблице `competitions` с `competition_type=continental_cup` и `name="Champions League"`, представляющая один сезон турнира.
- **UCL_Round** — запись в таблице `competition_rounds` (новая), описывающая фазу турнира: `league_phase`, `knockout_playoff`, `round_of_16`, `quarter_final`, `semi_final`, `final`.
- **UCL_Standing** — запись в таблице `ucl_standings` (новая), хранящая позицию клуба в лиговой фазе (очки, разница мячей, ранг).
- **UCL_Tie** — запись в таблице `ucl_ties` (новая), описывающая двухматчевое противостояние (квалификация плей-офф, 1/8, 1/4, 1/2) с двумя клубами и агрегированным счётом.
- **League_Phase_Match** — один из 8 матчей клуба в лиговой фазе (4 дома, 4 на выезде) против 8 разных соперников.
- **Knockout_Playoff** — раунд квалификации плей-офф: команды с 9-го по 24-е места играют двухматчевый раунд за выход в 1/8 финала.
- **Two_Legged_Tie** — двухматчевое противостояние: первый матч у одного клуба дома, ответный — у другого; победитель определяется по сумме голов; при равенстве — правило выездного гола не применяется (формат 2024/25+), играется дополнительное время и серия пенальти.
- **Aggregate_Score** — суммарный счёт двухматчевого противостояния (`home_total` vs `away_total`, где home/away — клубы участники, не привязка к домашнему матчу).
- **Neutral_Venue** — нейтральная площадка финала (например, Puskás Aréna, Будапешт), не являющаяся домашним стадионом ни одного из финалистов.
- **Matchday** — дата проведения тура UCL (вторник или среда; финал — суббота).
- **Calendar_Event** — запись в существующей таблице `calendar_events` (event_type=`match`, priority=8, competition_id=UCL competition id), отображаемая в календаре игрока.
- **Match_Engine** — существующий сервис `app/services/match_engine.py`, симулирующий один матч (использует CA + домашнее преимущество).
- **Calendar_Engine** — существующий сервис `app/services/calendar_engine.py`, генерирующий клубный календарь.
- **CLUBS** — статический список клубов в `app/data/club_budgets.py` (1-based `club_id` = индекс + 1).
- **UCL_Participant** — один из 36 клубов, участвующих в текущем сезоне UCL.

---

## Requirements

### Requirement 1: Состав участников турнира

**User Story:** Как игрок, я хочу видеть в турнире 36 ведущих европейских клубов, чтобы соревнования соответствовали реальному формату Лиги чемпионов 2024/25+.

#### Acceptance Criteria

1. WHEN a new career is created, THE UCL_Generator SHALL create exactly one UCL_Competition record per season with `competition_type=continental_cup` and `num_teams=36`.
2. THE UCL_Generator SHALL register the following 36 clubs as UCL_Participants for the current season: Arsenal, Liverpool, Manchester City, Newcastle United, Tottenham Hotspur, Chelsea (England, 6); Athletic Bilbao, A. Madrid, Barcelona, Villarreal, R. Madrid (Spain, 5); Bayern Munich, Bayer Leverkusen, Borussia Dortmund, Eintracht Frankfurt (Germany, 4); Atalanta, Inter Milan, Juventus, Napoli (Italy, 4); Marseille, Monaco, Paris Saint-Germain (France, 3); Ajax, PSV Eindhoven (Netherlands, 2); Benfica, Sporting CP (Portugal, 2); Club Brugge, Union Saint-Gilloise (Belgium, 2); Bodø/Glimt, Galatasaray, Kairat, Qarabağ, Copenhagen, Olympiacos, Pafos, Slavia Prague (other 8).
3. THE UCL_Generator SHALL look up the `club_id` (1-based) of each UCL_Participant from the existing CLUBS list in `app/data/club_budgets.py` when the club is present there.
4. WHERE a UCL_Participant club is not present in the CLUBS list, THE UCL_Generator SHALL register the missing club name as a string-only participant identified by `club_name` while still allowing fixtures to be generated for that club.
5. THE UCL_Generator SHALL store the list of 36 UCL_Participants in a `ucl_participants` table linked to the UCL_Competition by `competition_id`.

---

### Requirement 2: Расписание лиговой фазы (Swiss-system)

**User Story:** Как игрок, я хочу, чтобы каждый клуб провёл 8 матчей лиговой фазы против 8 разных соперников (4 дома, 4 на выезде), чтобы расписание соответствовало формату 2024/25+.

#### Acceptance Criteria

1. THE UCL_Generator SHALL generate exactly 8 League_Phase_Matches for every UCL_Participant in the season.
2. THE UCL_Generator SHALL ensure each UCL_Participant plays against 8 distinct opponents in the league phase, with no opponent repeated.
3. THE UCL_Generator SHALL assign each UCL_Participant exactly 4 home matches and 4 away matches across the 8 league phase matches.
4. THE UCL_Generator SHALL distribute the 144 total league phase matches (36 clubs × 8 matches ÷ 2) across 8 matchdays, with 18 matches scheduled per matchday.
5. THE UCL_Generator SHALL schedule league phase matchdays only on Tuesday or Wednesday calendar dates.
6. THE UCL_Generator SHALL NOT schedule league phase matchdays on dates falling within FIFA international windows defined in `app/data/league_configs.py` `FIFA_INTERNATIONAL_WINDOWS`.
7. THE UCL_Generator SHALL place the 8 league phase matchdays between September and the end of January of the season year, separated by at least 14 days where international windows or holidays force gaps.
8. IF a UCL_Participant has a domestic league fixture scheduled on a Saturday adjacent to a UCL matchday, THE UCL_Generator SHALL NOT schedule that participant for two UCL matches within 48 hours of each other.

---

### Requirement 3: Турнирная таблица лиговой фазы

**User Story:** Как игрок, я хочу видеть единую турнирную таблицу из 36 клубов с очками, разницей мячей и местом, чтобы понимать положение своей команды.

#### Acceptance Criteria

1. THE UCL_Generator SHALL create one UCL_Standing record per UCL_Participant per season with initial values `played=0, won=0, drawn=0, lost=0, goals_for=0, goals_against=0, goal_difference=0, points=0`.
2. WHEN a League_Phase_Match is simulated and its result is persisted, THE UCL_Generator SHALL update the UCL_Standing of both participating clubs: 3 points for a win, 1 point for a draw, 0 points for a loss; goals scored and conceded SHALL be added to `goals_for` and `goals_against`.
3. THE UCL_Generator SHALL recompute `goal_difference` as `goals_for - goals_against` after every match.
4. THE UCL_Generator SHALL provide a method to return the league phase standings sorted by: (1) `points` descending, (2) `goal_difference` descending, (3) `goals_for` descending, (4) club name ascending.
5. WHEN all 8 matchdays of the league phase are completed, THE UCL_Generator SHALL assign final ranks 1 through 36 to UCL_Participants in the sorted order.

---

### Requirement 4: Квалификация плей-офф и сетка 1/8 финала

**User Story:** Как игрок, я хочу, чтобы команды с 1-го по 8-е места после лиговой фазы выходили напрямую в 1/8 финала, а команды с 9-го по 24-е играли квалификацию, чтобы соответствовать формату 2024/25+.

#### Acceptance Criteria

1. WHEN the league phase finishes, THE UCL_Generator SHALL classify clubs ranked 1-8 as direct qualifiers to the Round of 16.
2. WHEN the league phase finishes, THE UCL_Generator SHALL classify clubs ranked 9-24 as Knockout_Playoff participants.
3. WHEN the league phase finishes, THE UCL_Generator SHALL classify clubs ranked 25-36 as eliminated for the season.
4. THE UCL_Generator SHALL pair Knockout_Playoff participants such that each pair contains one club from rank range [9-16] (seeded) and one from [17-24] (unseeded), with the higher-seeded club playing the second leg at home.
5. THE UCL_Generator SHALL generate 8 Two_Legged_Ties for the Knockout_Playoff round, scheduled across 2 matchdays (first leg, second leg) separated by 7 days.
6. WHEN a Knockout_Playoff Two_Legged_Tie is decided, THE UCL_Generator SHALL place the winning club into the Round of 16 bracket.
7. THE UCL_Generator SHALL build the Round of 16 bracket by pairing direct qualifiers (ranks 1-8) with Knockout_Playoff winners according to a predetermined bracket map (1 vs lowest playoff winner, 2 vs second-lowest, etc.) such that the higher-seeded club plays the second leg at home.

---

### Requirement 5: Раунды плей-офф (1/8, 1/4, 1/2 финала)

**User Story:** Как игрок, я хочу, чтобы плей-офф проходил в формате двухматчевых противостояний с правильным учётом сумм голов, чтобы определить победителя пары.

#### Acceptance Criteria

1. THE UCL_Generator SHALL generate 8 Two_Legged_Ties for the Round of 16, 4 for the Quarter Finals, and 2 for the Semi Finals.
2. THE UCL_Generator SHALL schedule the first leg and second leg of every Two_Legged_Tie on Tuesday or Wednesday calendar dates separated by at least 7 days.
3. WHEN both legs of a Two_Legged_Tie are simulated, THE UCL_Generator SHALL compute the Aggregate_Score by summing each club's goals across both matches.
4. IF the Aggregate_Score is unequal, THEN THE UCL_Generator SHALL declare the club with more aggregate goals the winner.
5. IF the Aggregate_Score is equal after both legs, THEN THE UCL_Generator SHALL simulate 30 minutes of extra time during the second leg via Match_Engine, then a penalty shootout if still tied, and declare the shootout winner the tie winner.
6. WHEN a Two_Legged_Tie winner is determined, THE UCL_Generator SHALL place the winner into the next round's bracket according to a predetermined bracket map.
7. THE UCL_Generator SHALL NOT apply the away-goals rule (eliminated in real UEFA competition since 2021/22).

---

### Requirement 6: Финал на нейтральной площадке

**User Story:** Как игрок, я хочу, чтобы финал проходил в одном матче на заранее объявленной нейтральной площадке в фиксированную дату конца мая, чтобы передать атмосферу финала.

#### Acceptance Criteria

1. THE UCL_Generator SHALL generate exactly 1 Final fixture per season as a single-leg match (not a Two_Legged_Tie).
2. THE UCL_Generator SHALL schedule the Final on a fixed Saturday in late May of the season year, configurable via a `UCL_FINAL_DATE` constant (default: last Saturday of May).
3. THE UCL_Generator SHALL store the Final's venue as a Neutral_Venue identified by a venue name string (e.g., "Puskás Aréna, Budapest"), configurable via a `UCL_FINAL_VENUE` constant.
4. THE UCL_Generator SHALL mark both finalist clubs with neither `home_club_id` nor `away_club_id` corresponding to the Neutral_Venue's host club; the first-named club in the calendar event description SHALL be treated as the nominal home for kick-off purposes only.
5. WHEN the Final is simulated and ends in a draw after 90 minutes, THE UCL_Generator SHALL simulate 30 minutes of extra time and, if still tied, a penalty shootout to determine the winner.
6. WHEN the Final winner is determined, THE UCL_Generator SHALL update the UCL_Competition record with the champion club identifier and mark the competition as completed.

---

### Requirement 7: Интеграция с календарём

**User Story:** Как игрок, я хочу видеть все матчи Лиги чемпионов в существующем календаре наряду с матчами лиги, чтобы планировать сезон в одном месте.

#### Acceptance Criteria

1. WHEN UCL fixtures are generated, THE UCL_Generator SHALL insert one Calendar_Event per UCL match into the `calendar_events` table.
2. THE UCL_Generator SHALL set `event_type="match"`, `priority=8`, `competition_id=<UCL competition id>`, and `kick_off_time="21:00"` on every UCL Calendar_Event.
3. WHEN the UCL_Participant is the player's club, THE UCL_Generator SHALL set `home_club_id=player_club_id` for home matches and `away_club_id=player_club_id` for away matches, mirroring the existing convention used by `Calendar_Engine.generate_season()` for league fixtures.
4. THE UCL_Generator SHALL set the `description` field on every UCL Calendar_Event using the format `"Лига чемпионов, {round_label}: vs {opponent_name} {home_away_tag}"` for matches involving the player's club, where `{round_label}` is one of `"тур 1"`...`"тур 8"`, `"квалификация плей-офф"`, `"1/8 финала"`, `"1/4 финала"`, `"1/2 финала"`, `"финал"`, and `{home_away_tag}` is `"(H)"` for home or `"(A)"` for away matches.
5. THE UCL_Generator SHALL set the `description` field on UCL Calendar_Events not involving the player's club using the format `"Champions League {round_label}: {home_club_name} vs {away_club_name}"`, where `{round_label}` is the English equivalent (e.g., `"Matchday 1"`, `"Round of 16"`, `"Quarter Final"`, `"Final"`).
6. THE UCL_Generator SHALL set `description` on the Final Calendar_Event using the format `"Лига чемпионов, финал: {finalist_a} vs {finalist_b} ({neutral_venue})"`.
7. THE UCL_Generator SHALL ensure the existing endpoint `POST /api/calendar/{career_id}/match/{event_id}/simulate` can parse the opponent name from the UCL Calendar_Event description by including the substring `"vs {opponent_name} (H)"` or `"vs {opponent_name} (A)"` for matches involving the player's club.

---

### Requirement 8: Симуляция матчей UCL

**User Story:** Как игрок, я хочу симулировать матчи Лиги чемпионов через ту же кнопку «Пропустить (авто)», что и матчи лиги, чтобы получать счёт и поминутные события.

#### Acceptance Criteria

1. WHEN the player clicks the "⏭ Пропустить (авто)" button on a UCL Calendar_Event in the calendar tab, THE existing `POST /api/calendar/{career_id}/match/{event_id}/simulate` endpoint SHALL invoke `MatchEngine.simulate_match(home_id, away_id, home_name, away_name)` and return the resulting `MatchResult`.
2. WHEN a UCL match is simulated successfully, THE UCL_Generator SHALL persist the home and away scores into the relevant UCL_Standing (for league phase) or UCL_Tie (for knockout) records.
3. WHEN the player clicks the "▶ Играть матч" button on a UCL Calendar_Event, THE frontend SHALL display an alert with the message `"Движок в разработке, попробуйте через несколько дней"` and SHALL NOT trigger any backend simulation.
4. WHEN a UCL match simulation completes, THE existing simulate endpoint SHALL update the Calendar_Event `description` to include the final score in the format `"{home_team} {home_score} - {away_score} {away_team}"` and set `is_locked=1`, mirroring its current behaviour for league matches.
5. WHEN a UCL knockout match simulation completes, THE UCL_Generator SHALL recompute the Aggregate_Score on the parent UCL_Tie if the second leg has been played, and SHALL determine the tie winner per Requirements 5.4 and 5.5.

---

### Requirement 9: Хранение состояния турнира

**User Story:** Как разработчик, я хочу, чтобы состояние Лиги чемпионов (таблица, сетка, результаты) сохранялось в БД, чтобы данные пережили перезапуск сервера.

#### Acceptance Criteria

1. THE UCL_Generator SHALL create a new `competition_rounds` table with columns: `id`, `competition_id`, `round_type` (one of `league_phase`, `knockout_playoff`, `round_of_16`, `quarter_final`, `semi_final`, `final`), `round_order`, `start_date`, `end_date`, `is_completed`.
2. THE UCL_Generator SHALL create a new `ucl_participants` table with columns: `id`, `competition_id`, `club_id` (nullable for non-CLUBS clubs), `club_name`, `seed`, `final_rank`.
3. THE UCL_Generator SHALL create a new `ucl_standings` table with columns: `id`, `competition_id`, `participant_id`, `played`, `won`, `drawn`, `lost`, `goals_for`, `goals_against`, `goal_difference`, `points`, `rank`.
4. THE UCL_Generator SHALL create a new `ucl_ties` table with columns: `id`, `competition_id`, `round_id`, `home_participant_id`, `away_participant_id`, `leg1_home_score`, `leg1_away_score`, `leg2_home_score`, `leg2_away_score`, `aggregate_home`, `aggregate_away`, `winner_participant_id`, `winner_decided_by` (one of `aggregate`, `extra_time`, `penalties`), `bracket_position`.
5. THE UCL_Generator SHALL provide an Alembic migration script that creates all four new tables (`competition_rounds`, `ucl_participants`, `ucl_standings`, `ucl_ties`) with appropriate foreign keys to `competitions(id)` (ON DELETE CASCADE) and indexes on `competition_id`.
6. WHEN a UCL match result is persisted, THE UCL_Generator SHALL update the corresponding `ucl_standings` (league phase) or `ucl_ties` (knockout) row in the same database transaction as the Calendar_Event update.

---

### Requirement 10: Интеграция с созданием карьеры

**User Story:** Как игрок, я хочу, чтобы Лига чемпионов автоматически создавалась при старте новой карьеры, чтобы не требовалось ручной настройки.

#### Acceptance Criteria

1. WHEN a new career is created via `POST /api/careers`, THE existing career creation flow SHALL invoke `UCLGenerator.generate_competition(career_id, year)` after `CalendarEngine.generate_season()` completes.
2. IF `UCLGenerator.generate_competition()` raises an exception, THEN THE career creation flow SHALL log the error and continue without aborting the career creation, mirroring the existing pattern used by `CalendarEngine.generate_season()` failures in `app/api/routes/careers.py`.
3. THE UCL_Generator SHALL produce a deterministic schedule for the same career_id, year, and seed inputs, supporting reproducible test execution.
4. THE UCL_Generator SHALL skip generation if a UCL_Competition already exists for the given career_id and season year, returning the existing competition record.

---

### Requirement 11: Отображение во фронтенде

**User Story:** Как игрок, я хочу, чтобы матчи UCL отображались в существующей вкладке календаря с теми же кнопками действий, что и матчи лиги, чтобы интерфейс был единообразным.

#### Acceptance Criteria

1. THE existing calendar tab in `frontend/index.html` SHALL display UCL Calendar_Events alongside league Calendar_Events without requiring frontend code changes specific to UCL events.
2. WHEN the player opens the day-detail panel for a date with a UCL match, THE existing day-detail rendering SHALL show the description, kick-off time, and the same `"▶ Играть матч"` and `"⏭ Пропустить (авто)"` buttons as for league matches.
3. WHEN the player clicks `"⏭ Пропустить (авто)"` on a UCL match, THE frontend SHALL call `POST /api/calendar/{career_id}/match/{event_id}/simulate` and render the returned score and minute-by-minute events using the existing `showMatchResult()` function.
4. WHEN the player clicks `"▶ Играть матч"` on a UCL match, THE frontend SHALL display the alert `"Движок в разработке, попробуйте через несколько дней"` without invoking any backend endpoint.

---

### Requirement 12: Обработка ошибок и граничных случаев

**User Story:** Как разработчик, я хочу, чтобы модуль корректно обрабатывал отсутствующие данные и состояния гонки, чтобы система оставалась стабильной.

#### Acceptance Criteria

1. IF the league phase pairing algorithm cannot produce a valid 8-match-per-club schedule for any reason, THEN THE UCL_Generator SHALL raise a `UCLScheduleError` exception with a descriptive message identifying the participant and constraint that failed.
2. IF a UCL match Calendar_Event references a club that cannot be resolved to a `club_id` in CLUBS, THEN THE existing simulate endpoint SHALL return HTTP 400 with the message `"Opponent club not found in CLUBS list"`.
3. IF a Two_Legged_Tie's second leg is simulated before the first leg, THEN THE UCL_Generator SHALL log a warning and compute the Aggregate_Score using only the played leg's scores until the missing leg is simulated.
4. IF `MatchEngine.simulate_match()` raises an exception during a UCL match simulation, THEN the simulate endpoint SHALL return HTTP 500 with the original error message and SHALL NOT modify the Calendar_Event description or the UCL_Standing/UCL_Tie records.
5. THE UCL_Generator SHALL NOT generate UCL fixtures on dates that already contain a `priority>=10` (locked international or holiday) Calendar_Event for the player's club.
