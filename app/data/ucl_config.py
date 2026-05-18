"""
Static configuration for the UEFA Champions League (2024/25+ format).

This module defines the 36 UCL participants, league-phase target dates,
knockout-phase scheduling constants, the final venue, and the Round of 16
bracket map. All constants are pure data — runtime scheduling, pairings,
and persistence live in `app/services/ucl_generator.py`.

`club_id` values are 1-based indices into `app.data.club_budgets.CLUBS`.
Participants not present in CLUBS use `None` and are tracked by
`club_name` only (Requirement 1.4).
"""

from __future__ import annotations

from datetime import date, timedelta

# ---------------------------------------------------------------------------
# 36 UCL participants for the current season.
# Each entry: (display_name, club_id_or_None, country)
#
# club_id is the 1-based index in CLUBS from app.data.club_budgets when the
# club exists there, otherwise None. The indices below were verified against
# the actual CLUBS list in app/data/club_budgets.py — do NOT edit them by
# hand without re-verifying with the same lookup.
# ---------------------------------------------------------------------------
UCL_PARTICIPANTS: list[tuple[str, int | None, str]] = [
    # England (6)
    ("Arsenal", 3, "England"),
    ("Liverpool", 2, "England"),
    ("Manchester City", 1, "England"),
    ("Newcastle United", 6, "England"),
    ("Tottenham Hotspur", 7, "England"),
    ("Chelsea", 4, "England"),
    # Spain (5)
    ("Athletic Bilbao", 25, "Spain"),
    ("A. Madrid", 23, "Spain"),
    ("Barcelona", 22, "Spain"),
    ("Villarreal", 26, "Spain"),
    ("R. Madrid", 21, "Spain"),
    # Germany (4)
    ("Bayern Munich", 41, "Germany"),
    ("Bayer Leverkusen", 44, "Germany"),
    ("Borussia Dortmund", 43, "Germany"),
    ("Eintracht Frankfurt", 46, "Germany"),
    # Italy (4)
    ("Atalanta", 63, "Italy"),
    ("Inter Milan", 60, "Italy"),
    ("Juventus", 59, "Italy"),
    ("Napoli", 62, "Italy"),
    # France (3)
    ("Marseille", 81, "France"),
    ("Monaco", 80, "France"),
    ("Paris Saint-Germain", 79, "France"),
    # Netherlands (2)
    ("Ajax", 115, "Netherlands"),
    ("PSV Eindhoven", 116, "Netherlands"),
    # Portugal (2)
    ("Benfica", 97, "Portugal"),
    ("Sporting CP", 98, "Portugal"),
    # Belgium (2) — not in CLUBS
    ("Club Brugge", None, "Belgium"),
    ("Union Saint-Gilloise", None, "Belgium"),
    # Other 8 — only Galatasaray is in CLUBS
    ("Bodø/Glimt", None, "Norway"),
    ("Galatasaray", 133, "Turkey"),
    ("Kairat", None, "Kazakhstan"),
    ("Qarabağ", None, "Azerbaijan"),
    ("Copenhagen", None, "Denmark"),
    ("Olympiacos", None, "Greece"),
    ("Pafos", None, "Cyprus"),
    ("Slavia Prague", None, "Czech Republic"),
]

assert len(UCL_PARTICIPANTS) == 36, (
    f"UCL_PARTICIPANTS must contain exactly 36 entries, "
    f"got {len(UCL_PARTICIPANTS)}"
)

# ---------------------------------------------------------------------------
# League phase target dates.
#
# Each tuple: (month, week_of_month, weekday)
#   - month: 1-12 (January is treated as belonging to year+1 for MD7/MD8)
#   - week_of_month: 1-4, or 5 to mean "last week of month"
#   - weekday: 1 = Tuesday, 2 = Wednesday
#
# UCLGenerator.assign_matchdays_to_dates() resolves these into concrete
# dates and shifts them if they collide with FIFA windows or locked
# calendar events.
# ---------------------------------------------------------------------------
UCL_LEAGUE_PHASE_TARGETS: list[tuple[int, int, int]] = [
    (9, 3, 1),    # MD1: 3rd Tuesday of September
    (10, 1, 2),   # MD2: 1st Wednesday of October
    (10, 3, 1),   # MD3: 3rd Tuesday of October
    (11, 1, 2),   # MD4: 1st Wednesday of November
    (11, 4, 1),   # MD5: 4th Tuesday of November
    (12, 2, 2),   # MD6: 2nd Wednesday of December
    (1, 3, 1),    # MD7: 3rd Tuesday of January (year + 1)
    (1, 5, 2),    # MD8: last Wednesday of January (year + 1)
]

# ---------------------------------------------------------------------------
# Knockout playoff scheduling (mid-February of year + 1).
# ---------------------------------------------------------------------------
UCL_KO_PLAYOFF_BASE_MONTH: int = 2          # February
UCL_KO_PLAYOFF_LEG_GAP_DAYS: int = 7        # 7 days between leg 1 and leg 2

# ---------------------------------------------------------------------------
# Round of 16 / Quarter Final / Semi Final first-leg target months
# (in the calendar year + 1 from the season start).
# ---------------------------------------------------------------------------
UCL_R16_LEG1_MONTH: int = 3   # early March
UCL_QF_LEG1_MONTH: int = 4    # early April
UCL_SF_LEG1_MONTH: int = 4    # late April / early May

# ---------------------------------------------------------------------------
# Final venue — fixed neutral ground per Requirement 6.3.
# ---------------------------------------------------------------------------
UCL_FINAL_VENUE: str = "Puskás Aréna, Budapest"


def get_final_date(year: int) -> date:
    """
    Return the last Saturday of May for the given year.

    Used to schedule the single-leg Final (Requirement 6.2).
    `year` is the calendar year of the final itself (i.e. season_start_year + 1).
    """
    d = date(year, 5, 31)
    # weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
    while d.weekday() != 5:
        d -= timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# Round of 16 bracket map.
#
# Maps the seed of a direct qualifier (rank 1-8 from the league phase) to
# the playoff-winner index it faces (1 = highest-ranked playoff winner,
# 8 = lowest-ranked). Standard pairing places seed 1 against the lowest
# playoff winner, and the higher-seeded club plays the second leg at home.
# ---------------------------------------------------------------------------
UCL_R16_BRACKET_MAP: dict[int, int] = {
    1: 8,
    2: 7,
    3: 6,
    4: 5,
    5: 4,
    6: 3,
    7: 2,
    8: 1,
}
