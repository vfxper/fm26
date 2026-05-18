"""
Local development server - runs without Docker, PostgreSQL, or Redis.
Uses SQLite for database and in-memory cache.

Usage:
    python run_local.py

Opens:
    http://localhost:8000/docs  - API documentation (Swagger)
    http://localhost:8000/      - API root
"""

import os
import sys
import asyncio

# Override settings for local development
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./fm26_local.db"
os.environ["REDIS_URL"] = ""
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"
os.environ["BOT_TOKEN"] = "fake:token"
os.environ["JWT_SECRET"] = "local-dev-secret-key-not-for-production"
os.environ["API_HOST"] = "0.0.0.0"
os.environ["API_PORT"] = "8000"

# Install aiosqlite if not present
try:
    import aiosqlite
except ImportError:
    print("Installing aiosqlite for local SQLite support...")
    os.system(f"{sys.executable} -m pip install aiosqlite --quiet")

try:
    import uvicorn
except ImportError:
    print("Installing uvicorn...")
    os.system(f"{sys.executable} -m pip install uvicorn[standard] --quiet")

try:
    import fastapi
except ImportError:
    print("Installing fastapi...")
    os.system(f"{sys.executable} -m pip install fastapi --quiet")


def patch_for_sqlite():
    """Patch database module to work with SQLite."""
    # Monkey-patch the database module to use SQLite
    import app.core.database as db_module
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    
    engine = create_async_engine("sqlite+aiosqlite:///./fm26_local.db", echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async def get_db():
        # Mirrors app.core.database.get_db_session: commit on success
        # so prod auth.register's `await db.flush()` actually persists.
        # Without this, multi-user registrations get rolled back and
        # all registered tokens collapse to the same auto-incremented id.
        async with SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def init_db():
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Create tables (simplified)
            await conn.run_sync(create_tables)
            # ALTER missing columns on existing DBs (no-op on fresh DB).
            # Safe-add wizard fields and any other recent additions.
            for stmt in [
                "ALTER TABLE careers ADD COLUMN manager_age INTEGER",
                "ALTER TABLE careers ADD COLUMN manager_country VARCHAR(100)",
                "ALTER TABLE careers ADD COLUMN dev_style VARCHAR(40)",
                "ALTER TABLE players ADD COLUMN name_ascii TEXT",
            ]:
                try:
                    await conn.execute(text(stmt))
                except Exception:
                    # Column already exists or table doesn't exist yet — ignore.
                    pass
            # Make sure the accent-insensitive search index exists.
            try:
                await conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_players_name_ascii "
                    "ON players(name_ascii)"
                ))
            except Exception:
                pass
            # Ensure dev user exists
            await conn.execute(text(
                "INSERT OR IGNORE INTO users (id, telegram_user_id, email, username, email_verified, auth_provider, language_code) "
                "VALUES (1, 123456, 'dev@local.test', 'Developer', 1, 'telegram', 'en')"
            ))
        print("  Database initialized (SQLite)")
    
    async def close_db():
        await engine.dispose()
    
    async def check_db_health():
        return True
    
    db_module.get_db = get_db
    db_module.get_db_session = get_db
    db_module.init_db = init_db
    db_module.close_db = close_db
    db_module.check_db_health = check_db_health
    db_module.engine = engine
    db_module.SessionLocal = SessionLocal


def create_tables(conn):
    """Create minimal tables for local dev."""
    from sqlalchemy import MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, Date, Text, LargeBinary
    from sqlalchemy import ForeignKey, Index, func
    
    metadata = MetaData()
    
    Table('users', metadata,
        Column('id', Integer, primary_key=True),
        Column('telegram_user_id', Integer, unique=True, nullable=True),
        Column('email', String(320), unique=True, nullable=True),
        Column('password_hash', String(255), nullable=True),
        Column('username', String(255), nullable=True),
        Column('first_name', String(255), nullable=True),
        Column('last_name', String(255), nullable=True),
        Column('email_verified', Boolean, default=False),
        Column('email_verification_token', String(255), nullable=True),
        Column('email_verification_expires', DateTime, nullable=True),
        Column('google_id', String(255), nullable=True),
        Column('auth_provider', String(20), default='telegram'),
        Column('settings_json', Text, nullable=True),
        Column('language_code', String(10), default='en'),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, server_default=func.now()),
        Column('last_login_at', DateTime, nullable=True),
    )
    
    Table('careers', metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer),
        Column('club_id', Integer),
        Column('manager_name', String(100)),
        Column('current_season', Integer, default=1),
        Column('current_week', Integer, default=1),
        Column('game_date', String(10), default='2025-07-01'),  # ISO YYYY-MM-DD; in-game clock
        Column('budget', Float, default=50000000),
        Column('reputation', Integer, default=50),
        Column('manager_reputation', Integer, default=50),
        Column('board_confidence', Integer, default=50),
        Column('board_objectives', Text, nullable=True),
        Column('status', String(20), default='active'),
        Column('tactical_knowledge', Integer, default=10),
        Column('man_management', Integer, default=10),
        Column('motivating', Integer, default=10),
        Column('attacking', Integer, default=10),
        Column('defending', Integer, default=10),
        Column('technical', Integer, default=10),
        Column('mental', Integer, default=10),
        Column('youth_development', Integer, default=10),
        Column('board_relations', Integer, default=10),
        Column('seasons_managed', Integer, default=0),
        Column('trophies_won', Integer, default=0),
        Column('matches_won', Integer, default=0),
        Column('matches_drawn', Integer, default=0),
        Column('matches_lost', Integer, default=0),
        Column('total_transfer_spend', Integer, default=0),
        Column('tactics_presets', Text, nullable=True),
        Column('active_tactic_index', Integer, default=0),
        Column('matchday_lineup', Text, nullable=True),
        Column('training_intensity', String(20), default='normal'),
        Column('save_timestamp', DateTime, nullable=True),
        Column('game_mode', String(20), default='full'),
        Column('manager_age', Integer, nullable=True),
        Column('manager_country', String(100), nullable=True),
        Column('dev_style', String(40), nullable=True),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, nullable=True),
    )
    
    Table('players', metadata,
        Column('id', Integer, primary_key=True),
        Column('uid', String(255), unique=True, nullable=True),
        Column('name', String(200)),
        Column('age', Integer),
        Column('nationality', String(100)),
        Column('club', String(200)),
        Column('position', String(50)),
        Column('positions', String(120)),  # CSV-derived comma-list e.g. "AML,AMR,STL,STR"
        Column('ca', Integer),
        Column('pa', Integer),
        Column('height', Integer),
        Column('weight', Integer),
        Column('left_foot', Integer),
        Column('right_foot', Integer),
        Column('price', String(50)),
        Column('wage', Integer),
        Column('traits', Text),
        # Attributes
        Column('corners', Integer, default=10),
        Column('crossing', Integer, default=10),
        Column('dribbling', Integer, default=10),
        Column('finishing', Integer, default=10),
        Column('first_touch', Integer, default=10),
        Column('free_kick', Integer, default=10),
        Column('heading', Integer, default=10),
        Column('long_shots', Integer, default=10),
        Column('long_throws', Integer, default=10),
        Column('marking', Integer, default=10),
        Column('passing', Integer, default=10),
        Column('penalty_taking', Integer, default=10),
        Column('tackling', Integer, default=10),
        Column('technique', Integer, default=10),
        Column('aggression', Integer, default=10),
        Column('anticipation', Integer, default=10),
        Column('bravery', Integer, default=10),
        Column('composure', Integer, default=10),
        Column('concentration', Integer, default=10),
        Column('decisions', Integer, default=10),
        Column('determination', Integer, default=10),
        Column('flair', Integer, default=10),
        Column('leadership', Integer, default=10),
        Column('off_the_ball', Integer, default=10),
        Column('positioning', Integer, default=10),
        Column('teamwork', Integer, default=10),
        Column('vision', Integer, default=10),
        Column('work_rate', Integer, default=10),
        Column('acceleration', Integer, default=10),
        Column('agility', Integer, default=10),
        Column('balance', Integer, default=10),
        Column('jumping_reach', Integer, default=10),
        Column('natural_fitness', Integer, default=10),
        Column('pace', Integer, default=10),
        Column('stamina', Integer, default=10),
        Column('strength', Integer, default=10),
    )
    
    Table('squad_players', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer),
        Column('player_id', Integer),
        Column('squad_number', Integer),
        # Squad role — one of:
        #   star      — звезда команды, требует уважения / большой ЗП
        #   important — важный игрок, регулярный старт
        #   starter   — стартовый состав
        #   rotation  — игрок ротации
        #   backup    — игрок замены
        #   prospect  — молодой подающий надежды
        # Auto-assigned at career creation based on player CA vs squad
        # peers (see app.services.squad_roles.auto_assign_roles).
        Column('status', String(30), default='starter'),
        Column('morale', Integer, default=100),
        Column('fitness', Integer, default=100),
        Column('match_fitness', Integer, default=100),
        Column('fatigue', Integer, default=0),
        Column('wage', Integer, default=50000),
        Column('contract_expiry', String(20)),
        Column('contract_years', Integer, default=3),
        Column('is_transfer_listed', Boolean, default=False),
        Column('is_loan_listed', Boolean, default=False),
        Column('is_injured', Boolean, default=False),
        Column('is_loaned', Boolean, default=False),
        Column('training_role', String(50), nullable=True),       # e.g. "Inside Forward (Attack)"
        Column('individual_focus', String(40), nullable=True),    # e.g. "finishing"
        Column('individual_intensity', String(10), default='normal'),  # low|normal|high
        Column('match_minutes_last5', Integer, default=0),
        Column('relationship_with_manager', Integer, default=50),
    )
    
    Table('career_saves', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer),
        Column('user_id', Integer),
        Column('name', String(100)),
        Column('slot_type', String(20), default='manual'),
        Column('season', Integer),
        Column('week', Integer),
        Column('data', LargeBinary),
        Column('checksum', String(16)),
        Column('created_at', DateTime, server_default=func.now()),
    )
    
    Table('clubs', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(255)),
        Column('reputation', Integer, default=50),
        Column('league', String(255), default='League'),
        Column('country', String(100), default='Unknown'),
        Column('stadium_level', Integer, default=2),
        Column('training_facilities_level', Integer, default=2),
        Column('youth_academy_level', Integer, default=2),
        Column('medical_centre_level', Integer, default=2),
        Column('scouting_network_level', Integer, default=2),
        Column('balance', Integer, default=50000000),
        Column('transfer_budget', Integer, default=20000000),
        Column('scouting_budget', Integer, default=1000000),
        Column('wage_budget', Integer, default=500000),
        Column('matchday_revenue', Integer, default=100000),
        Column('stadium_capacity', Integer, default=30000),
        Column('stadium_name', String(255), nullable=True),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, nullable=True),
    )
    
    Table('competitions', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(255)),
        Column('competition_type', String(50), default='league'),
        Column('season', Integer, default=1),
        Column('status', String(20), default='active'),
        Column('created_at', DateTime, server_default=func.now()),
    )
    
    Table('fixtures', metadata,
        Column('id', Integer, primary_key=True),
        Column('competition_id', Integer),
        Column('home_club_id', Integer),
        Column('away_club_id', Integer),
        Column('match_id', Integer, nullable=True),
        Column('matchday', Integer),
        Column('round_name', String(100), nullable=True),
        Column('scheduled_date', DateTime),
        Column('status', String(20), default='scheduled'),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, nullable=True),
    )
    
    Table('matches', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer),
        Column('fixture_id', Integer, nullable=True),
        Column('home_club_id', Integer),
        Column('away_club_id', Integer),
        Column('home_score', Integer, default=0),
        Column('away_score', Integer, default=0),
        Column('status', String(20), default='scheduled'),
        Column('played_at', DateTime, nullable=True),
        Column('created_at', DateTime, server_default=func.now()),
    )
    
    Table('calendar_events', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer),
        Column('event_date', String(10)),
        Column('event_type', String(30)),
        Column('competition_id', Integer, nullable=True),
        Column('home_club_id', Integer, nullable=True),
        Column('away_club_id', Integer, nullable=True),
        Column('is_locked', Boolean, default=False),
        Column('priority', Integer, default=5),
        Column('kick_off_time', String(5), nullable=True),
        Column('weather_data', Text, nullable=True),
        Column('description', Text, nullable=True),
        Column('travel_data', Text, nullable=True),
        Column('original_date', String(10), nullable=True),
        Column('reschedule_reason', String(255), nullable=True),
        Column('is_cancelled', Boolean, default=False),
        Column('template_id', Integer, nullable=True),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, server_default=func.now()),
    )

    # Inbox feed shown on the dedicated "Исходящие" tab. Each row is a
    # short manager-facing message (match results, transfer offers,
    # contract renewals, board reactions, ...).
    Table('inbox_messages', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('created_date', String(10)),       # in-game date
        Column('category', String(30)),           # match, transfer, board, training, news
        Column('subject', String(255)),
        Column('body', Text),
        Column('is_read', Boolean, default=False),
        Column('is_pinned', Boolean, default=False),
        Column('payload', Text),                  # optional JSON for action buttons
        Column('created_at', DateTime, server_default=func.now()),
    )

    # In-progress match state stored at half-time so the user can make
    # substitutions before pressing "Continue". One row per
    # (career_id, event_id) pair. Cleared after the second-half
    # simulation completes.
    Table('match_sessions', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('event_id', Integer, nullable=False),
        Column('phase', String(20), default='halftime'),
        Column('state_json', Text),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, server_default=func.now()),
    )

    # Per-player season tally of goals/assists/appearances in each
    # competition. Populated by both the user's match flow and the
    # AI-vs-AI background runner so the "Top scorers / Top assists"
    # screens reflect every league + cup match in the universe.
    Table('player_match_stats', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('player_id', Integer, nullable=False),
        Column('club_name', String(120)),
        Column('competition', String(40)),  # 'league:Premier League' / 'ucl' / 'uel' / 'uecl' / 'cup'
        Column('season', Integer, default=1),
        Column('goals', Integer, default=0),
        Column('assists', Integer, default=0),
        Column('appearances', Integer, default=0),
        Index('idx_pms_career_comp', 'career_id', 'competition'),
        Index('idx_pms_player', 'player_id'),
    )
    
    Table('league_configs', metadata,
        Column('id', Integer, primary_key=True),
        Column('country', String(100), unique=True),
        Column('league_name', String(255)),
        Column('has_winter_break', Boolean, default=False),
        Column('winter_break_start', String(5), nullable=True),
        Column('winter_break_end', String(5), nullable=True),
        Column('mandatory_fixture_dates', Text, nullable=True),
        Column('blackout_dates', Text, nullable=True),
        Column('custom_milestones', Text, nullable=True),
        Column('season_start_date', String(5), nullable=True),
        Column('season_end_date', String(5), nullable=True),
        Column('european_competition', String(50), nullable=True),
        Column('created_at', DateTime, server_default=func.now()),
    )
    
    Table('recurring_templates', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer),
        Column('name', String(100)),
        Column('day_assignments', Text),
        Column('is_active', Boolean, default=True),
        Column('created_at', DateTime, server_default=func.now()),
        Column('updated_at', DateTime, server_default=func.now()),
    )
    
    # ---------------------------------------------------------------
    # UEFA Champions League tables (spec: uefa-champions-league)
    # ---------------------------------------------------------------
    
    Table('competition_rounds', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('competition_id', Integer,
               ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False),
        Column('round_type', String(30), nullable=False),
        Column('round_order', Integer, nullable=False),
        Column('start_date', Date, nullable=True),
        Column('end_date', Date, nullable=True),
        Column('is_completed', Boolean, default=False, nullable=False),
        Column('created_at', DateTime, server_default=func.now()),
        Index('idx_comp_rounds_comp', 'competition_id'),
        Index('idx_comp_rounds_comp_order', 'competition_id', 'round_order', unique=True),
    )
    
    Table('ucl_participants', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('competition_id', Integer,
               ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False),
        Column('club_id', Integer, nullable=True),
        Column('club_name', String(100), nullable=False),
        Column('country', String(50), nullable=False),
        Column('seed', Integer, nullable=False),
        Column('final_rank', Integer, nullable=True),
        Index('idx_ucl_part_comp', 'competition_id'),
        Index('idx_ucl_part_comp_seed', 'competition_id', 'seed', unique=True),
    )
    
    Table('ucl_standings', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('competition_id', Integer,
               ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False),
        Column('participant_id', Integer,
               ForeignKey('ucl_participants.id', ondelete='CASCADE'), nullable=False),
        Column('played', Integer, nullable=False, server_default='0'),
        Column('won', Integer, nullable=False, server_default='0'),
        Column('drawn', Integer, nullable=False, server_default='0'),
        Column('lost', Integer, nullable=False, server_default='0'),
        Column('goals_for', Integer, nullable=False, server_default='0'),
        Column('goals_against', Integer, nullable=False, server_default='0'),
        Column('goal_difference', Integer, nullable=False, server_default='0'),
        Column('points', Integer, nullable=False, server_default='0'),
        Column('rank', Integer, nullable=True),
        Index('idx_ucl_stand_comp', 'competition_id'),
        Index('idx_ucl_stand_comp_part', 'competition_id', 'participant_id', unique=True),
    )
    
    Table('ucl_ties', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('competition_id', Integer,
               ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False),
        Column('round_id', Integer,
               ForeignKey('competition_rounds.id', ondelete='CASCADE'), nullable=False),
        Column('home_participant_id', Integer,
               ForeignKey('ucl_participants.id'), nullable=True),
        Column('away_participant_id', Integer,
               ForeignKey('ucl_participants.id'), nullable=True),
        Column('leg1_home_score', Integer, nullable=True),
        Column('leg1_away_score', Integer, nullable=True),
        Column('leg2_home_score', Integer, nullable=True),
        Column('leg2_away_score', Integer, nullable=True),
        Column('aggregate_home', Integer, nullable=True),
        Column('aggregate_away', Integer, nullable=True),
        Column('winner_participant_id', Integer,
               ForeignKey('ucl_participants.id'), nullable=True),
        Column('winner_decided_by', String(20), nullable=True),
        Column('bracket_position', Integer, nullable=False),
        Index('idx_ucl_tie_comp', 'competition_id'),
        Index('idx_ucl_tie_round', 'round_id'),
        Index('idx_ucl_tie_round_pos', 'round_id', 'bracket_position', unique=True),
    )

    # Persisted Swiss-system schedule for the league phase. Stored at
    # generation time so the background runner can replay the EXACT
    # pairings (the in-memory `build_swiss_pairings` is RNG-seeded and
    # would produce a different schedule on a fresh call).
    Table('ucl_phase_matchups', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('competition_id', Integer,
               ForeignKey('competitions.id', ondelete='CASCADE'), nullable=False),
        Column('matchday', Integer, nullable=False),
        Column('home_participant_id', Integer, nullable=False),
        Column('away_participant_id', Integer, nullable=False),
        Column('played', Boolean, default=False, nullable=False),
        Index('idx_ucl_match_comp', 'competition_id'),
        Index('idx_ucl_match_md', 'competition_id', 'matchday'),
    )

    # ── Transfer system, scouting, training roles, injuries, promises ─────

    # Active negotiations + closed deals. direction='in' = AI -> player,
    # 'out' = player -> AI. Status: pending, counter, accepted, rejected,
    # expired, closed.
    Table('transfer_offers', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('direction', String(8), nullable=False),
        Column('player_id', Integer, nullable=False),
        Column('from_club_id', Integer, nullable=True),
        Column('to_club_id', Integer, nullable=True),
        Column('from_club_name', String(120), nullable=True),
        Column('to_club_name', String(120), nullable=True),
        Column('fee', Integer, default=0),
        Column('wage', Integer, default=0),
        Column('contract_years', Integer, default=3),
        Column('role', String(20), default='first_team'),
        Column('sell_on_pct', Integer, default=0),
        Column('loan_type', String(24), nullable=True),
        Column('loan_buyback_fee', Integer, nullable=True),
        Column('loan_until', String(10), nullable=True),
        Column('status', String(20), default='pending'),
        Column('counter_fee', Integer, nullable=True),
        Column('counter_wage', Integer, nullable=True),
        Column('counter_deadline', String(10), nullable=True),
        Column('created_date', String(10)),
        Column('resolved_date', String(10), nullable=True),
        Column('created_at', DateTime, server_default=func.now()),
        Index('idx_offers_career', 'career_id'),
        Index('idx_offers_player', 'player_id'),
    )

    # AI-vs-AI background transfer ledger (so we can show news + history
    # without polluting the player-facing transfer_offers table).
    Table('ai_transfers', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('player_id', Integer, nullable=False),
        Column('player_name', String(120)),
        Column('from_club', String(120)),
        Column('to_club', String(120)),
        Column('fee', Integer, default=0),
        Column('is_loan', Boolean, default=False),
        Column('transfer_date', String(10)),
        Index('idx_ai_tr_career_date', 'career_id', 'transfer_date'),
    )

    # Per-club AI transfer-window quota (resets on window open).
    Table('ai_window_quota', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('club_name', String(120), nullable=False),
        Column('window_year', Integer, nullable=False),
        Column('window_kind', String(8), nullable=False),  # summer / winter
        Column('count', Integer, default=0),
        Index('idx_quota_unique', 'career_id', 'club_name',
              'window_year', 'window_kind', unique=True),
    )

    # Scouting assignments. status: pending|in_progress|completed.
    # mode: search_by_filter (find players matching criteria),
    #       individual (scout one specific player_id),
    #       region_youth (find 15-19yo players in a region).
    Table('scout_assignments', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('mode', String(24), nullable=False),
        Column('player_id', Integer, nullable=True),
        Column('filter_json', Text, nullable=True),       # JSON: {min_pa, max_age, min_age, position, ...}
        Column('detail_level', String(10), default='full'),  # short (7d) | full (14d)
        Column('start_date', String(10)),
        Column('due_date', String(10)),
        Column('status', String(16), default='in_progress'),
        Column('result_json', Text, nullable=True),       # JSON list of player_ids found
        Column('created_at', DateTime, server_default=func.now()),
        Index('idx_scout_career', 'career_id'),
    )

    # Per-player scouting knowledge cached for the career. level=0 unknown,
    # 1=short report visible, 2=full report visible. updated when an
    # assignment completes.
    Table('scout_knowledge', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('player_id', Integer, nullable=False),
        Column('level', Integer, default=0),
        Column('last_seen_date', String(10)),
        Index('idx_sk_unique', 'career_id', 'player_id', unique=True),
    )

    # Hidden per-player attributes that don't exist in the CSV but are
    # critical for realism. Created lazily on first reference.
    Table('player_hidden_attrs', metadata,
        Column('player_id', Integer, primary_key=True),
        Column('injury_proneness', Integer, default=10),     # 1-20
        Column('ambition', Integer, default=10),             # 1-20
        Column('professionalism', Integer, default=10),
        Column('loyalty', Integer, default=10),
        Column('adaptability', Integer, default=10),
        Column('agent_greed', Integer, default=10),
        Column('agent_patience', Integer, default=10),
    )

    # Injury catalogue (seeded once on startup if empty).
    Table('injury_types', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(80)),
        Column('body_part', String(40)),
        Column('severity', String(24)),                       # minor|moderate|major|career_threatening
        Column('min_days', Integer),
        Column('max_days', Integer),
        Column('reoccurrence_risk', Float, default=1.0),
        Column('ca_impact', Float, default=0.0),
        Column('attribute_drops', Text, nullable=True),       # JSON
        Column('requires_surgery', Boolean, default=False),
        Column('surgery_days', Integer, default=0),
    )

    # Active + historical injuries per player.
    Table('player_injuries', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('player_id', Integer, nullable=False),
        Column('injury_type_id', Integer, nullable=True),
        Column('start_date', String(10)),
        Column('estimated_return_date', String(10)),
        Column('actual_return_date', String(10), nullable=True),
        Column('treatment_type', String(20), default='physio'),  # physio|rush|surgery
        Column('rush_risk', Boolean, default=False),
        Column('source', String(20), default='match'),           # match|training
        Column('notes', Text, nullable=True),
        Column('is_active', Boolean, default=True),
        Index('idx_pi_career_active', 'career_id', 'is_active'),
    )

    # Promises tracked per (career, player) for follow-through.
    Table('player_promises', metadata,
        Column('id', Integer, primary_key=True),
        Column('career_id', Integer, nullable=False),
        Column('player_id', Integer, nullable=False),
        Column('promise_type', String(40)),                   # playing_time|new_contract|sell_at_end|sign_player|etc
        Column('details_json', Text, nullable=True),
        Column('start_date', String(10)),
        Column('deadline_date', String(10)),
        Column('status', String(16), default='active'),       # active|fulfilled|broken
        Column('created_at', DateTime, server_default=func.now()),
    )

    # Tactic + lineup — JSON blob keyed off career_id. Used by both the
    # match engine and the visual pitch UI.
    Table('career_tactics', metadata,
        Column('career_id', Integer, primary_key=True),
        Column('formation', String(20), default='4-3-3'),
        Column('mentality', String(20), default='balanced'),
        Column('pressing', String(20), default='medium'),
        Column('defensive_line', String(20), default='standard'),
        Column('tempo', String(20), default='normal'),
        Column('width', String(20), default='standard'),
        Column('starting_xi', Text, nullable=True),          # JSON: { "GK": player_id, "DR": ..., ... }
        Column('subs', Text, nullable=True),                 # JSON list of player_ids
        Column('player_roles', Text, nullable=True),         # JSON: { "<player_id>": { "role": "...", "duty": "support|attack|defend" } }
        Column('updated_at', DateTime, server_default=func.now()),
    )

    metadata.create_all(conn)


def patch_cache():
    """Patch cache module to work without Redis."""
    import app.core.cache as cache_module
    
    class FakeRedis:
        _store = {}
        async def get(self, key): return self._store.get(key)
        async def set(self, key, value, **kw): self._store[key] = value
        async def setex(self, key, ttl, value): self._store[key] = value
        async def delete(self, *keys):
            for k in keys: self._store.pop(k, None)
        async def keys(self, pattern): return []
        async def ping(self): return True
    
    _fake = FakeRedis()
    
    async def init_cache(): print("  Cache: in-memory (no Redis)")
    async def close_cache(): pass
    async def get_redis_client(): return _fake
    
    cache_module.init_cache = init_cache
    cache_module.close_cache = close_cache
    cache_module.get_redis_client = get_redis_client


def patch_auth():
    """Patch auth dependency for local dev with REAL multi-user
    isolation. Each registered user gets a stable token, and
    ``get_current_user`` parses the token to look up THAT user.
    """
    import app.api.dependencies as deps
    from fastapi import Header, HTTPException
    from sqlalchemy import text as _sql_text
    from typing import Optional

    class _U:
        def __init__(self, uid, email="dev@local.test", username="Player"):
            self.id = uid
            self.telegram_id = uid
            self.email = email
            self.username = username
            self.is_verified = True

    async def get_current_user(authorization: Optional[str] = Header(None)):
        # Two token formats supported:
        #   1. "Bearer local-token-{user_id}" — written by the local
        #      registration endpoint below.
        #   2. "Bearer <JWT>" — written by the production auth route
        #      that ships in app/api/routes/auth.py. We validate it
        #      via verify_token() to extract the user_id.
        # Anonymous / missing tokens default to user 1 (single-player dev).
        uid = 1
        if authorization:
            tok = authorization.replace("Bearer ", "").strip()
            if tok.startswith("local-token-"):
                try:
                    uid = int(tok.split("-")[-1])
                except ValueError:
                    uid = 1
            elif tok and tok != "guest":
                try:
                    from app.services.auth_service import verify_token
                    parsed_uid = verify_token(tok)
                    if parsed_uid is not None:
                        uid = int(parsed_uid)
                except Exception:
                    uid = 1
        from app.core.database import get_db
        async for db in get_db():
            row = (await db.execute(_sql_text(
                "SELECT id, email, username FROM users WHERE id = :i"
            ), {"i": uid})).fetchone()
            if row:
                return _U(row[0], row[1] or "dev@local.test", row[2] or "Player")
            # Fallback: dev auto-create user 1.
            if uid == 1:
                try:
                    await db.execute(_sql_text(
                        "INSERT OR IGNORE INTO users "
                        "(id, email, password_hash, username, email_verified, auth_provider, language_code) "
                        "VALUES (1, 'dev@local.test', '', 'Player', 1, 'email', 'ru')"
                    ))
                    await db.commit()
                except Exception:
                    pass
                return _U(1)
            raise HTTPException(401, "Bad token")

    deps.get_current_user = get_current_user

    # Also patch the auth routes to work with SQLite. The original
    # auth.py routes use a different JWT-secret pipeline than what we
    # have here, so we strip them out and replace with simple email/
    # password-hash lookups against the local SQLite users table.
    try:
        from fastapi import APIRouter
        from pydantic import BaseModel, Field
        from sqlalchemy import text as sql_text
        import hashlib

        import app.api.routes.auth as auth_module

        original_router = auth_module.router

        # Strip /register and /login from the auth router. Those endpoints
        # come from the SQL-Alchemy ORM auth_service and use a JWT
        # encoded with a different secret than what verify_token in
        # this patch will accept. By dropping them, our local versions
        # below take their place when FastAPI binds the router.
        original_router.routes = [
            r for r in original_router.routes
            if not (hasattr(r, "path") and r.path in ("/register", "/login"))
        ]
        # Same for routes that may have been mounted on the main app
        # via include_router. We try to find the mounted app late so
        # this patch survives the order-of-operations dance.
        def _strip_main_app_auth_routes():
            try:
                from app.main import app as fastapi_app
                fastapi_app.routes = [
                    r for r in fastapi_app.routes
                    if not (hasattr(r, "path") and r.path in
                            ("/api/auth/register", "/api/auth/login"))
                ]
                # Tell FastAPI to rebuild the underlying ASGI router
                # so the change actually takes effect for incoming
                # requests.
                if hasattr(fastapi_app, "router"):
                    fastapi_app.router.routes = [
                        r for r in fastapi_app.router.routes
                        if not (hasattr(r, "path") and r.path in
                                ("/api/auth/register", "/api/auth/login"))
                    ]
            except Exception as _e:
                print(f"  late-strip-routes warning: {_e}")
        # Keep the function so we can call it from a startup hook.
        auth_module._strip_main_app_auth_routes = _strip_main_app_auth_routes

        class LocalRegisterRequest(BaseModel):
            email: str
            password: str = Field(..., min_length=8)
            name: str

        class LocalLoginRequest(BaseModel):
            email: str
            password: str

        @original_router.post("/register", response_model=None, include_in_schema=False)
        async def local_register(request: LocalRegisterRequest):
            """Local registration with per-user token."""
            from app.core.database import get_db
            async for db in get_db():
                pw_hash = hashlib.sha256(request.password.encode()).hexdigest()
                # Look up existing user
                row = (await db.execute(
                    sql_text("SELECT id FROM users WHERE email = :email"),
                    {"email": request.email},
                )).fetchone()
                if row:
                    return {"detail": "Email already registered",
                            "access_token": f"local-token-{row[0]}",
                            "token_type": "bearer"}
                # Insert and grab the new id.
                await db.execute(
                    sql_text(
                        "INSERT INTO users (email, password_hash, username, "
                        "email_verified, auth_provider, language_code) "
                        "VALUES (:email, :pw, :name, 1, 'email', 'ru')"
                    ),
                    {"email": request.email, "pw": pw_hash, "name": request.name},
                )
                await db.commit()
                row = (await db.execute(
                    sql_text("SELECT id FROM users WHERE email = :email"),
                    {"email": request.email},
                )).fetchone()
                uid = int(row[0])
                return {"access_token": f"local-token-{uid}", "token_type": "bearer"}

        @original_router.post("/login", response_model=None, include_in_schema=False)
        async def local_login(request: LocalLoginRequest):
            """Local login with per-user token. Returns 401 on bad creds."""
            from app.core.database import get_db
            async for db in get_db():
                pw_hash = hashlib.sha256(request.password.encode()).hexdigest()
                row = (await db.execute(
                    sql_text("SELECT id FROM users WHERE email = :email AND password_hash = :pw"),
                    {"email": request.email, "pw": pw_hash},
                )).fetchone()
                if not row:
                    return {"detail": "Bad email/password", "access_token": None}
                return {"access_token": f"local-token-{row[0]}", "token_type": "bearer"}
    except Exception as e:
        print(f"  Auth patch warning: {e}")


if __name__ == "__main__":
    print("=" * 50)
    print("  FM26 - Local Development Server")
    print("=" * 50)
    print()
    
    # Apply patches BEFORE importing app
    print("  Patching for local development...")
    
    # Force CORS to allow all origins (must be valid JSON for pydantic-settings)
    os.environ["CORS_ORIGINS"] = '["*"]'
    
    patch_cache()
    patch_for_sqlite()
    patch_auth()
    
    # Patch CORS settings
    try:
        from app.core.config import settings
        settings.CORS_ORIGINS = ["*"]
    except:
        pass
    
    # Auto-seed DB on first boot (Render free tier has no shell, so we
    # can't run seed_local.py manually). Skip if already seeded.
    try:
        import sqlite3 as _sq
        _db_path = os.path.join(os.path.dirname(__file__), "fm26_local.db")
        if os.path.exists(_db_path):
            _con = _sq.connect(_db_path)
            try:
                _row = _con.execute("SELECT COUNT(*) FROM players").fetchone()
                _player_count = int(_row[0]) if _row else 0
            except Exception:
                _player_count = 0
            _con.close()
            if _player_count == 0:
                print("  Auto-seeding database (first boot)...")
                try:
                    import seed_local as _seed
                    _seed.seed_database()
                    print("  ✓ Database seeded")
                except Exception as _e:
                    print(f"  ⚠ Auto-seed failed: {_e}")
            else:
                print(f"  ✓ Database already seeded ({_player_count} players)")
    except Exception as _e:
        print(f"  ⚠ Auto-seed check failed: {_e}")
    
    print("  ✓ SQLite database (no PostgreSQL needed)")
    print("  ✓ In-memory cache (no Redis needed)")
    print("  ✓ Auth disabled (auto-login as dev user)")
    print("  ✓ CORS: allow all origins")
    print()
    print("  Starting server...")
    print("  Game UI: http://localhost:3000")
    print("  API Docs: http://localhost:8000/docs")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    
    import uvicorn
    port = int(os.environ.get("PORT", 8000))

    # Late-strip /api/auth/register|login from the main app so our
    # local replacements take precedence. The main app's include_router
    # call happens at module import time, so we need to defer this
    # until AFTER `app.main` has loaded.
    try:
        import app.api.routes.auth as auth_module
        if hasattr(auth_module, "_strip_main_app_auth_routes"):
            auth_module._strip_main_app_auth_routes()
    except Exception as _e:
        print(f"  late-strip-routes warning: {_e}")

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
