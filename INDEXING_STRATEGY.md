# Database Indexing Strategy

## Overview
This document outlines the comprehensive indexing strategy implemented across all database models in the Telegram Football Manager application. The strategy follows PostgreSQL best practices and optimizes for common query patterns.

## Indexing Principles

### 1. Foreign Key Indexes
**All foreign key columns are indexed** to optimize JOIN operations and maintain referential integrity performance.

### 2. Status and Enum Field Indexes
**All status and enum fields are indexed** to support filtering queries (WHERE clauses).

### 3. Date/Timestamp Indexes
**Date and timestamp fields used in queries are indexed** to support:
- Range queries (BETWEEN, >, <)
- Sorting operations (ORDER BY)
- Time-based filtering

### 4. Composite Indexes
**Composite indexes are created for common query patterns** that filter on multiple columns together.

### 5. Unique Constraints
**Unique indexes enforce data integrity** while also providing query optimization.

## Model-by-Model Index Coverage

### 1. User Model (`users`)
**Single Column Indexes:**
- `telegram_user_id` (unique) - Primary lookup field
- `username` - User search
- `last_login_at` - Activity tracking

**Purpose:** Fast user lookup by Telegram ID, username search, and activity queries.

---

### 2. Player Model (`players`)
**Single Column Indexes:**
- `uid` (unique) - CSV identifier lookup
- `name` - Player name search
- `position` - Position filtering
- `club` - Club filtering
- `ca` (Current Ability) - Ability-based queries
- `pa` (Potential Ability) - Potential-based queries
- `nationality` - Nationality filtering
- `age` - Age-based queries

**Composite Indexes:**
- `(position, ca)` - Position + ability queries (e.g., "Find ST with CA > 150")
- `(club, position)` - Club squad queries by position

**Purpose:** Optimizes player search, filtering, and scouting queries across 50+ attributes.

---

### 3. Club Model (`clubs`)
**Single Column Indexes:**
- `name` - Club name lookup
- `league` - League filtering
- `reputation` - Reputation-based queries
- `country` - Country filtering

**Composite Indexes:**
- `(league, reputation)` - League standings and reputation queries

**Purpose:** Fast club lookup, league queries, and reputation-based filtering.

---

### 4. Career Model (`careers`)
**Single Column Indexes:**
- `user_id` (FK) - User's careers lookup
- `club_id` (FK) - Club's active careers
- `save_timestamp` - Save system queries

**Composite Indexes:**
- `(user_id, current_season)` - User's career progression queries

**Purpose:** Optimizes career lookup, save system, and progression tracking.

---

### 5. SquadPlayer Model (`squad_players`)
**Single Column Indexes:**
- `career_id` (FK) - Career's squad lookup
- `player_id` (FK) - Player's squad history
- `squad_status` - Status filtering (KEY_PLAYER, FIRST_TEAM, etc.)
- `morale` - Morale-based queries
- `contract_end_date` - Contract expiry queries

**Composite Indexes:**
- `(career_id, squad_status)` - Squad management queries
- `(career_id, player_id)` (unique) - Prevents duplicate squad entries
- `(career_id, squad_number)` (unique) - Enforces unique squad numbers

**Purpose:** Optimizes squad management, contract tracking, and morale queries.

---

### 6. Match Model (`matches`)
**Single Column Indexes:**
- `career_id` (FK) - Career's match history
- `home_club_id` (FK) - Home club matches
- `away_club_id` (FK) - Away club matches
- `match_date` - Date-based queries
- `competition` - Competition filtering
- `status` - Status filtering (scheduled, in_progress, completed)

**Composite Indexes:**
- `(career_id, match_date)` - Career match history by date
- `(competition, match_date)` - Competition fixtures by date
- `(home_club_id, away_club_id, match_date)` - Head-to-head queries

**Purpose:** Optimizes match history, fixture lists, and competition queries.

---

### 7. MatchEvent Model (`match_events`)
**Single Column Indexes:**
- `match_id` (FK) - Match's event stream
- `player_id` (FK) - Player's event history
- `target_player_id` (FK) - Secondary player involvement
- `event_type` - Event type filtering
- `team` - Team filtering (home/away)
- `minute` - Time-based queries

**Composite Indexes:**
- `(match_id, minute, second)` - Chronological event stream
- `(match_id, event_type)` - Match events by type (e.g., all goals)
- `(player_id, event_type)` - Player statistics by event type
- `(match_id, team)` - Team-specific event queries

**Purpose:** Optimizes match simulation, event stream queries, and player statistics.

---

### 8. Transfer Model (`transfers`)
**Single Column Indexes:**
- `career_id` (FK) - Career's transfer history
- `player_id` (FK) - Player's transfer history
- `from_club_id` (FK) - Selling club transfers
- `to_club_id` (FK) - Buying club transfers
- `transfer_type` - Type filtering (permanent, loan, free_agent)
- `transfer_status` - Status filtering (pending, accepted, completed)
- `season` - Season-based queries

**Composite Indexes:**
- `(career_id, season)` - Career's seasonal transfers
- `(player_id, season)` - Player's transfer history by season
- `(transfer_status, career_id)` - Pending transfers for career

**Purpose:** Optimizes transfer market, history tracking, and pending transfer queries.

---

### 9. Injury Model (`injuries`)
**Single Column Indexes:**
- `career_id` (FK) - Career's injury history
- `player_id` (FK) - Player's injury history
- `squad_player_id` (FK) - Squad player's injuries
- `injury_type` - Injury type filtering
- `severity` - Severity filtering (minor, moderate, severe)
- `status` - Status filtering (active, recovering, recovered)
- `injury_date` - Date-based queries
- `season` - Season-based queries
- `occurred_in_match_id` (FK) - Match injury tracking

**Composite Indexes:**
- `(career_id, season)` - Career's seasonal injuries
- `(player_id, season)` - Player's injury history by season
- `(status, career_id)` - Active injuries for career
- `(squad_player_id, status)` - Squad player availability

**Purpose:** Optimizes injury tracking, player availability, and injury-prone detection.

---

### 10. Staff Model (`staff`)
**Single Column Indexes:**
- `career_id` (FK) - Career's staff
- `club_id` (FK) - Club's staff
- `name` - Staff name search
- `role` - Role filtering (8 staff roles)
- `contract_expiry_date` - Contract expiry queries

**Composite Indexes:**
- `(career_id, role)` - Career's staff by role
- `(club_id, role)` - Club's staff by role
- `(career_id, contract_expiry_date)` - Contract renewal tracking

**Purpose:** Optimizes staff management, role-based queries, and contract tracking.

---

### 11. TrainingSchedule Model (`training_schedules`)
**Single Column Indexes:**
- `career_id` (FK) - Career's training schedules
- `player_id` (FK) - Player's training history
- `squad_player_id` (FK) - Squad player's training
- `training_focus` - Focus area filtering
- `season` - Season-based queries
- `is_injured` - Injured player filtering

**Composite Indexes:**
- `(career_id, season)` - Career's seasonal training
- `(career_id, season, week)` - Weekly training schedules
- `(player_id, season)` - Player's training history
- `(squad_player_id, training_focus)` - Player's focus history
- `(career_id, squad_player_id, season, week)` (unique) - Prevents duplicate schedules

**Purpose:** Optimizes training management, attribute development tracking, and weekly schedules.

---

### 12. ScoutingAssignment Model (`scouting_assignments`)
**Single Column Indexes:**
- `career_id` (FK) - Career's scouting assignments
- `staff_id` (FK) - Scout's assignments
- `target_player_id` (FK) - Player scouting
- `assignment_type` - Type filtering (player, region, competition)
- `assignment_status` - Status filtering (assigned, in_progress, completed)
- `target_region` - Region filtering
- `target_competition` - Competition filtering
- `start_date` - Date-based queries
- `completion_date` - Completion tracking

**Composite Indexes:**
- `(career_id, assignment_status)` - Career's active assignments
- `(staff_id, assignment_status)` - Scout's workload
- `(career_id, assignment_type)` - Assignment type queries

**Purpose:** Optimizes scouting system, scout workload tracking, and report generation.

---

### 13. MediaEvent Model (`media_events`)
**Single Column Indexes:**
- `career_id` (FK) - Career's media events
- `match_id` (FK) - Match-related events
- `event_type` - Type filtering (5 event types)
- `event_status` - Status filtering (pending, responded, expired)
- `related_player_id` (FK) - Player interview tracking
- `related_club_id` (FK) - Rival comment tracking
- `event_date` - Date-based queries
- `expiry_date` - Expiry tracking

**Composite Indexes:**
- `(career_id, event_status)` - Career's pending events
- `(career_id, event_type)` - Event type queries
- `(career_id, event_date)` - Event history by date
- `(event_status, expiry_date)` - Expired event cleanup

**Purpose:** Optimizes media system, pending event queries, and press conference tracking.

---

### 14. Competition Model (`competitions`)
**Single Column Indexes:**
- `name` - Competition name lookup
- `competition_type` - Type filtering (league, cup)
- `season` - Season filtering
- `country` - Country filtering
- `is_active` - Active competition filtering
- `is_completed` - Completed competition filtering
- `current_matchday` - **NEW** - Progress tracking

**Composite Indexes:**
- `(season, competition_type)` - Season's competitions by type
- `(country, season)` - Country's seasonal competitions
- `(is_active, season)` - Active competitions for season

**Purpose:** Optimizes competition queries, fixture generation, and league table updates.

---

### 15. Fixture Model (`fixtures`)
**Single Column Indexes:**
- `competition_id` (FK) - Competition's fixtures
- `home_club_id` (FK) - Home club fixtures
- `away_club_id` (FK) - Away club fixtures
- `match_id` (FK) - Match linkage
- `matchday` - Matchday filtering
- `scheduled_date` - Date-based queries
- `status` - Status filtering (scheduled, completed, postponed)

**Composite Indexes:**
- `(competition_id, matchday)` - Matchday fixtures
- `(competition_id, status)` - Competition's pending fixtures
- `(home_club_id, away_club_id, scheduled_date)` - Head-to-head queries
- `(scheduled_date, status)` - Upcoming fixtures
- `(competition_id, matchday, home_club_id, away_club_id)` (unique) - Prevents duplicate fixtures

**Purpose:** Optimizes fixture lists, matchday queries, and competition scheduling.

---

## Index Maintenance Best Practices

### 1. Monitor Index Usage
```sql
-- Check index usage statistics
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

### 2. Identify Missing Indexes
```sql
-- Find tables with sequential scans
SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC;
```

### 3. Remove Unused Indexes
```sql
-- Find unused indexes (idx_scan = 0)
SELECT schemaname, tablename, indexname
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexname NOT LIKE 'pg_%';
```

### 4. Analyze Index Bloat
```sql
-- Check index size
SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

### 5. Regular VACUUM and ANALYZE
```sql
-- Maintain index health
VACUUM ANALYZE;
```

---

## Query Optimization Guidelines

### 1. Use Indexed Columns in WHERE Clauses
```python
# Good - Uses index on career_id
squad_players = session.query(SquadPlayer).filter(SquadPlayer.career_id == career_id).all()

# Bad - Full table scan
squad_players = session.query(SquadPlayer).filter(SquadPlayer.morale + 10 > 80).all()
```

### 2. Leverage Composite Indexes
```python
# Good - Uses composite index (career_id, season)
transfers = session.query(Transfer).filter(
    Transfer.career_id == career_id,
    Transfer.season == current_season
).all()

# Less optimal - Only uses career_id index
transfers = session.query(Transfer).filter(
    Transfer.career_id == career_id
).filter(
    Transfer.season == current_season
).all()
```

### 3. Use Covering Indexes When Possible
```python
# Good - Index covers all selected columns
player_names = session.query(Player.name, Player.position).filter(
    Player.club == "Manchester United"
).all()
```

### 4. Avoid Functions on Indexed Columns
```python
# Bad - Function prevents index usage
matches = session.query(Match).filter(
    func.date(Match.match_date) == date.today()
).all()

# Good - Uses index
matches = session.query(Match).filter(
    Match.match_date >= datetime.combine(date.today(), datetime.min.time()),
    Match.match_date < datetime.combine(date.today() + timedelta(days=1), datetime.min.time())
).all()
```

### 5. Use EXPLAIN ANALYZE
```python
# Analyze query performance
from sqlalchemy import text

query = session.query(Player).filter(Player.ca > 150)
explain = session.execute(text(f"EXPLAIN ANALYZE {query}"))
print(explain.fetchall())
```

---

## Performance Monitoring

### Key Metrics to Track
1. **Query Execution Time**: Monitor slow queries (> 100ms)
2. **Index Hit Ratio**: Should be > 99%
3. **Sequential Scans**: Minimize on large tables
4. **Index Bloat**: Keep indexes compact with regular VACUUM
5. **Lock Contention**: Monitor for blocking queries

### Recommended Tools
- **pg_stat_statements**: Track query performance
- **pgBadger**: Analyze PostgreSQL logs
- **pg_stat_user_indexes**: Monitor index usage
- **EXPLAIN ANALYZE**: Analyze individual queries

---

## Conclusion

The current indexing strategy provides comprehensive coverage across all 15 models with:
- **100+ indexes** total across all tables
- **All foreign keys indexed** for optimal JOIN performance
- **All status/enum fields indexed** for filtering queries
- **Composite indexes** for common multi-column query patterns
- **Unique constraints** for data integrity and query optimization

This strategy ensures optimal performance for:
- Player search and filtering (50+ attributes)
- Squad management and contract tracking
- Match simulation and event streaming
- Transfer market and history queries
- Training and attribute development
- Scouting and report generation
- Media events and press conferences
- Competition fixtures and league tables

Regular monitoring and maintenance will ensure continued optimal performance as the application scales.
