# Requirements Document

## Introduction

Telegram Football Manager (TFM)  это упрощённая 2D-версия Football Manager, работающая как Telegram Web App. Игрок берёт на себя роль менеджера футбольного клуба и ведёт карьеру: управляет составом из базы 2600 реальных игроков (файл `2600球员属性.csv`), выстраивает тактику, проводит трансферы, тренирует команду и наблюдает за матчами в реальном времени через 2D-анимацию на HTML5 Canvas. Бэкенд реализован на Python 3.11, фронтенд  на HTML5 Canvas + JavaScript. Монетизация: бесплатная основа с косметическим премиумом.

Документ охватывает MVP (пункты 1200) и расширенные возможности (пункты 201800).

---

## Glossary

- **TFM**  Telegram Football Manager, данная игра.
- **Game_Engine**  серверный Python-модуль, симулирующий матчи и игровую логику.
- **Match_Renderer**  клиентский JavaScript-модуль, отрисовывающий 2D-матч на HTML5 Canvas.
- **Player_DB**  база данных игроков, загружаемая из `2600球员属性.csv`.
- **Career_Manager**  модуль управления карьерой менеджера (один клуб).
- **Transfer_Engine**  модуль трансферного рынка.
- **Training_Module**  модуль тренировок и развития игроков.
- **Finance_Module**  модуль финансов клуба.
- **Scout_Module**  модуль скаутинга игроков.
- **Medical_Module**  модуль здоровья и травм игроков.
- **Tactic_Editor**  интерфейс настройки тактики и расстановки.
- **UI**  пользовательский интерфейс Telegram Web App.
- **AI_Manager**  искусственный интеллект, управляющий командами-соперниками.
- **CA**  Current Ability, текущий уровень способностей игрока (1200).
- **PA**  Potential Ability, потенциальный уровень способностей игрока (1200).
- **Telegram_Bot**  Telegram-бот, являющийся точкой входа в игру.
- **Save_System**  система сохранения и загрузки игры.
- **Premium_Store**  магазин косметических премиум-предметов.
- **Youth_Academy**  модуль молодёжной академии клуба.
- **Media_Module**  модуль взаимодействия со СМИ и пресс-конференций.
- **Competition_Engine**  модуль соревнований (лига, кубки, еврокубки).

---

## Requirements


### Requirement 1: Концепция и платформа

**User Story:** As a football fan, I want to manage a football club inside Telegram, so that I can enjoy a Football Manager experience without leaving the messenger.

#### Acceptance Criteria

1. THE TFM SHALL run as a Telegram Web App accessible via a Telegram_Bot command.
2. THE TFM SHALL support all devices (iOS, Android, desktop) that support Telegram Web App.
3. THE TFM SHALL load the initial game screen within 5 seconds on a 4G mobile connection.
4. WHEN a user opens the Telegram_Bot for the first time, THE TFM SHALL present a new-game setup screen.
5. THE TFM SHALL operate in single-club career mode where the player manages one club throughout the career.
6. THE Game_Engine SHALL be implemented in Python 3.11 and run on the server side.
7. THE Match_Renderer SHALL be implemented in HTML5 Canvas and JavaScript and run on the client side.
8. THE Player_DB SHALL be loaded from the file `2600球员属性.csv` containing 2600 players with attributes.
9. IF the Telegram Web App API is unavailable, THEN THE TFM SHALL display a descriptive error message and provide a retry option.
10. THE TFM SHALL support Russian and English languages at minimum.

---

### Requirement 2: 2D-графика и визуальный стиль

**User Story:** As a player, I want to watch matches in a clean 2D view, so that I can follow the action without needing a powerful device.

#### Acceptance Criteria

1. THE Match_Renderer SHALL display the football pitch as a 2D top-down view on HTML5 Canvas.
2. THE Match_Renderer SHALL represent players as coloured circles or simple sprites with shirt numbers.
3. THE Match_Renderer SHALL animate player movement, ball movement, and key events (shots, tackles, goals) at a minimum of 30 frames per second on mid-range mobile devices.
4. WHEN a goal is scored, THE Match_Renderer SHALL display a goal celebration animation lasting no more than 3 seconds.
5. THE Match_Renderer SHALL scale the pitch and player icons responsively to fit the device screen width without horizontal scrolling.
6. THE Match_Renderer SHALL use a colour scheme consistent with the simplified Football Manager 2026 visual style.
7. WHERE a user has enabled reduced-motion accessibility setting, THE Match_Renderer SHALL reduce or disable non-essential animations.
8. THE Match_Renderer SHALL display a real-time scoreboard, match clock, and current formation overlay during the match.
9. WHEN the match is paused, THE Match_Renderer SHALL freeze all animations and display a pause indicator.
10. THE Match_Renderer SHALL render weather effects (rain, snow, fog) as lightweight overlay effects on the canvas.

---

### Requirement 3: Движок матча

**User Story:** As a player, I want matches to feel realistic and varied, so that tactics and player quality genuinely affect outcomes.

#### Acceptance Criteria

1. THE Game_Engine SHALL simulate a full 90-minute match in under 2 seconds of server processing time.
2. THE Game_Engine SHALL use player CA, PA, and individual attributes from Player_DB to calculate match actions.
3. THE Game_Engine SHALL produce match events (passes, shots, tackles, fouls, cards, goals, substitutions) as a time-stamped event stream.
4. WHEN the Game_Engine produces an event stream, THE Match_Renderer SHALL replay it in real time at configurable speed (1, 2, 4, or instant).
5. THE Game_Engine SHALL factor in team tactics, formation, player positions, and player morale when calculating match outcomes.
6. THE Game_Engine SHALL simulate player fatigue: WHILE a player's stamina attribute is below 50% of maximum, THE Game_Engine SHALL reduce that player's effective CA by 10%.
7. IF a player receives a red card, THEN THE Game_Engine SHALL remove that player from the match and prevent substitution for that slot.
8. THE Game_Engine SHALL generate at least 5 distinct match commentary lines per match event type.
9. THE Game_Engine SHALL support extra time and penalty shootouts for knockout competitions.
10. WHEN a match simulation is complete, THE Game_Engine SHALL persist the full match result, statistics, and event log to the database.
11. THE Game_Engine SHALL calculate home advantage by applying a 5% boost to the home team's effective CA in all match calculations.
12. THE Game_Engine SHALL simulate set pieces (corners, free kicks, penalties) using dedicated set-piece logic that references player set-piece attributes.

---

### Requirement 4: Тактика и расстановка

**User Story:** As a manager, I want to set up tactics and formations, so that I can influence how my team plays.

#### Acceptance Criteria

1. THE Tactic_Editor SHALL support at least 15 standard formations (4-4-2, 4-3-3, 4-2-3-1, 3-5-2, 5-3-2, 4-5-1, 3-4-3, 4-1-4-1, 4-3-2-1, 5-4-1, 3-6-1, 4-4-1-1, 4-2-2-2, 3-4-1-2, 4-3-1-2).
2. THE Tactic_Editor SHALL allow the player to assign individual player roles (e.g., Sweeper Keeper, Ball-Playing Defender, Deep-Lying Playmaker, Advanced Forward) to each position.
3. THE Tactic_Editor SHALL allow configuration of team mentality (Defensive, Cautious, Balanced, Positive, Attacking, Very Attacking).
4. THE Tactic_Editor SHALL allow configuration of pressing intensity (Low, Medium, High, Gegenpressing).
5. THE Tactic_Editor SHALL allow configuration of defensive line height (Deep, Standard, High, Very High).
6. THE Tactic_Editor SHALL allow configuration of width (Narrow, Standard, Wide).
7. THE Tactic_Editor SHALL allow configuration of tempo (Slow, Standard, Fast).
8. WHEN the player saves a tactic, THE Tactic_Editor SHALL store up to 5 named tactic presets per user.
9. THE Game_Engine SHALL apply the active tactic preset when simulating a match.
10. THE Tactic_Editor SHALL display a visual pitch diagram showing player positions and movement arrows for the selected formation.
11. WHEN a player is dragged to a new position on the pitch diagram, THE Tactic_Editor SHALL update the formation and validate that the new position is compatible with the player's listed positions in Player_DB.
12. THE Tactic_Editor SHALL support in-match tactical adjustments that take effect at the next simulated minute.

---

### Requirement 5: Управление составом

**User Story:** As a manager, I want to manage my squad, so that I can pick the best team and keep players happy.

#### Acceptance Criteria

1. THE Career_Manager SHALL maintain a squad of between 18 and 40 players per club.
2. THE Career_Manager SHALL enforce a matchday squad limit of 18 players (11 starters + 7 substitutes).
3. THE Career_Manager SHALL track each player's contract expiry date, wage, and release clause.
4. WHEN a player's contract has fewer than 6 months remaining, THE Career_Manager SHALL notify the player-manager with an alert.
5. THE Career_Manager SHALL allow the player-manager to set each player's squad status (Key Player, First Team, Rotation, Backup, Not Needed).
6. THE Career_Manager SHALL calculate and display player morale based on squad status, playing time, recent results, and contract satisfaction.
7. WHILE a player's morale is below 40 out of 100, THE Career_Manager SHALL reduce that player's effective CA by 5% in match simulations.
8. THE Career_Manager SHALL allow the player-manager to interact with players via a simplified interaction menu (Praise, Criticise, Promise Playing Time, Discuss Contract).
9. IF a player's morale drops below 20 out of 100 for 3 consecutive in-game weeks, THEN THE Career_Manager SHALL trigger a transfer request from that player.
10. THE Career_Manager SHALL display each player's full attribute profile sourced from Player_DB, including CA, PA, position, age, nationality, and all 50+ individual attributes.
11. THE Career_Manager SHALL age players by 1 year on their in-game birthday and recalculate CA based on age, PA, training, and morale.
12. THE Career_Manager SHALL enforce a maximum of 3 non-EU players in the starting 11 for leagues with such restrictions (configurable per competition).

---

### Requirement 6: Трансферная система

**User Story:** As a manager, I want to buy and sell players, so that I can build the squad I need.

#### Acceptance Criteria

1. THE Transfer_Engine SHALL operate transfer windows twice per in-game season (summer: weeks 18, winter: weeks 2630).
2. THE Transfer_Engine SHALL allow the player-manager to make transfer bids for any player in Player_DB not currently in the player's club.
3. THE Transfer_Engine SHALL calculate AI acceptance probability based on the bid amount relative to the player's market value, the selling club's financial situation, and the player's contract length.
4. WHEN a transfer bid is accepted, THE Transfer_Engine SHALL deduct the transfer fee from the club's transfer budget and add the player to the squad.
5. THE Transfer_Engine SHALL support loan deals (season-long and emergency loans) in addition to permanent transfers.
6. THE Transfer_Engine SHALL allow the player-manager to list players for sale and set an asking price.
7. THE AI_Manager SHALL generate transfer bids for listed players based on player value and AI club needs.
8. THE Transfer_Engine SHALL enforce a maximum squad size of 40 players; IF a transfer would exceed this limit, THEN THE Transfer_Engine SHALL reject the transfer and display an error.
9. THE Transfer_Engine SHALL simulate free agent signings outside of transfer windows.
10. THE Transfer_Engine SHALL display a transfer history log showing all completed transfers for the current season.
11. WHEN a transfer window closes, THE Transfer_Engine SHALL prevent new permanent transfer bids until the next window opens.
12. THE Transfer_Engine SHALL calculate player wages as part of the transfer negotiation and display the impact on the club's wage budget.

---

### Requirement 7: Тренировки и развитие игроков

**User Story:** As a manager, I want to train my players, so that they improve over time.

#### Acceptance Criteria

1. THE Training_Module SHALL allow the player-manager to assign each player to one of at least 8 training focus areas (General, Fitness, Tactics, Attacking, Defending, Set Pieces, Individual Technical, Individual Mental).
2. THE Training_Module SHALL simulate weekly training sessions and update player attributes at the end of each in-game week.
3. WHEN a player under 24 years old is assigned to a training focus area for 4 consecutive in-game weeks, THE Training_Module SHALL increase the relevant attributes by 1 point (capped at PA).
4. WHEN a player over 30 years old is not assigned to a Fitness training focus, THE Training_Module SHALL decrease the player's stamina and pace attributes by 1 point per 8 in-game weeks.
5. THE Training_Module SHALL allow the player-manager to hire up to 5 specialist coaches, each providing a bonus to a specific training area.
6. THE Training_Module SHALL display a training schedule view showing all players and their assigned focus areas for the current week.
7. IF a player is injured, THEN THE Training_Module SHALL assign that player to rehabilitation training automatically and prevent assignment to other focus areas.
8. THE Training_Module SHALL track and display each player's attribute history over the career.
9. THE Training_Module SHALL simulate youth player development through the Youth_Academy with weekly attribute updates.
10. THE Training_Module SHALL allow the player-manager to set team-wide training intensity (Light, Normal, Heavy) which affects injury risk and attribute development rate.

---

### Requirement 8: Финансы клуба

**User Story:** As a manager, I want to manage club finances, so that I can make sustainable decisions.

#### Acceptance Criteria

1. THE Finance_Module SHALL maintain a club balance sheet with income (matchday revenue, TV rights, prize money, player sales, sponsorships) and expenditure (wages, transfer fees, infrastructure, staff salaries).
2. THE Finance_Module SHALL update the club balance at the end of each in-game week.
3. WHEN the club balance falls below zero, THE Finance_Module SHALL notify the player-manager and restrict transfer spending to zero until the balance is positive.
4. THE Finance_Module SHALL calculate matchday revenue based on stadium capacity, average attendance, and ticket price (configurable by the player-manager within board-set limits).
5. THE Finance_Module SHALL distribute prize money at the end of each competition based on final league position and cup progress.
6. THE Finance_Module SHALL display a financial summary screen showing current balance, weekly wage bill, transfer budget, and projected end-of-season balance.
7. THE Finance_Module SHALL allow the player-manager to request a transfer budget increase from the board, subject to board approval based on club financial health.
8. THE Finance_Module SHALL simulate sponsorship deals that renew annually with value based on club reputation and league position.
9. IF the club is in financial deficit for 3 consecutive in-game seasons, THEN THE Finance_Module SHALL trigger a board takeover event with consequences for the player-manager's job security.
10. THE Finance_Module SHALL track and display a 5-season financial history chart.

---

### Requirement 9: Инфраструктура клуба

**User Story:** As a manager, I want to develop club infrastructure, so that I can improve facilities and attract better players.

#### Acceptance Criteria

1. THE Career_Manager SHALL track club infrastructure across 5 categories: Stadium, Training Facilities, Youth Academy, Medical Centre, and Scouting Network.
2. Each infrastructure category SHALL have 5 upgrade levels (Basic, Standard, Good, Excellent, World Class).
3. THE Career_Manager SHALL allow the player-manager to request infrastructure upgrades from the board, subject to board approval and club financial health.
4. WHEN a Training Facilities upgrade is completed, THE Training_Module SHALL apply a bonus multiplier to all attribute development rates.
5. WHEN a Youth Academy upgrade is completed, THE Youth_Academy SHALL generate higher-quality youth prospects.
6. WHEN a Medical Centre upgrade is completed, THE Medical_Module SHALL reduce average player injury recovery time by 10% per upgrade level above Standard.
7. WHEN a Scouting Network upgrade is completed, THE Scout_Module SHALL reveal more accurate player attribute information during scouting.
8. WHEN a Stadium upgrade is completed, THE Finance_Module SHALL increase maximum matchday revenue capacity.
9. Infrastructure upgrades SHALL take between 4 and 26 in-game weeks to complete depending on upgrade level.
10. THE Career_Manager SHALL display a club overview screen showing current infrastructure levels and any upgrades in progress.

---

### Requirement 10: Персонал клуба

**User Story:** As a manager, I want to hire and manage staff, so that I can improve all areas of the club.

#### Acceptance Criteria

1. THE Career_Manager SHALL support the following staff roles: Assistant Manager, Goalkeeping Coach, Fitness Coach, Tactical Coach, Youth Coach, Chief Scout, Head of Medical Staff, and Data Analyst.
2. THE Career_Manager SHALL allow the player-manager to hire and fire staff within the constraints of the staff wage budget.
3. Each staff member SHALL have a set of relevant attributes (e.g., Coaching, Scouting, Medical, Tactical Knowledge) rated 120.
4. WHEN a Fitness Coach with a Coaching attribute above 15 is hired, THE Training_Module SHALL apply a 10% bonus to fitness training effectiveness.
5. WHEN a Chief Scout with a Scouting attribute above 15 is hired, THE Scout_Module SHALL reduce scouting report generation time by 20%.
6. THE Career_Manager SHALL display a staff management screen listing all current staff, their roles, attributes, and wages.
7. IF a staff member's contract expires and is not renewed, THEN THE Career_Manager SHALL remove that staff member from the club.
8. THE Career_Manager SHALL allow the player-manager to assign scouts to specific regions or competitions for targeted scouting.
9. THE Career_Manager SHALL simulate staff morale based on club success and working conditions.
10. THE Career_Manager SHALL allow the player-manager to negotiate staff contracts with duration (15 years) and wage.

---

### Requirement 11: Медицина и травмы

**User Story:** As a manager, I want to manage player injuries, so that I can plan my squad around fitness.

#### Acceptance Criteria

1. THE Medical_Module SHALL simulate player injuries during matches based on player attributes (bravery, stamina, strength), match intensity, and pitch conditions.
2. THE Medical_Module SHALL classify injuries into 3 severity levels: Minor (12 weeks), Moderate (38 weeks), and Severe (9+ weeks).
3. WHEN a player is injured during a match, THE Game_Engine SHALL remove that player from the match and THE Medical_Module SHALL set a recovery timeline.
4. THE Medical_Module SHALL display an injury list screen showing all injured players, injury type, and estimated return date.
5. WHILE a player is injured, THE Career_Manager SHALL prevent that player from being selected in the matchday squad.
6. THE Medical_Module SHALL simulate training ground injuries with a weekly probability based on training intensity and player age.
7. WHEN a player returns from injury, THE Medical_Module SHALL apply a 2-week match sharpness penalty reducing effective CA by 10%.
8. THE Medical_Module SHALL allow the player-manager to view each player's injury history.
9. IF a player suffers 3 or more injuries in a single in-game season, THEN THE Medical_Module SHALL flag that player as injury-prone and increase future injury probability by 15%.
10. THE Medical_Module SHALL simulate player fatigue accumulation across consecutive matches and reduce injury risk when the player-manager rotates the squad.

---

### Requirement 12: Скаутинг

**User Story:** As a manager, I want to scout players, so that I can find transfer targets and youth prospects.

#### Acceptance Criteria

1. THE Scout_Module SHALL allow the player-manager to send scouts to observe specific players or regions.
2. WHEN a scout is assigned to a player, THE Scout_Module SHALL generate a scouting report after 24 in-game weeks depending on scout quality and Scouting Network level.
3. THE Scout_Module SHALL reveal player attributes progressively: basic attributes (name, position, age, nationality, club) are visible immediately; detailed attributes are revealed after the scouting report is complete.
4. THE Scout_Module SHALL display a scouting shortlist of up to 50 players.
5. THE Scout_Module SHALL allow the player-manager to filter the shortlist by position, age, nationality, CA range, and PA range.
6. WHEN a scouting report is complete, THE Scout_Module SHALL notify the player-manager via an in-game notification.
7. THE Scout_Module SHALL simulate youth scouting to discover players aged 15–18 not yet in Player_DB, generating them procedurally with attributes based on region and academy quality.
8. THE Scout_Module SHALL allow the player-manager to add scouted players directly to the transfer shortlist.
9. IF a scout is not assigned to any task, THEN THE Scout_Module SHALL display a warning notification to the player-manager.
10. THE Scout_Module SHALL display a world map view showing active scouting assignments by region.

---

### Requirement 13: Медиа и пресс-конференции

**User Story:** As a manager, I want to interact with the media, so that I can manage my reputation and player morale.

#### Acceptance Criteria

1. THE Media_Module SHALL present pre-match and post-match press conference events with multiple-choice response options.
2. THE Media_Module SHALL present at least 3 response options per press conference question.
3. WHEN the player-manager selects a press conference response, THE Media_Module SHALL calculate the morale impact on relevant players and the reputation impact on the manager.
4. THE Media_Module SHALL simulate media pressure events (e.g., "Manager under pressure after 3 losses") that affect board confidence.
5. THE Media_Module SHALL display a media reputation score (1100) for the player-manager that changes based on results and press conference responses.
6. THE Media_Module SHALL generate player interview events where players make public statements that the player-manager must respond to.
7. WHEN the player-manager's media reputation falls below 30, THE Media_Module SHALL trigger increased board scrutiny events.
8. THE Media_Module SHALL display a news feed showing recent media events, results, and transfer news.
9. THE Media_Module SHALL localise press conference questions and responses in the user's selected language.
10. THE Media_Module SHALL simulate rival manager comments that the player-manager can respond to, affecting inter-club rivalry.

---

### Requirement 14: Соревнования и лиги

**User Story:** As a manager, I want to compete in leagues and cups, so that I have meaningful objectives each season.

#### Acceptance Criteria

1. THE Competition_Engine SHALL simulate at least one domestic league (20 clubs, 38 matchdays), one domestic cup (knockout), and one continental cup (group stage + knockout) per season.
2. THE Competition_Engine SHALL generate a full season fixture list at the start of each season.
3. THE Competition_Engine SHALL simulate all non-player-managed matches using the Game_Engine and AI_Manager.
4. THE Competition_Engine SHALL maintain a live league table updated after each matchday.
5. THE Competition_Engine SHALL enforce promotion and relegation between league tiers at the end of each season.
6. THE Competition_Engine SHALL award prize money and reputation points based on final competition standings.
7. WHEN the player-manager's club wins a competition, THE Competition_Engine SHALL trigger a trophy celebration event and update the club's trophy cabinet.
8. THE Competition_Engine SHALL simulate European qualification based on domestic league position.
9. THE Competition_Engine SHALL display a full fixture list with results, upcoming matches, and competition standings.
10. THE Competition_Engine SHALL support multi-season careers with increasing competition difficulty as the club's reputation grows.
11. THE Competition_Engine SHALL simulate cup draws using a randomised seeded draw system.
12. WHEN a match is scheduled, THE Competition_Engine SHALL check for player availability (injuries, suspensions) and notify the player-manager of any issues.

---

### Requirement 15: Карьера менеджера

**User Story:** As a player, I want my manager career to feel meaningful and progressive, so that I stay engaged over multiple seasons.

#### Acceptance Criteria

1. THE Career_Manager SHALL track manager attributes: Tactical Knowledge, Man Management, Motivating, Attacking, Defending, Technical, Mental, Youth Development, and Board Relations (each rated 120).
2. THE Career_Manager SHALL increase manager attributes based on in-game achievements (e.g., winning a league increases Tactical Knowledge by 1).
3. THE Career_Manager SHALL track manager reputation (1100) which affects the quality of clubs and players willing to work with the manager.
4. THE Career_Manager SHALL present board objectives at the start of each season (e.g., "Finish in top 6", "Reach cup semi-final").
5. WHEN the player-manager meets all board objectives, THE Career_Manager SHALL increase board confidence and unlock infrastructure upgrade options.
6. IF the player-manager fails board objectives for 2 consecutive seasons, THEN THE Career_Manager SHALL trigger a sacking event ending the career.
7. THE Career_Manager SHALL display a career statistics screen showing seasons managed, trophies won, win percentage, and total transfer spend.
8. THE Career_Manager SHALL support a Hall of Fame showing the player-manager's greatest achievements.
9. THE Career_Manager SHALL allow the player-manager to set personal objectives in addition to board objectives.
10. THE Career_Manager SHALL simulate manager fatigue: WHILE the player-manager has lost 5 or more consecutive matches, THE Career_Manager SHALL apply a morale penalty to all players.

---

### Requirement 16: UI/UX и навигация

**User Story:** As a player, I want a clean and intuitive interface, so that I can manage my club efficiently on a mobile screen.

#### Acceptance Criteria

1. THE UI SHALL provide a bottom navigation bar with 5 main sections: Home (Dashboard), Squad, Tactics, Transfers, and Match.
2. THE UI SHALL render all screens within the Telegram Web App viewport without requiring external browser navigation.
3. THE UI SHALL support both portrait and landscape orientations on mobile devices.
4. THE UI SHALL use touch-friendly controls with minimum tap target size of 4444 pixels.
5. THE UI SHALL display a persistent notification badge on navigation items when unread notifications are present.
6. THE UI SHALL provide a global search function to find players, staff, and competitions by name.
7. WHEN the user navigates back from a sub-screen, THE UI SHALL restore the previous screen's scroll position.
8. THE UI SHALL display loading indicators for all operations taking longer than 500 milliseconds.
9. THE UI SHALL support swipe gestures for navigating between related screens (e.g., swiping between player profiles).
10. THE UI SHALL provide a dark mode and light mode theme, defaulting to the user's Telegram theme setting.
11. THE UI SHALL display contextual help tooltips for all non-obvious UI elements.
12. THE UI SHALL be fully operable using only touch input with no requirement for keyboard input except for text search fields.

---

### Requirement 17: Настройки и конфигурация

**User Story:** As a player, I want to customise game settings, so that the game fits my preferences.

#### Acceptance Criteria

1. THE UI SHALL provide a Settings screen accessible from the main navigation.
2. THE UI SHALL allow the player to select the game language (Russian, English, and at least 3 additional languages).
3. THE UI SHALL allow the player to configure match simulation speed (1, 2, 4, Instant).
4. THE UI SHALL allow the player to enable or disable sound effects and background music independently.
5. THE UI SHALL allow the player to configure notification preferences (match reminders, transfer alerts, injury alerts, board messages).
6. THE UI SHALL allow the player to toggle between dark and light themes.
7. THE UI SHALL allow the player to reset all settings to defaults.
8. WHEN the player changes a setting, THE UI SHALL apply the change immediately without requiring a restart.
9. THE UI SHALL persist all settings to the server-side Save_System so they are restored on next session.
10. THE UI SHALL display the current app version and a link to the privacy policy.

---

### Requirement 18: Система сохранений

**User Story:** As a player, I want my progress to be saved automatically, so that I never lose my career data.

#### Acceptance Criteria

1. THE Save_System SHALL automatically save the game state after every significant action (match completion, transfer, tactic change, end of week).
2. THE Save_System SHALL store save data server-side linked to the user's Telegram user ID.
3. THE Save_System SHALL maintain at least 3 automatic save slots (current, previous, 2 weeks ago) to allow rollback.
4. WHEN the user opens the game after a session gap, THE Save_System SHALL restore the most recent save state within 3 seconds.
5. THE Save_System SHALL allow the player to manually create a named save at any time.
6. THE Save_System SHALL display a save history screen showing all available saves with timestamps.
7. IF a save operation fails due to a server error, THEN THE Save_System SHALL retry up to 3 times and notify the player if all retries fail.
8. THE Save_System SHALL compress save data to a maximum of 500 KB per save slot.
9. THE Save_System SHALL support export of save data as a JSON file for backup purposes.
10. THE Save_System SHALL prevent save data corruption by using atomic write operations with checksum validation.

---

### Requirement 19: Мультиплеер и социальные функции

**User Story:** As a player, I want to compare my progress with friends, so that I have a social competitive element.

#### Acceptance Criteria

1. THE TFM SHALL provide a global leaderboard showing top managers ranked by reputation score, trophies won, and win percentage.
2. THE TFM SHALL allow players to share match results and career milestones as Telegram messages.
3. THE TFM SHALL support a friends leaderboard showing rankings among the player's Telegram contacts who also play TFM.
4. THE TFM SHALL allow players to challenge friends to a simulated head-to-head match using their current squads.
5. WHEN a head-to-head challenge is accepted, THE Game_Engine SHALL simulate the match and notify both players of the result.
6. THE TFM SHALL display a weekly challenge event where all players compete under the same conditions (same club, same budget) for a limited time.
7. THE TFM SHALL allow players to view other players' club profiles (squad, trophies, formation) without modifying them.
8. THE TFM SHALL protect player save data so that social features cannot modify another player's career state.
9. THE TFM SHALL rate-limit head-to-head challenges to a maximum of 10 per day per user to prevent abuse.
10. THE TFM SHALL display a notification when a friend achieves a major milestone (e.g., wins a league title).

---

### Requirement 20: Доступность

**User Story:** As a player with accessibility needs, I want the game to be usable, so that I am not excluded from the experience.

#### Acceptance Criteria

1. THE UI SHALL provide a minimum text size of 14px for all body text and 12px for secondary labels.
2. THE UI SHALL maintain a minimum colour contrast ratio of 4.5:1 for all text against its background (WCAG AA).
3. THE UI SHALL provide text labels for all icon-only buttons.
4. WHERE a user has enabled the reduced-motion setting, THE Match_Renderer SHALL disable particle effects and transition animations.
5. THE UI SHALL support dynamic text size scaling based on the device's system font size setting.
6. THE UI SHALL provide an alternative text description for all non-decorative images and icons.
7. THE UI SHALL ensure all interactive elements are reachable and operable via keyboard navigation on desktop.
8. THE UI SHALL provide a high-contrast mode option in Settings.
9. THE UI SHALL not rely solely on colour to convey information (e.g., injury status uses both colour and icon).
10. THE UI SHALL display all monetary values and statistics in locale-appropriate formats based on the selected language.

---

### Requirement 21: Монетизация и премиум

**User Story:** As a player, I want the core game to be free, so that I can enjoy the full experience without paying.

#### Acceptance Criteria

1. THE TFM SHALL provide all core gameplay features (career mode, match simulation, transfers, tactics, training) for free without time gates or paywalls.
2. THE Premium_Store SHALL offer only cosmetic items: kit colours, stadium themes, match ball skins, manager avatar customisation, and UI themes.
3. THE Premium_Store SHALL accept payment via Telegram Stars (Telegram's in-app currency).
4. WHEN a premium cosmetic item is purchased, THE Premium_Store SHALL apply it immediately to the player's game without affecting gameplay balance.
5. THE Premium_Store SHALL display a clear label "Cosmetic Only  No Gameplay Advantage" on all premium items.
6. THE TFM SHALL not display advertisements that interrupt gameplay.
7. THE Premium_Store SHALL allow players to preview cosmetic items before purchase.
8. WHEN a purchase is completed, THE Premium_Store SHALL send a confirmation notification via Telegram.
9. THE Premium_Store SHALL maintain a purchase history accessible to the player.
10. THE TFM SHALL comply with Telegram's payment policies and applicable consumer protection laws regarding in-app purchases.

---

### Requirement 22: Технические требования и производительность

**User Story:** As a player, I want the game to run smoothly, so that I have a good experience on any device.

#### Acceptance Criteria

1. THE Game_Engine SHALL handle concurrent match simulations for up to 10,000 active users without exceeding 2 seconds per simulation.
2. THE TFM backend SHALL be deployed on a server capable of handling 50,000 daily active users.
3. THE TFM SHALL use WebSocket connections for real-time match event streaming between the Game_Engine and Match_Renderer.
4. THE Match_Renderer SHALL maintain 30 FPS on devices with at least 2 GB RAM and a mid-range mobile GPU.
5. THE TFM SHALL cache static assets (pitch graphics, player sprites, UI components) using browser caching with a minimum TTL of 24 hours.
6. THE TFM backend API SHALL respond to all non-simulation requests within 500 milliseconds under normal load.
7. THE TFM SHALL implement rate limiting: a maximum of 100 API requests per minute per user.
8. THE TFM SHALL use HTTPS for all client-server communication.
9. THE TFM SHALL validate all user inputs on the server side to prevent injection attacks.
10. THE TFM SHALL log all errors server-side with sufficient context for debugging, without logging personally identifiable information beyond Telegram user ID.
11. THE TFM SHALL implement database connection pooling to support concurrent user sessions efficiently.
12. THE TFM SHALL perform database backups every 24 hours with a retention period of 30 days.

---

### Requirement 23: База данных игроков (CSV)

**User Story:** As a player, I want to manage real-world players, so that the game feels authentic.

#### Acceptance Criteria

1. THE Player_DB SHALL load all player records from `2600球员属性.csv` at server startup and cache them in memory.
2. THE Player_DB SHALL parse the following attributes for each player: name, position, age, CA, PA, nationality, club, and all 50+ technical, mental, and physical attributes defined in the CSV schema.
3. THE Player_DB SHALL support querying players by position, age range, CA range, PA range, nationality, and club.
4. WHEN the CSV file is updated, THE Player_DB SHALL reload without requiring a full server restart.
5. THE Player_DB SHALL handle CSV parsing errors gracefully: IF a row contains invalid data, THEN THE Player_DB SHALL skip that row, log the error, and continue loading remaining rows.
6. THE Player_DB SHALL generate a unique internal player ID for each player based on the `uid` field in the CSV.
7. THE Player_DB SHALL support player attribute updates (from training and aging) stored separately from the base CSV data, preserving the original CSV values as a reference.
8. THE Player_DB SHALL provide a player search API endpoint that returns results within 200 milliseconds for queries against the full 2600-player dataset.
9. THE Player_DB SHALL display player names in their original script where supported by the device font, with a romanised fallback.
10. FOR ALL players loaded from CSV, THE Player_DB SHALL verify that CA is between 1 and 200 and PA is between CA and 200; IF validation fails, THEN THE Player_DB SHALL log a warning and clamp the value to the valid range.

---

### Requirement 24: Telegram-специфика и интеграция

**User Story:** As a Telegram user, I want the game to integrate naturally with Telegram, so that I don't need to leave the app.

#### Acceptance Criteria

1. THE Telegram_Bot SHALL respond to the `/start` command by opening the TFM Web App.
2. THE Telegram_Bot SHALL respond to the `/help` command with a list of available commands and a link to the game guide.
3. THE TFM SHALL use the Telegram Web App `MainButton` for primary actions (e.g., "Simulate Match", "Confirm Transfer").
4. THE TFM SHALL use the Telegram Web App `BackButton` for navigating back within the app.
5. THE TFM SHALL use the Telegram Web App `HapticFeedback` API to provide tactile feedback on goal events and match results.
6. THE TFM SHALL use the Telegram Web App `showAlert` and `showConfirm` APIs for critical confirmations (e.g., "Are you sure you want to sell this player?").
7. THE TFM SHALL use the Telegram Web App `CloudStorage` API to store lightweight user preferences (theme, language, notification settings).
8. THE TFM SHALL use the Telegram Web App `sendData` API to send match result summaries back to the Telegram chat.
9. THE Telegram_Bot SHALL send push notifications for scheduled match reminders 30 minutes before the simulated match time.
10. THE TFM SHALL handle Telegram Web App lifecycle events (expand, close, viewport change) gracefully without data loss.
11. THE TFM SHALL authenticate users exclusively via Telegram's `initData` mechanism and validate the hash server-side on every API request.
12. THE TFM SHALL comply with Telegram's Web App Content Security Policy requirements.

---

### Requirement 25: Локализация

**User Story:** As a non-English speaker, I want the game in my language, so that I can understand all features.

#### Acceptance Criteria

1. THE TFM SHALL support at least 6 languages: Russian, English, Spanish, Portuguese, French, and German.
2. THE TFM SHALL store all UI strings in language resource files (JSON format) separate from application code.
3. WHEN the player selects a language in Settings, THE UI SHALL apply the new language immediately without restarting the app.
4. THE TFM SHALL display player names in their original form from Player_DB regardless of the selected UI language.
5. THE TFM SHALL format dates, numbers, and currencies according to the locale conventions of the selected language.
6. THE TFM SHALL provide a fallback to English for any string not yet translated in the selected language.
7. THE TFM SHALL support right-to-left text layout for future Arabic language support without requiring code changes.
8. THE TFM SHALL allow community-contributed translations via a defined translation contribution process.
9. THE TFM SHALL display the language completion percentage for non-English languages in the Settings screen.
10. THE TFM SHALL not hard-code any user-visible strings in application code; all strings SHALL be referenced via localisation keys.

---

---

## Расширенные требования (201800)

### Requirement 26: Глубокая симуляция матча — физика мяча

**User Story:** As a player, I want ball physics to feel realistic, so that matches are visually convincing.

#### Acceptance Criteria

1. THE Match_Renderer SHALL simulate ball trajectory using a simplified 2D physics model including speed, direction, and deceleration.
2. THE Match_Renderer SHALL render ball spin effects (curve, dip) as visual trajectory arcs on the canvas.
3. THE Game_Engine SHALL calculate shot power and direction based on the shooting player's finishing, technique, and composure attributes.
4. THE Game_Engine SHALL simulate deflections: WHEN a shot hits a defender, THE Game_Engine SHALL recalculate ball direction using a randomised deflection angle.
5. THE Match_Renderer SHALL display a ball shadow on the pitch surface to indicate ball height during aerial balls.
6. THE Game_Engine SHALL simulate goalkeeper saves using a probability model based on the goalkeeper's reflexes, positioning, and the shot's power and placement.
7. THE Game_Engine SHALL simulate post and crossbar hits as distinct match events with appropriate visual feedback in Match_Renderer.
8. THE Match_Renderer SHALL animate the ball rolling to a stop after out-of-play events.
9. THE Game_Engine SHALL factor in wind direction (derived from weather conditions) when calculating long-pass and shot trajectories.
10. FOR ALL simulated shots, THE Game_Engine SHALL produce a shot placement value (on target, off target, blocked, saved, goal) that is consistent with the player's finishing attribute distribution.

---

### Requirement 27: ИИ игроков на поле

**User Story:** As a player, I want AI players to behave intelligently, so that matches feel dynamic.

#### Acceptance Criteria

1. THE Game_Engine SHALL simulate individual player decision-making using a weighted probability model based on player attributes (decisions, vision, anticipation, composure).
2. THE Game_Engine SHALL simulate off-the-ball movement: players without the ball SHALL move to tactically appropriate positions based on the active formation and team mentality.
3. THE Game_Engine SHALL simulate pressing behaviour: WHEN team pressing intensity is set to High or Gegenpressing, THE Game_Engine SHALL increase the probability of defensive players closing down the ball carrier within 5 simulated metres.
4. THE Game_Engine SHALL simulate player positioning errors: WHILE a player's concentration attribute is below 10, THE Game_Engine SHALL apply a 15% chance of positional error per defensive action.
5. THE Game_Engine SHALL simulate player communication: players with high teamwork attributes SHALL have a higher probability of making overlapping runs and combination plays.
6. THE Game_Engine SHALL simulate goalkeeper distribution: goalkeepers with high passing attributes SHALL prefer short distribution; goalkeepers with high kicking attributes SHALL prefer long distribution.
7. THE Game_Engine SHALL simulate player personality traits from Player_DB (e.g., "喜欢从双侧内切"  prefers cutting inside) as modifiers to decision probabilities.
8. THE Game_Engine SHALL simulate fatigue-driven decision degradation: WHILE a player's in-match stamina is below 30%, THE Game_Engine SHALL reduce that player's decisions attribute by 3 points for simulation purposes.
9. THE Game_Engine SHALL simulate player aggression: WHILE a player's aggression attribute is above 15, THE Game_Engine SHALL increase the probability of that player committing a foul by 10%.
10. THE Game_Engine SHALL ensure that AI player behaviour is deterministic given the same random seed, enabling match replay functionality.

---

### Requirement 28: События матча и комментарии

**User Story:** As a player, I want rich match events and commentary, so that matches feel alive.

#### Acceptance Criteria

1. THE Game_Engine SHALL generate the following event types: kick-off, pass, dribble, tackle, foul, free kick, corner, throw-in, shot, save, goal, offside, yellow card, red card, substitution, injury, penalty, extra time, full time.
2. THE Match_Renderer SHALL display a scrollable match event log panel alongside the pitch view.
3. THE Game_Engine SHALL generate contextual commentary text for each event type, referencing the player's name, the event description, and the match minute.
4. THE Game_Engine SHALL generate at least 10 distinct commentary variants per event type to avoid repetition.
5. THE Game_Engine SHALL generate special commentary for notable events: hat-tricks, own goals, last-minute winners, red cards, and penalty saves.
6. THE Match_Renderer SHALL highlight the relevant player(s) on the canvas when a key event occurs.
7. THE Game_Engine SHALL simulate crowd noise events (roar on goal, groan on missed chance) as audio cues in the Match_Renderer.
8. THE Game_Engine SHALL generate a match rating (110) for each player based on their actions during the match.
9. THE Game_Engine SHALL generate a Man of the Match award for the highest-rated player.
10. THE Game_Engine SHALL generate a post-match statistics screen showing possession, shots, shots on target, corners, fouls, cards, and pass accuracy for both teams.

---

### Requirement 29: Психология и мораль

**User Story:** As a manager, I want player psychology to matter, so that team management has real consequences.

#### Acceptance Criteria

1. THE Career_Manager SHALL track individual player morale (0100) and team morale (average of all squad players).
2. THE Game_Engine SHALL apply a team morale bonus: WHILE team morale is above 75, THE Game_Engine SHALL apply a 3% boost to all players' effective CA.
3. THE Game_Engine SHALL apply a team morale penalty: WHILE team morale is below 25, THE Game_Engine SHALL apply a 5% reduction to all players' effective CA.
4. THE Career_Manager SHALL update player morale after each match based on result (win +5, draw +1, loss -5), playing time, and individual performance rating.
5. THE Career_Manager SHALL simulate dressing room dynamics: WHEN a high-CA player (CA > 170) has morale below 40, THE Career_Manager SHALL apply a -3 morale penalty to all players with lower CA in the same squad.
6. THE Career_Manager SHALL simulate player confidence: WHEN a player scores in 3 consecutive matches, THE Career_Manager SHALL apply a +10 confidence bonus increasing that player's finishing attribute by 1 for the next 4 matches.
7. THE Career_Manager SHALL simulate pre-match team talks with 3 response options (Motivate, Calm, Demand) each affecting team morale differently based on the match context.
8. THE Career_Manager SHALL simulate half-time team talks with options based on the current match score.
9. THE Career_Manager SHALL simulate player unhappiness events triggered by lack of playing time, failed transfer requests, or wage disputes.
10. THE Career_Manager SHALL display a team morale indicator on the squad management screen using a colour-coded bar (red < 40, amber 4070, green > 70).

---

### Requirement 30: Сет-пьесы

**User Story:** As a manager, I want to set up set pieces, so that I can exploit dead-ball situations.

#### Acceptance Criteria

1. THE Tactic_Editor SHALL allow the player-manager to configure corner kick routines (near post, far post, short corner, penalty area flood).
2. THE Tactic_Editor SHALL allow the player-manager to assign corner kick takers and free kick takers from the squad.
3. THE Tactic_Editor SHALL allow the player-manager to configure free kick routines (direct shot, cross, short pass, dummy run).
4. THE Tactic_Editor SHALL allow the player-manager to configure penalty takers in priority order (1st, 2nd, 3rd choice).
5. THE Game_Engine SHALL simulate set pieces using the configured routines and the relevant player attributes (corners, free_kicks, heading, jumping, finishing).
6. THE Game_Engine SHALL calculate corner kick goal probability based on the corner taker's corners attribute and the target player's heading and jumping attributes.
7. THE Game_Engine SHALL simulate defensive set-piece organisation: WHEN the defending team has a high defensive line, THE Game_Engine SHALL increase the probability of a successful offside trap on set pieces.
8. THE Game_Engine SHALL simulate penalty shootouts by calculating each penalty's outcome using the taker's penalty attribute and the goalkeeper's reflexes and penalty-stopping attributes.
9. THE Match_Renderer SHALL display set-piece routines as animated arrow overlays on the pitch canvas.
10. THE Game_Engine SHALL track set-piece statistics (goals from corners, free kick goals, penalty conversion rate) in the season statistics.

---

### Requirement 31: Погода и условия матча

**User Story:** As a manager, I want weather to affect matches, so that conditions add strategic depth.

#### Acceptance Criteria

1. THE Competition_Engine SHALL assign weather conditions to each match based on the season month and stadium location (Rain, Snow, Fog, Clear, Windy, Hot).
2. THE Game_Engine SHALL apply weather modifiers to match simulation: Rain reduces passing accuracy by 5%; Snow reduces pace and stamina by 10%; Fog reduces long-pass accuracy by 15%; Hot conditions increase fatigue rate by 10%.
3. THE Match_Renderer SHALL display weather effects as visual overlays on the canvas (rain drops, snow particles, fog filter, heat shimmer).
4. THE Game_Engine SHALL factor in pitch condition (Good, Soft, Heavy, Waterlogged) derived from weather history when calculating match events.
5. WHEN pitch condition is Waterlogged, THE Competition_Engine SHALL postpone the match and reschedule it within 2 in-game weeks.
6. THE Game_Engine SHALL simulate player-specific weather adaptation: WHILE a player's nationality region matches the weather type (e.g., Nordic player in snow), THE Game_Engine SHALL reduce the weather penalty for that player by 50%.
7. THE Match_Renderer SHALL display the current weather condition and pitch condition in the match HUD.
8. THE Game_Engine SHALL simulate wind direction affecting long shots and crosses: WHILE wind speed is above 30 km/h, THE Game_Engine SHALL apply a directional modifier to all aerial balls.
9. THE Competition_Engine SHALL generate a weather forecast for the next 3 matchdays visible to the player-manager.
10. THE Game_Engine SHALL track weather-related statistics (goals scored in rain, clean sheets in snow) in the season statistics.

---

### Requirement 32: Молодёжная академия

**User Story:** As a manager, I want to develop youth players, so that I can build a sustainable club.

#### Acceptance Criteria

1. THE Youth_Academy SHALL generate 5 new youth prospects per in-game season with ages between 15 and 18.
2. THE Youth_Academy SHALL assign each youth prospect a PA between 100 and 180 based on the Youth Academy infrastructure level.
3. THE Youth_Academy SHALL assign each youth prospect a nationality based on the club's country and scouting network regions.
4. THE Youth_Academy SHALL allow the player-manager to promote youth prospects to the first-team squad.
5. THE Youth_Academy SHALL simulate youth player development weekly, increasing CA by 13 points per month for players under 20 with PA above current CA.
6. THE Youth_Academy SHALL display a youth squad screen showing all prospects with their current CA, PA, position, and age.
7. WHEN a youth player reaches age 18 without being promoted, THE Youth_Academy SHALL offer the player-manager the option to promote, loan out, or release the player.
8. THE Youth_Academy SHALL simulate youth cup competitions where the youth squad competes against AI youth teams.
9. THE Youth_Academy SHALL track youth graduates who reach the first team and display them in a "Club Legends" section.
10. THE Youth_Academy SHALL allow the player-manager to assign a dedicated youth coach whose attributes affect development rates.

---

### Requirement 33: Сборные

**User Story:** As a player, I want my players to be called up to national teams, so that the game world feels complete.

#### Acceptance Criteria

1. THE Competition_Engine SHALL simulate international breaks 4 times per in-game season where eligible players are called up to national teams.
2. THE Competition_Engine SHALL select national team squads based on player CA, nationality, and current form.
3. WHEN a player is called up to a national team, THE Career_Manager SHALL make that player unavailable for club matches during the international break.
4. THE Competition_Engine SHALL simulate international matches and update player morale based on national team results.
5. WHEN a player is injured during an international break, THE Medical_Module SHALL apply the injury to the player's club career.
6. THE Competition_Engine SHALL simulate major international tournaments (World Cup, continental championships) every 4 and 2 in-game years respectively.
7. THE Career_Manager SHALL display each player's international caps and goals in their player profile.
8. THE Competition_Engine SHALL allow the player-manager to view national team fixtures and results.
9. THE Competition_Engine SHALL simulate national team manager AI that selects players based on form and fitness.
10. WHEN a player wins a major international tournament, THE Career_Manager SHALL apply a +10 morale bonus and a +2 reputation boost to that player.

---

### Requirement 34: ИИ соперников

**User Story:** As a player, I want AI managers to behave intelligently, so that the competition feels challenging.

#### Acceptance Criteria

1. THE AI_Manager SHALL manage all non-player clubs in the competition, making transfer decisions, tactical selections, and squad management decisions.
2. THE AI_Manager SHALL select match tactics based on the opponent's strengths and weaknesses, using a simplified tactical analysis model.
3. THE AI_Manager SHALL make transfer bids for players based on club needs, budget, and player CA.
4. THE AI_Manager SHALL simulate press conference responses that affect media narratives.
5. THE AI_Manager SHALL adapt difficulty based on the player-manager's career progression: WHEN the player-manager's club reputation exceeds 70, THE AI_Manager SHALL increase tactical sophistication.
6. THE AI_Manager SHALL simulate realistic transfer market behaviour: AI clubs SHALL not spend more than 150% of their transfer budget in a single window.
7. THE AI_Manager SHALL simulate squad rotation: AI clubs SHALL rest key players before important matches.
8. THE AI_Manager SHALL simulate youth development: AI clubs SHALL promote youth players to their first team when CA exceeds 130.
9. THE AI_Manager SHALL simulate managerial changes: IF an AI club finishes in the bottom 3 of the league for 2 consecutive seasons, THEN THE AI_Manager SHALL replace the club's manager.
10. THE AI_Manager SHALL maintain consistent club identity (playing style, transfer philosophy) across seasons.

---

### Requirement 35: Звук и атмосфера

**User Story:** As a player, I want sound effects and crowd atmosphere, so that matches feel immersive.

#### Acceptance Criteria

1. THE Match_Renderer SHALL play crowd ambient sound during match simulation.
2. THE Match_Renderer SHALL play distinct sound effects for: goal scored, shot saved, foul committed, yellow card, red card, and full-time whistle.
3. THE Match_Renderer SHALL modulate crowd noise volume based on match events (louder on near-miss, loudest on goal).
4. THE UI SHALL play subtle UI interaction sounds for button taps and navigation transitions.
5. WHEN the player-manager enables background music in Settings, THE UI SHALL play a looping background music track during menu navigation.
6. THE Match_Renderer SHALL support muting all sounds independently of the device volume setting.
7. THE Match_Renderer SHALL use Web Audio API for sound playback to ensure compatibility with Telegram Web App.
8. THE Match_Renderer SHALL preload all match sound assets before the match begins to prevent audio lag.
9. THE Match_Renderer SHALL simulate stadium-specific crowd chants based on the home club's identity.
10. THE Match_Renderer SHALL fade out crowd noise gradually when the match ends.

---

### Requirement 36: Обучение и онбординг

**User Story:** As a new player, I want a tutorial, so that I can learn the game quickly.

#### Acceptance Criteria

1. THE TFM SHALL present an interactive tutorial to all new users on first launch, covering: squad selection, tactic setup, match simulation, and transfer basics.
2. THE tutorial SHALL be completable in under 10 minutes.
3. THE tutorial SHALL be skippable at any point with a single tap.
4. THE tutorial SHALL use contextual tooltips overlaid on the actual game UI rather than separate tutorial screens.
5. WHEN the player-manager completes the tutorial, THE Career_Manager SHALL award a starter bonus of in-game currency or a free transfer budget boost.
6. THE TFM SHALL provide a Help Centre accessible from Settings with searchable articles covering all game features.
7. THE TFM SHALL display contextual hints during the first 5 in-game weeks for features the player-manager has not yet used.
8. THE TFM SHALL provide a "Quick Start" mode that pre-configures a recommended tactic and squad for the player-manager's chosen club.
9. THE tutorial SHALL support all languages available in the game.
10. THE TFM SHALL track tutorial completion status and not repeat completed tutorial steps.

---

### Requirement 37: Статистика и аналитика

**User Story:** As a manager, I want detailed statistics, so that I can make data-driven decisions.

#### Acceptance Criteria

1. THE Career_Manager SHALL track and display season statistics for each player: appearances, goals, assists, average match rating, yellow cards, red cards, and minutes played.
2. THE Career_Manager SHALL track and display team statistics per season: wins, draws, losses, goals scored, goals conceded, clean sheets, and points.
3. THE Career_Manager SHALL display a player performance chart showing attribute changes over the career.
4. THE Career_Manager SHALL display a team performance chart showing league position over multiple seasons.
5. THE Career_Manager SHALL display a transfer statistics summary: total spent, total received, net spend per season.
6. THE Game_Engine SHALL generate xG (expected goals) values for each shot and display them in the post-match statistics.
7. THE Career_Manager SHALL display a heat map for each player showing their average positions during matches.
8. THE Career_Manager SHALL display a pass network diagram for the team showing the most frequent passing combinations.
9. THE Career_Manager SHALL allow the player-manager to export season statistics as a CSV file.
10. THE Career_Manager SHALL display a comparison view allowing the player-manager to compare two players' attributes and statistics side by side.

---

### Requirement 38: Архитектура и технические детали

**User Story:** As a developer, I want a clean architecture, so that the system is maintainable and scalable.

#### Acceptance Criteria

1. THE TFM backend SHALL be structured as a RESTful API with WebSocket support, implemented in Python 3.11 using FastAPI or equivalent framework.
2. THE TFM backend SHALL use a relational database (PostgreSQL) for persistent game state storage.
3. THE TFM backend SHALL use Redis for session caching and real-time match event queuing.
4. THE TFM frontend SHALL be a single-page application (SPA) communicating with the backend via REST API and WebSocket.
5. THE TFM SHALL implement a modular architecture where Game_Engine, Career_Manager, Transfer_Engine, Training_Module, Finance_Module, Scout_Module, Medical_Module, and Competition_Engine are independent Python modules with defined interfaces.
6. THE TFM SHALL use environment variables for all configuration (database URLs, API keys, Telegram bot token) with no hard-coded secrets.
7. THE TFM SHALL implement structured logging (JSON format) for all server-side operations.
8. THE TFM SHALL include a health check endpoint (`/health`) returning server status and database connectivity.
9. THE TFM SHALL be deployable via Docker containers with a provided `docker-compose.yml` for local development.
10. THE TFM SHALL include automated tests covering at least 80% of Game_Engine logic, with tests runnable via a single command.
11. THE TFM SHALL implement database migrations using Alembic or equivalent tool.
12. THE TFM SHALL document all public API endpoints using OpenAPI (Swagger) specification.

---

### Requirement 39: Отладка и инструменты разработчика

**User Story:** As a developer, I want debugging tools, so that I can diagnose issues quickly.

#### Acceptance Criteria

1. THE TFM SHALL provide a developer mode (enabled via environment variable) that exposes additional debug endpoints.
2. WHEN developer mode is enabled, THE Game_Engine SHALL accept a fixed random seed parameter to produce deterministic match simulations.
3. WHEN developer mode is enabled, THE TFM SHALL expose a match replay endpoint that re-runs a stored match event log.
4. THE TFM SHALL log all match simulation inputs and outputs at DEBUG level when developer mode is enabled.
5. THE TFM SHALL provide a simulation benchmark endpoint that runs 1000 match simulations and reports average execution time.
6. THE TFM SHALL include a data validation script that checks all records in Player_DB for attribute range compliance.
7. THE TFM SHALL provide a fixture generation test that verifies a full season fixture list has no scheduling conflicts.
8. THE TFM SHALL include integration tests for all Telegram Web App API interactions using mock Telegram data.
9. THE TFM SHALL provide a load testing script simulating 1000 concurrent users running match simulations.
10. THE TFM SHALL include a CSV import validation tool that reports all data quality issues in `2600球员属性.csv` before server startup.

---

### Requirement 40: Пост-релиз и сообщество

**User Story:** As a player, I want the game to evolve, so that there is always new content to enjoy.

#### Acceptance Criteria

1. THE TFM SHALL support hot-patching of Player_DB by replacing the CSV file without server restart.
2. THE TFM SHALL provide a seasonal content update mechanism delivering new competitions, events, and cosmetic items.
3. THE TFM SHALL include a community feedback system allowing players to report bugs and suggest features from within the game.
4. THE TFM SHALL display a changelog screen showing recent updates and new features.
5. THE TFM SHALL support A/B testing of new features by routing a configurable percentage of users to experimental versions.
6. THE TFM SHALL provide a public API for community developers to build companion apps (read-only access to leaderboards and statistics).
7. THE TFM SHALL implement a referral system where players earn cosmetic rewards for inviting friends via Telegram.
8. THE TFM SHALL support seasonal events (e.g., World Cup mode, Christmas cup) with time-limited gameplay variations.
9. THE TFM SHALL provide a moderation system allowing administrators to ban abusive users from social features.
10. THE TFM SHALL publish a public roadmap showing planned features for the next 3 months.

---

---

## Приоритеты реализации

### MVP (Пункты 1200  обязательные для первого релиза)

| # | Требование | Приоритет |
|---|-----------|-----------|
| 1 | Концепция и платформа (Telegram Web App, Python 3.11) | P0 |
| 2 | 2D-графика и визуальный стиль (HTML5 Canvas) | P0 |
| 3 | Движок матча (симуляция, события, статистика) | P0 |
| 4 | Тактика и расстановка (15 формаций, роли, менталитет) | P0 |
| 5 | Управление составом (состав, мораль, контракты) | P0 |
| 6 | Трансферная система (окна, торги, свободные агенты) | P0 |
| 7 | Тренировки и развитие игроков | P0 |
| 8 | Финансы клуба | P0 |
| 9 | Инфраструктура клуба | P1 |
| 10 | Персонал клуба | P1 |
| 11 | Медицина и травмы | P0 |
| 12 | Скаутинг | P1 |
| 13 | Медиа и пресс-конференции | P1 |
| 14 | Соревнования и лиги | P0 |
| 15 | Карьера менеджера | P0 |
| 16 | UI/UX и навигация | P0 |
| 17 | Настройки и конфигурация | P1 |
| 18 | Система сохранений | P0 |
| 19 | Мультиплеер и социальные функции | P2 |
| 20 | Доступность | P1 |
| 21 | Монетизация и премиум | P1 |
| 22 | Технические требования и производительность | P0 |
| 23 | База данных игроков (CSV) | P0 |
| 24 | Telegram-специфика и интеграция | P0 |
| 25 | Локализация | P1 |

### Расширенные возможности (Пункты 201800  для последующих версий)

| # | Требование | Приоритет |
|---|-----------|-----------|
| 26 | Физика мяча | P1 |
| 27 | ИИ игроков на поле | P1 |
| 28 | События матча и комментарии | P1 |
| 29 | Психология и мораль (расширенная) | P1 |
| 30 | Сет-пьесы | P2 |
| 31 | Погода и условия матча | P2 |
| 32 | Молодёжная академия | P2 |
| 33 | Сборные | P2 |
| 34 | ИИ соперников | P1 |
| 35 | Звук и атмосфера | P2 |
| 36 | Обучение и онбординг | P1 |
| 37 | Статистика и аналитика | P1 |
| 38 | Архитектура и технические детали | P0 |
| 39 | Отладка и инструменты разработчика | P1 |
| 40 | Пост-релиз и сообщество | P3 |

**Легенда приоритетов:**
- **P0**  Критично для MVP, без этого игра не работает
- **P1**  Важно для качественного MVP, реализуется в первом релизе
- **P2**  Желательно, реализуется в версии 1.11.2
- **P3**  Долгосрочная дорожная карта

