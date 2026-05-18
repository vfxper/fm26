# Requirements Document

## Introduction

Club Calendar and Schedule — система автоматической генерации и управления клубным календарём для Football Manager 26. При выборе клуба и старте карьеры система генерирует полный сезонный календарь с учётом приоритетов (международные окна → еврокубки → лига → кубки → товарищеские матчи), управляет конфликтами дат, отображает события в интерактивном месячном виде с цветовой кодировкой, и автоматически обновляет расписание при изменениях (вылет из кубка, перенос матчей). Бэкенд: Python/FastAPI + SQLite, фронтенд: HTML/JS.

---

## Glossary

- **Calendar_Engine** — серверный Python-модуль, генерирующий и управляющий сезонным календарём клуба.
- **Calendar_UI** — клиентский JavaScript-модуль, отображающий календарь в виде месячной сетки с интерактивными элементами.
- **Calendar_Event** — запись в таблице `calendar_events`, представляющая одно событие (матч, тренировка, дедлайн, международный перерыв).
- **Season_Block** — структурный блок сезона (предсезонка, первая половина, зимний перерыв, вторая половина, завершение сезона).
- **Date_Blocker** — механизм блокировки дат для предотвращения конфликтов расписания.
- **Priority_Level** — числовое значение приоритета события (0–10), определяющее порядок размещения в календаре.
- **Reschedule_Engine** — подмодуль Calendar_Engine, отвечающий за автоматический перенос матчей при конфликтах.
- **Weather_Generator** — модуль генерации погодных условий на основе климата города и времени года.
- **Reminder_System** — модуль уведомлений о предстоящих событиях.
- **Travel_Planner** — модуль автоматического планирования поездок на выездные матчи.
- **Recurring_Template** — шаблон повторяющихся событий (еженедельное расписание тренировок).
- **International_Window** — период международных матчей, когда вызванные игроки недоступны для клуба.
- **Competition_Engine** — существующий модуль соревнований (лига, кубки, еврокубки).
- **Career_Manager** — существующий модуль управления карьерой менеджера.
- **Filter_Panel** — панель фильтрации событий в Calendar_UI.
- **Kick_Off_Slot** — временной слот начала матча (Sat 15:00, Fri 20:00, Sat 12:30, Sun 16:30).
- **Season_Milestone** — визуальный маркер ключевого события сезона (открытие трансферного окна, дедлайн регистрации, финал кубка).

---

## Requirements

### Requirement 1: Структура сезона и даты

**User Story:** As a manager, I want the season to follow a realistic structure with defined blocks, so that the game feels authentic and I can plan ahead.

#### Acceptance Criteria

1. WHEN a new career is created, THE Calendar_Engine SHALL generate a full season calendar starting from July 15 of the current in-game year.
2. THE Calendar_Engine SHALL structure the season into 5 blocks: Pre-season (July 15 – August 10), First Half (August 10 – December 31), Winter Break (January 1–31), Second Half (February 1 – May 31), and Season Finish (June 1–14).
3. THE Calendar_Engine SHALL open the summer transfer window on July 1 and close it on August 31.
4. THE Calendar_Engine SHALL open the winter transfer window on January 1 and close it on January 31.
5. THE Calendar_Engine SHALL schedule pre-season training camp events during the 2–3 weeks before the first league matchday.
6. THE Calendar_Engine SHALL schedule player return-from-international-duty events at the start of pre-season.
7. THE Calendar_Engine SHALL schedule medical examination events during the first week of pre-season.
8. THE Calendar_Engine SHALL schedule pre-season friendly matches on free dates between July 20 and August 8.
9. WHILE the Winter Break block is active for leagues that observe a winter pause (Germany, Spain), THE Calendar_Engine SHALL schedule no league matches during January.
10. WHILE the Winter Break block is active for leagues that play through winter (England), THE Calendar_Engine SHALL schedule league matches including a mandatory Boxing Day (December 26) fixture.
11. THE Calendar_Engine SHALL schedule the Super Cup match (champion vs cup winner) during the last week of pre-season before the first league matchday.
12. THE Calendar_Engine SHALL end the season no later than June 14, with player holidays beginning June 1 for eliminated clubs.

---

### Requirement 2: Генерация календаря и приоритеты

**User Story:** As a manager, I want the calendar to be generated automatically with correct priorities, so that important fixtures are never overwritten by less important ones.

#### Acceptance Criteria

1. THE Calendar_Engine SHALL generate calendar events in the following priority order: FIFA international windows (priority 10) → European competition dates (priority 8) → Domestic league matches (priority 6) → Domestic cup matches (priority 4) → Friendly matches (priority 2).
2. THE Calendar_Engine SHALL schedule European competition matches on Tuesday, Wednesday, or Thursday only.
3. THE Calendar_Engine SHALL schedule domestic league matches on Saturday or Sunday by default, with Friday and Monday available for TV-selected fixtures.
4. THE Calendar_Engine SHALL schedule domestic cup matches on midweek dates (Tuesday, Wednesday, Thursday).
5. THE Calendar_Engine SHALL schedule friendly matches only on dates with no other events.
6. THE Calendar_Engine SHALL generate league matchdays every Saturday from August 10 to May 15, excluding dates blocked by international windows.
7. THE Calendar_Engine SHALL create cup round slots with placeholder opponents, filling actual opponents as teams progress through the competition.
8. THE Calendar_Engine SHALL schedule European group stage matches on fixed UEFA dates (Tuesday and Wednesday for Champions League, Thursday for Europa League).
9. THE Calendar_Engine SHALL schedule European knockout stage matches on Tuesday, Wednesday, or Thursday.
10. THE Calendar_Engine SHALL add international qualifier and tournament matches to the calendar for called-up players.

---

### Requirement 3: Конфликты и перенос матчей

**User Story:** As a manager, I want the system to handle scheduling conflicts automatically, so that my team never has two matches on the same day.

#### Acceptance Criteria

1. THE Calendar_Engine SHALL implement 3 date blocking types: international_break, european_match, and domestic_league.
2. WHEN a new event conflicts with an existing higher-priority event, THE Calendar_Engine SHALL reject the placement and suggest the nearest available free slot.
3. WHEN a European match is scheduled on Thursday, THE Reschedule_Engine SHALL move the club's next league match to Sunday or Monday.
4. WHEN a domestic cup match conflicts with a league match, THE Reschedule_Engine SHALL move the league match to the nearest available midweek date.
5. WHEN a club is eliminated from a cup competition, THE Calendar_Engine SHALL remove all future cup match slots for that club and mark those dates as available.
6. IF the Calendar_Engine detects 3 or more matches scheduled within a 7-day period for a single club, THEN THE Calendar_Engine SHALL flag an overload warning and suggest rescheduling the lowest-priority match.
7. THE Calendar_Engine SHALL log all rescheduling actions with the original date, new date, and reason for the move.
8. THE Calendar_Engine SHALL prevent scheduling any match within 48 hours of another match for the same club.
9. WHEN an international break is active, THE Calendar_Engine SHALL block all club match dates for the duration of the break.
10. IF a rescheduling attempt fails because no free slot exists within 7 days of the original date, THEN THE Calendar_Engine SHALL escalate the conflict to the player-manager with manual resolution options.

---

### Requirement 4: Время начала матчей и доход

**User Story:** As a manager, I want matches to have realistic kick-off times that affect revenue, so that TV slots feel meaningful.

#### Acceptance Criteria

1. THE Calendar_Engine SHALL assign a default kick-off time of Saturday 15:00 to all league matches.
2. THE Calendar_Engine SHALL assign TV slot kick-off times to selected matches: Friday 20:00, Saturday 12:30, and Sunday 16:30.
3. WHEN a match is assigned a TV slot kick-off time, THE Calendar_Engine SHALL apply a TV revenue bonus multiplier to the matchday income for that fixture.
4. THE Calendar_Engine SHALL assign a kick-off time of 21:00 (local time) to European competition matches.
5. THE Calendar_Engine SHALL assign a kick-off time of 20:00 to midweek domestic cup matches.
6. THE Calendar_Engine SHALL store the kick-off time as part of the Calendar_Event record.
7. WHEN the player-manager views a match event in the calendar, THE Calendar_UI SHALL display the kick-off time alongside the opponent and stadium information.

---

### Requirement 5: Погода и условия

**User Story:** As a manager, I want to see weather forecasts for match days, so that I can adjust my tactics based on conditions.

#### Acceptance Criteria

1. THE Weather_Generator SHALL generate weather conditions (rain, snow, clear, overcast, fog) for each match day based on the city's climate profile and the calendar month.
2. THE Weather_Generator SHALL generate a temperature value (in Celsius) appropriate for the city and month.
3. THE Weather_Generator SHALL generate a pitch condition value (dry, wet, muddy, frozen, artificial) based on weather and stadium type.
4. WHEN the player-manager clicks a match day in the Calendar_UI, THE Calendar_UI SHALL display the weather forecast including precipitation type, temperature, and pitch condition.
5. THE Weather_Generator SHALL make weather data available to the Game_Engine for tactical impact calculations during match simulation.
6. THE Weather_Generator SHALL generate snow conditions only for cities in cold climates during November–March.
7. THE Weather_Generator SHALL generate rain probability proportional to the city's historical rainfall for that month.

---

### Requirement 6: База данных календаря

**User Story:** As a developer, I want a well-structured database schema for calendar events, so that the system can efficiently query and update the schedule.

#### Acceptance Criteria

1. THE Calendar_Engine SHALL store events in a `calendar_events` table with columns: id, career_id, event_date, event_type, competition_id, home_club_id, away_club_id, is_locked, priority, kick_off_time, weather_data, description, created_at, updated_at.
2. THE Calendar_Engine SHALL support the following event_type values: match, training, meeting, deadline, international, medical, day_off, travel, milestone.
3. THE Calendar_Engine SHALL enforce that is_locked events (priority 9–10) cannot be rescheduled by the Reschedule_Engine.
4. THE Calendar_Engine SHALL store priority as an integer from 0 to 10, where 10 is the highest priority.
5. THE Calendar_Engine SHALL index the calendar_events table on (career_id, event_date) for efficient date-range queries.
6. THE Calendar_Engine SHALL index the calendar_events table on (career_id, event_type) for efficient type-filtered queries.
7. WHEN a calendar event is modified, THE Calendar_Engine SHALL update the updated_at timestamp.
8. THE Calendar_Engine SHALL support soft-deletion of events by setting a cancelled flag rather than removing records.

---

### Requirement 7: Интерфейс календаря — месячная сетка

**User Story:** As a manager, I want to see my schedule in a monthly grid view with color-coded events, so that I can quickly understand my upcoming commitments.

#### Acceptance Criteria

1. THE Calendar_UI SHALL display a monthly grid view showing all days of the selected month with event indicators.
2. THE Calendar_UI SHALL use the following color coding for event icons: Red for official matches, Blue for friendly matches, Green for training sessions, Grey for days off, Orange for transfer deadlines, Purple for medical events, and a country flag icon for international call-ups.
3. THE Calendar_UI SHALL allow the player-manager to navigate between months using previous/next controls.
4. THE Calendar_UI SHALL highlight the current in-game day with a distinct border or background color.
5. THE Calendar_UI SHALL display multiple event indicators on a single day when multiple events are scheduled.
6. THE Calendar_UI SHALL display Season_Milestone markers as visual dividers between season blocks (e.g., "Transfer window opens", "Registration deadline", "Last matchday", "Cup final").
7. THE Calendar_UI SHALL render the monthly grid responsively to fit mobile screen widths without horizontal scrolling.
8. THE Calendar_UI SHALL display the month name and year as a header above the grid.

---

### Requirement 8: Интерфейс календаря — детали дня

**User Story:** As a manager, I want to click on a day to see full details of all events, so that I can plan my decisions around the schedule.

#### Acceptance Criteria

1. WHEN the player-manager clicks a day in the monthly grid, THE Calendar_UI SHALL display a detail panel showing all events for that day.
2. WHEN a match event is displayed in the detail panel, THE Calendar_UI SHALL show the opponent name, kick-off time, stadium name, competition name, and weather forecast.
3. WHEN a training event is displayed in the detail panel, THE Calendar_UI SHALL show the training type, training load (light/normal/heavy), and participating squad.
4. WHEN a deadline event is displayed in the detail panel, THE Calendar_UI SHALL show the deadline description and a countdown timer.
5. WHEN an international call-up event is displayed, THE Calendar_UI SHALL show the player name, national team, and match details.
6. THE Calendar_UI SHALL provide navigation links from match events to the match preparation screen.
7. THE Calendar_UI SHALL provide navigation links from training events to the training configuration screen.
8. WHEN a medical event is displayed, THE Calendar_UI SHALL show the player name, examination type, and any results.

---

### Requirement 9: Фильтрация и выбор команды

**User Story:** As a manager, I want to filter calendar events and switch between team views, so that I can focus on what matters to me.

#### Acceptance Criteria

1. THE Calendar_UI SHALL provide a Filter_Panel with toggles to show or hide: matches, training sessions, international breaks, transfer windows, medical events, and days off.
2. THE Calendar_UI SHALL provide a team selector dropdown with options: First Team, Youth Team, and Loaned Players.
3. WHEN the player-manager selects "Youth Team" in the team selector, THE Calendar_UI SHALL display only events relevant to the youth squad.
4. WHEN the player-manager selects "Loaned Players" in the team selector, THE Calendar_UI SHALL display loan return dates and loaned player match schedules.
5. THE Calendar_UI SHALL persist the current filter and team selection state across navigation within the same session.
6. WHEN all event types are hidden via the Filter_Panel, THE Calendar_UI SHALL display a message indicating no events match the current filter.
7. THE Calendar_UI SHALL update the monthly grid immediately when a filter toggle is changed without requiring a page reload.

---

### Requirement 10: Персональная интеграция

**User Story:** As a manager, I want to see personal events like contract expiries and player birthdays in the calendar, so that I can manage relationships proactively.

#### Acceptance Criteria

1. THE Calendar_Engine SHALL add contract expiry date events to the calendar for all squad players whose contracts expire within the current season.
2. THE Calendar_Engine SHALL add player birthday events to the calendar for all first-team squad players.
3. THE Calendar_Engine SHALL add promise deadline events to the calendar when the player-manager makes a promise to a player (e.g., "promise playing time by December").
4. WHEN a contract expiry event is within 30 days, THE Calendar_UI SHALL highlight it with a warning indicator.
5. WHEN a promise deadline event is within 7 days, THE Reminder_System SHALL notify the player-manager.
6. THE Calendar_UI SHALL display personal events with a distinct icon style to differentiate them from club operational events.

---

### Requirement 11: Система напоминаний

**User Story:** As a manager, I want to receive timely reminders about upcoming events, so that I never miss important deadlines or preparation opportunities.

#### Acceptance Criteria

1. THE Reminder_System SHALL notify the player-manager 2 in-game days before each match with a suggestion to review tactics.
2. THE Reminder_System SHALL notify the player-manager 1 in-game week before a transfer window deadline.
3. THE Reminder_System SHALL notify the player-manager 1 in-game day before a competition draw event.
4. THE Reminder_System SHALL display reminders as in-game notifications accessible from the main navigation.
5. THE Reminder_System SHALL allow the player-manager to dismiss individual reminders.
6. THE Reminder_System SHALL not generate duplicate reminders for the same event.
7. WHEN the player-manager advances a week, THE Reminder_System SHALL check all events in the upcoming 7 days and generate applicable reminders.

---

### Requirement 12: Предматчевый день

**User Story:** As a manager, I want the day before a match to have a special schedule, so that match preparation feels realistic.

#### Acceptance Criteria

1. WHEN a match is scheduled for the next day, THE Calendar_Engine SHALL automatically generate a pre-match day schedule replacing normal training.
2. THE Calendar_Engine SHALL schedule a morning light warmup session on the pre-match day.
3. THE Calendar_Engine SHALL schedule an afternoon tactical theory session on the pre-match day.
4. WHERE the match is an away fixture, THE Calendar_Engine SHALL schedule an evening hotel check-in event on the pre-match day.
5. WHILE a pre-match day schedule is active, THE Calendar_Engine SHALL prevent normal training sessions from being assigned to first-team players.
6. THE Calendar_UI SHALL display pre-match day events with a distinct visual grouping to indicate they are part of match preparation.

---

### Requirement 13: Планирование поездок

**User Story:** As a manager, I want away match travel to be planned automatically, so that logistics are handled without manual effort.

#### Acceptance Criteria

1. WHEN an away match is scheduled, THE Travel_Planner SHALL automatically generate departure and return travel events.
2. THE Travel_Planner SHALL select transport mode (bus or plane) based on the distance between the home and away stadiums.
3. THE Travel_Planner SHALL schedule the departure event to arrive at the destination at least 3 hours before kick-off.
4. THE Travel_Planner SHALL schedule the return event for 2 hours after the match ends.
5. THE Calendar_UI SHALL display travel events with departure time, transport mode, and destination.
6. THE Travel_Planner SHALL allow the player-manager to manually override the departure time or transport mode.
7. WHEN the player-manager overrides a travel plan, THE Travel_Planner SHALL validate that the new departure time still allows arrival before kick-off.

---

### Requirement 14: Повторяющиеся события и шаблоны

**User Story:** As a manager, I want to set up weekly training templates, so that I do not have to schedule training manually every week.

#### Acceptance Criteria

1. THE Calendar_Engine SHALL support Recurring_Template definitions that map days of the week to event types (e.g., Monday = tactical theory, Tuesday = practice match, Wednesday = rest).
2. THE Calendar_Engine SHALL allow the player-manager to create, edit, and delete Recurring_Templates.
3. WHEN the player-manager applies a Recurring_Template to a month, THE Calendar_Engine SHALL generate individual Calendar_Events for each applicable day that does not already have a higher-priority event.
4. THE Calendar_Engine SHALL skip template application on days that have matches, international breaks, or other locked events.
5. THE Calendar_Engine SHALL allow the player-manager to override individual generated events without affecting the template.
6. THE Calendar_UI SHALL provide a template management screen showing the current weekly template with day-by-day assignments.
7. WHEN a new season begins, THE Calendar_Engine SHALL prompt the player-manager to confirm or modify the existing Recurring_Template.

---

### Requirement 15: Синхронизация международного календаря

**User Story:** As a manager, I want to see when my players are called up for international duty, so that I can plan around their absence.

#### Acceptance Criteria

1. THE Calendar_Engine SHALL display national team match dates for all squad players who receive international call-ups.
2. THE Calendar_Engine SHALL mark international duty days with the player's national team flag color in the Calendar_UI.
3. WHILE a player is on international duty, THE Calendar_Engine SHALL mark that player as unavailable for club selection.
4. THE Calendar_Engine SHALL schedule international windows in September, October, November, and March of each season.
5. WHEN a player returns from international duty, THE Calendar_Engine SHALL apply a 2-day recovery period before the player is available for club matches.
6. THE Calendar_UI SHALL display a list of called-up players and their national team fixtures when an international break is selected.
7. IF a player is injured during international duty, THEN THE Calendar_Engine SHALL update the player's injury status and notify the player-manager immediately.

---

### Requirement 16: Вехи сезона

**User Story:** As a manager, I want to see key season milestones clearly marked in the calendar, so that I can track the season's progression.

#### Acceptance Criteria

1. THE Calendar_Engine SHALL generate Season_Milestone events for: "Summer transfer window opens" (July 1), "Season start" (July 15), "Summer transfer window closes" (August 31), "Winter transfer window opens" (January 1), "Winter transfer window closes" (January 31), "Registration deadline" (per competition rules), "Last league matchday", "Cup final date", and "European final date".
2. THE Calendar_UI SHALL display Season_Milestone events as visual dividers with distinct styling (larger text, horizontal rule, or banner).
3. THE Calendar_UI SHALL display a countdown to the next upcoming milestone on the calendar header.
4. THE Calendar_Engine SHALL allow leagues to define custom milestones (e.g., "Boxing Day fixtures" for English leagues).
5. WHEN a Season_Milestone date is reached during week advancement, THE Calendar_Engine SHALL trigger a notification to the player-manager.

---

### Requirement 17: Автоматическое обновление календаря

**User Story:** As a manager, I want the calendar to update automatically when circumstances change, so that I always see an accurate schedule.

#### Acceptance Criteria

1. WHEN a club is eliminated from a cup competition, THE Calendar_Engine SHALL remove all future cup fixtures for that club and free the associated dates.
2. WHEN a club qualifies for a new competition round, THE Calendar_Engine SHALL add the new fixture dates to the calendar.
3. WHEN the Calendar_Engine detects a fixture overload (3 matches in 7 days), THE Calendar_Engine SHALL suggest rescheduling the lowest-priority match and present options to the player-manager.
4. WHEN a player receives a red card or accumulates yellow cards resulting in a suspension, THE Calendar_Engine SHALL mark the player as unavailable for the relevant future match dates.
5. THE Calendar_Engine SHALL recalculate the calendar after each week advancement to account for new information (draw results, eliminations, postponements).
6. WHEN a match is postponed due to weather or other factors, THE Calendar_Engine SHALL find the nearest available date and reschedule automatically.
7. THE Calendar_Engine SHALL notify the player-manager of all automatic calendar changes via the Reminder_System.

---

### Requirement 18: Праздники и особые дни по лигам

**User Story:** As a manager, I want league-specific holidays and special fixture days to be respected, so that the calendar matches real football traditions.

#### Acceptance Criteria

1. THE Calendar_Engine SHALL support league-specific holiday rules defined in a configuration per country.
2. WHERE the league is English, THE Calendar_Engine SHALL schedule a mandatory fixture on Boxing Day (December 26) and New Year's Day (January 1).
3. WHERE the league is German or Spanish, THE Calendar_Engine SHALL enforce a winter pause with no league matches during January.
4. THE Calendar_Engine SHALL schedule no matches on Christmas Day (December 25) for any league.
5. THE Calendar_Engine SHALL allow league configurations to define additional mandatory fixture dates or blackout dates.
6. WHEN a holiday fixture is scheduled, THE Calendar_Engine SHALL mark it as is_locked with priority 9 to prevent rescheduling.
