"""
Seed local SQLite database with player data from CSV.

Usage:
    python seed_local.py

Reads 2600球员属性.csv and inserts players + clubs into fm26_local.db.
Run run_local.py first to create the database tables.
"""

import csv
import sqlite3
import os
import sys

CSV_PATH = os.path.join(os.path.dirname(__file__), "2600球员属性.csv")
DB_PATH = os.path.join(os.path.dirname(__file__), "fm26_local.db")

# CSV columns (first 50 columns from header)
CSV_COLUMNS = [
    'name', 'position', 'age', 'ca', 'pa', 'nationality', 'club',
    'corners', 'crossing', 'dribbling', 'finishing', 'first_touch', 'free_kicks',
    'heading', 'long_shots', 'long_throws', 'marking', 'passing', 'penalty',
    'tackling', 'technique', 'aggression', 'anticipation', 'bravery', 'composure',
    'concentration', 'decisions', 'determination', 'flair', 'leadership',
    'off_the_ball', 'positioning', 'teamwork', 'vision', 'work_rate',
    'acceleration', 'agility', 'balance', 'jumping', 'stamina', 'pace',
    'endurance', 'strength', 'price', 'wage', 'height', 'weight',
    'left_foot', 'right_foot', 'uid'
]

# DB column mapping (CSV column -> DB column)
# Most map directly, but some need renaming
DB_COLUMN_MAP = {
    'free_kicks': 'free_kick',
    'jumping': 'jumping_reach',
    'endurance': 'natural_fitness',
    'penalty': 'penalty_taking',
}


def safe_int(value, default=10):
    """Convert value to int safely, returning default if not possible."""
    if value is None or value == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        # Try stripping whitespace and non-numeric chars
        cleaned = ''.join(c for c in str(value) if c.isdigit() or c == '-')
        if cleaned:
            try:
                return int(cleaned)
            except ValueError:
                return default
        return default


def parse_money(value, default=0):
    """Parse a CSV money string like ``"£149,602,800"`` or ``"£496,918"``
    into an integer number of base units (pounds). Strips currency
    symbols, commas and whitespace. Returns ``default`` on failure.
    """
    if value is None or value == '':
        return default
    s = str(value).strip()
    if not s:
        return default
    # Strip currency symbols and grouping separators
    for ch in ('£', '$', '€', ',', ' ', '\xa0'):
        s = s.replace(ch, '')
    if not s:
        return default
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return default


def clean_price(value):
    """Clean price string - keep as-is for display."""
    if not value or value.strip() == '':
        return '0'
    return value.strip()


# ─── Position parsing ──────────────────────────────────────────────────────
#
# CSV ``position`` column uses FM-style codes like:
#   ``GK``               → goalkeeper
#   ``D RLC``            → defender (right/left/centre)
#   ``D/WB R``           → defender or wing-back, right side
#   ``AM/ST RL``         → attacking midfielder OR striker, right or left
#   ``D/DM/M/AM C``      → can play CB / DM / CM / AM (centre)
#
# We expand each entry into the cartesian product (line × side) and store
# both the raw string and a comma-separated list of expanded positions, so
# the engine and the UI can answer "can this player play X?".

LINE_NAMES = {
    'GK': 'GK',
    'D':  'D',   # defender (centre = CB, with side = FB)
    'WB': 'WB',  # wing-back
    'DM': 'DM',  # defensive mid
    'M':  'M',   # central midfielder
    'AM': 'AM',  # attacking mid
    'ST': 'ST',  # striker
}
SIDE_LETTERS = {'R', 'L', 'C'}


def parse_positions(raw: str) -> list[str]:
    """
    Expand an FM-style position string into a flat list like
    ``['CB', 'CM', 'AM', 'ST', ...]``.

    Examples:
        ``GK``           → ['GK']
        ``ST C``         → ['ST']
        ``AM/ST RL``     → ['AML', 'AMR', 'STL', 'STR']
        ``D/WB R``       → ['DR', 'WBR']
        ``D RLC``        → ['DR', 'DL', 'CB']
        ``D/DM/M/AM C``  → ['CB', 'DM', 'CM', 'AM']
    """
    if not raw:
        return []
    s = raw.strip()
    if not s:
        return []
    if s == 'GK':
        return ['GK']

    parts = s.split(' ', 1)
    lines_str = parts[0]
    sides_str = parts[1].strip() if len(parts) > 1 else 'C'

    lines = [ln for ln in lines_str.split('/') if ln in LINE_NAMES]
    if not lines:
        return []

    # Sides are concatenated letters: 'R', 'L', 'C', 'RL', 'RLC', etc.
    sides = [ch for ch in sides_str if ch in SIDE_LETTERS]
    if not sides:
        sides = ['C']

    result: list[str] = []
    for line in lines:
        for side in sides:
            if line == 'D' and side == 'C':
                code = 'CB'
            elif line == 'M' and side == 'C':
                code = 'CM'
            elif side == 'C':
                code = line  # GK, DM, AM, ST without side
            else:
                code = f'{line}{side}'
            if code not in result:
                result.append(code)
    return result


def parse_int_keep_zero(value, default=0):
    """Parse an integer, returning ``default`` only on parse failure."""
    if value is None or value == '':
        return default
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        cleaned = ''.join(c for c in str(value) if c.isdigit() or c == '-')
        if cleaned and cleaned != '-':
            try:
                return int(cleaned)
            except ValueError:
                return default
        return default


def seed_database():
    """Load CSV data into SQLite database."""
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run 'python run_local.py' first to create the database, then stop it and run this script.")
        sys.exit(1)

    if not os.path.exists(CSV_PATH):
        print(f"ERROR: CSV file not found at {CSV_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if players table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players'")
    if not cursor.fetchone():
        print("ERROR: 'players' table does not exist. Run run_local.py first.")
        conn.close()
        sys.exit(1)

    # Clear existing data
    cursor.execute("DELETE FROM players")
    cursor.execute("DELETE FROM clubs")
    conn.commit()

    # Ensure dev user exists
    cursor.execute(
        "INSERT OR IGNORE INTO users (id, telegram_user_id, email, username, email_verified, auth_provider, language_code) "
        "VALUES (1, 123456, 'dev@local.test', 'Developer', 1, 'telegram', 'en')"
    )
    conn.commit()

    print(f"Reading CSV: {CSV_PATH}")

    clubs_seen = {}
    players_inserted = 0
    errors = 0

    with open(CSV_PATH, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header

        for row_num, row in enumerate(reader, start=2):
            if len(row) < 50:
                errors += 1
                continue

            # Extract first 50 columns into the named dict
            data = dict(zip(CSV_COLUMNS, row[:50]))

            # Real currency values live AFTER the named columns:
            #   col[85] → transfer value (price)  e.g. "£149,602,800"
            #   col[95] → weekly wage             e.g. "£496,918"
            real_price_str = row[85] if len(row) > 85 else ''
            real_wage_str = row[95] if len(row) > 95 else ''

            name = data['name'].strip()
            if not name:
                errors += 1
                continue
            # CSV sometimes appends "(Club,Country)" or "(Country)" to
            # disambiguate the name. Strip everything from the first '('
            # onwards so the rendered name is just "Cristiano Ronaldo",
            # not "Cristiano Ronaldo(Al-Nassr Football Club,Portugal)".
            paren = name.find('(')
            if paren > 0:
                name = name[:paren].strip()

            club_name = data['club'].strip() if data['club'] else 'Free Agent'

            # Track clubs
            if club_name and club_name not in clubs_seen:
                clubs_seen[club_name] = len(clubs_seen) + 1

            # Parse attributes
            uid = data.get('uid', '').strip()
            if not uid:
                uid = f"player_{row_num}"
            else:
                uid = f"{uid}_{row_num}"  # Make unique by appending row number
            position = data['position'].strip() if data['position'] else 'Unknown'
            positions_list = parse_positions(position)
            positions_str = ','.join(positions_list)
            age = safe_int(data['age'], 25)
            ca = safe_int(data['ca'], 100)
            pa = safe_int(data['pa'], 100)
            nationality = data['nationality'].strip() if data['nationality'] else 'Unknown'

            # Clamp CA/PA to valid ranges. CSV PA may come negative
            # (FM uses negative numbers to express ranged PA, e.g. -8 →
            # "potential between 140 and 160"). Treat as abs() so the
            # UI shows a real number; clamp to a reasonable max if the
            # absolute value is small (single-digit "stars" rating).
            ca = max(1, min(200, ca))
            pa_val = pa
            if pa_val < 0:
                # Negative PA: tier code from FM. Map common ranges:
                #   -1 → ~80, -2 → ~100, -3 → ~120, -4 → ~140,
                #   -5 → ~155, -6 → ~165, -7 → ~175, -8 → ~185,
                #   -9 → ~195, -10 → 200
                tier_map = {1: 80, 2: 100, 3: 120, 4: 140, 5: 155,
                            6: 165, 7: 175, 8: 185, 9: 195, 10: 200}
                pa_val = tier_map.get(abs(pa_val), max(ca, 100))
            if pa_val == 0:
                pa_val = ca
            pa_val = max(1, min(200, pa_val))

            # Technical attributes
            corners = safe_int(data['corners'])
            crossing = safe_int(data['crossing'])
            dribbling = safe_int(data['dribbling'])
            finishing = safe_int(data['finishing'])
            first_touch = safe_int(data['first_touch'])
            free_kick = safe_int(data['free_kicks'])
            heading = safe_int(data['heading'])
            long_shots = safe_int(data['long_shots'])
            long_throws = safe_int(data['long_throws'])
            marking = safe_int(data['marking'])
            passing = safe_int(data['passing'])
            penalty_taking = safe_int(data['penalty'])
            tackling = safe_int(data['tackling'])
            technique = safe_int(data['technique'])

            # Mental attributes
            aggression = safe_int(data['aggression'])
            anticipation = safe_int(data['anticipation'])
            bravery = safe_int(data['bravery'])
            composure = safe_int(data['composure'])
            concentration = safe_int(data['concentration'])
            decisions = safe_int(data['decisions'])
            determination = safe_int(data['determination'])
            flair = safe_int(data['flair'])
            leadership = safe_int(data['leadership'])
            off_the_ball = safe_int(data['off_the_ball'])
            positioning = safe_int(data['positioning'])
            teamwork = safe_int(data['teamwork'])
            vision = safe_int(data['vision'])
            work_rate = safe_int(data['work_rate'])

            # Physical attributes
            acceleration = safe_int(data['acceleration'])
            agility = safe_int(data['agility'])
            balance = safe_int(data['balance'])
            jumping_reach = safe_int(data['jumping'])
            stamina = safe_int(data['stamina'])
            pace = safe_int(data['pace'])
            natural_fitness = safe_int(data['endurance'])
            strength = safe_int(data['strength'])

            # Financial — REAL currency values from CSV columns 85 / 95.
            # These come pre-formatted ("£149,602,800" / "£496,918") so we
            # parse them with `parse_money`. Fallback to a CA-keyed formula
            # only if the column is missing (rare).
            real_wage = parse_money(real_wage_str, 0)
            real_price = parse_money(real_price_str, 0)

            if real_wage > 0:
                wage = real_wage
            else:
                ca_clamped = max(40, min(200, ca))
                if ca_clamped <= 90:
                    wage = 3_000 + (ca_clamped - 40) * 540
                elif ca_clamped <= 120:
                    wage = 30_000 + (ca_clamped - 90) * 3_000
                elif ca_clamped <= 150:
                    wage = 120_000 + (ca_clamped - 120) * 7_667
                elif ca_clamped <= 180:
                    wage = 350_000 + (ca_clamped - 150) * 11_667
                else:
                    wage = 700_000 + (ca_clamped - 180) * 33_333

            if real_price > 0:
                price = str(real_price)
            else:
                ca_clamped = max(40, min(200, ca))
                price = str(max(50_000, ca_clamped * 100_000))
            height = safe_int(data['height'], 180)
            weight = safe_int(data['weight'], 75)
            left_foot = safe_int(data['left_foot'], 10)
            right_foot = safe_int(data['right_foot'], 10)

            # Clamp all 1-20 attributes
            def clamp(v, lo=1, hi=20):
                return max(lo, min(hi, v))

            try:
                cursor.execute("""
                    INSERT INTO players (
                        uid, name, position, positions, age, ca, pa, nationality, club,
                        corners, crossing, dribbling, finishing, first_touch, free_kick,
                        heading, long_shots, long_throws, marking, passing, penalty_taking,
                        tackling, technique,
                        aggression, anticipation, bravery, composure, concentration,
                        decisions, determination, flair, leadership, off_the_ball,
                        positioning, teamwork, vision, work_rate,
                        acceleration, agility, balance, jumping_reach, stamina, pace,
                        natural_fitness, strength,
                        price, wage, height, weight, left_foot, right_foot
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    uid, name, position, positions_str, age, ca, pa_val, nationality, club_name,
                    clamp(corners), clamp(crossing), clamp(dribbling), clamp(finishing),
                    clamp(first_touch), clamp(free_kick), clamp(heading), clamp(long_shots),
                    clamp(long_throws), clamp(marking), clamp(passing), clamp(penalty_taking),
                    clamp(tackling), clamp(technique),
                    clamp(aggression), clamp(anticipation), clamp(bravery), clamp(composure),
                    clamp(concentration), clamp(decisions), clamp(determination), clamp(flair),
                    clamp(leadership), clamp(off_the_ball), clamp(positioning), clamp(teamwork),
                    clamp(vision), clamp(work_rate),
                    clamp(acceleration), clamp(agility), clamp(balance), clamp(jumping_reach),
                    clamp(stamina), clamp(pace), clamp(natural_fitness), clamp(strength),
                    price, wage, height, weight, clamp(left_foot), clamp(right_foot),
                ))
                players_inserted += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  Row {row_num} error: {e} (name={name})")

    # Insert clubs
    print(f"\nInserting {len(clubs_seen)} clubs...")
    for club_name, club_id in clubs_seen.items():
        try:
            cursor.execute("""
                INSERT INTO clubs (id, name, reputation, league, country,
                    stadium_level, training_facilities_level, youth_academy_level,
                    medical_centre_level, scouting_network_level,
                    balance, transfer_budget, wage_budget, matchday_revenue, stadium_capacity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                club_id, club_name, 50, 'League', 'Unknown',
                2, 2, 2, 2, 2,
                50000000, 20000000, 500000, 100000, 30000,
            ))
        except Exception as e:
            print(f"  Club insert error for '{club_name}': {e}")

    conn.commit()
    conn.close()

    print(f"\n{'='*50}")
    print(f"  Seed complete!")
    print(f"  Players inserted: {players_inserted}")
    print(f"  Clubs created: {len(clubs_seen)}")
    print(f"  Errors/skipped: {errors}")
    print(f"{'='*50}")

    # Build / refresh an ASCII-only index column for accent-insensitive
    # search ("mbappe" → "Mbappé", "perez" → "Pérez"). We do this in
    # Python with `unicodedata.normalize` so SQLite's plain LIKE is
    # enough at query time.
    print("Building ASCII search index ...")
    import unicodedata
    con2 = sqlite3.connect(DB_PATH)
    cur2 = con2.cursor()
    try:
        cur2.execute("ALTER TABLE players ADD COLUMN name_ascii TEXT")
    except sqlite3.OperationalError:
        pass
    cur2.execute("SELECT id, name FROM players")
    for pid, nm in cur2.fetchall():
        if not nm:
            continue
        ascii_name = "".join(
            c for c in unicodedata.normalize("NFKD", nm)
            if not unicodedata.combining(c) and ord(c) < 128
        ).lower()
        cur2.execute("UPDATE players SET name_ascii = ? WHERE id = ?",
                     (ascii_name, pid))
    cur2.execute("CREATE INDEX IF NOT EXISTS idx_players_name_ascii "
                 "ON players(name_ascii)")
    con2.commit()
    con2.close()
    print(f"  ASCII index built.")


if __name__ == "__main__":
    seed_database()
