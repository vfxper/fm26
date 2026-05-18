"""
Static rosters for UEFA Europa League and UEFA Conference League 2025/26.

Format mirrors UCL_PARTICIPANTS: ``(display_name, club_id_or_None, country)``.
``club_id`` is a 1-based index into ``app.data.club_budgets.CLUBS`` when the
club exists there, otherwise ``None`` (we still display the name in the
calendar / table even when the club has no full record in our world).

Source: official 2025/26 group-stage participant lists.
"""

from __future__ import annotations

# ─── UEFA Europa League — 36 clubs, 8 league-phase matches ──────────────
UEL_PARTICIPANTS: list[tuple[str, int | None, str]] = [
    ("Aston Villa", None, "England"),
    ("Basel", None, "Switzerland"),
    ("Bologna", None, "Italy"),
    ("Braga", None, "Portugal"),
    ("Brann", None, "Norway"),
    ("Viktoria Plzeň", None, "Czech Republic"),
    ("Genk", None, "Belgium"),
    ("Go Ahead Eagles", None, "Netherlands"),
    ("Dinamo Zagreb", None, "Croatia"),
    ("Maccabi Tel Aviv", None, "Israel"),
    ("Malmö", None, "Sweden"),
    ("Midtjylland", None, "Denmark"),
    ("Nice", None, "France"),
    ("Nottingham Forest", None, "England"),
    ("Olympique Lyon", None, "France"),
    ("Panathinaikos", None, "Greece"),
    ("PAOK", None, "Greece"),
    ("Porto", None, "Portugal"),
    ("Rangers", None, "Scotland"),
    ("Real Betis", None, "Spain"),
    ("Roma", None, "Italy"),
    ("Celta Vigo", None, "Spain"),
    ("Celtic", None, "Scotland"),
    ("Fenerbahçe", None, "Turkey"),
    ("Ferencváros", None, "Hungary"),
    ("Feyenoord", None, "Netherlands"),
    ("Freiburg", None, "Germany"),
    ("FCSB", None, "Romania"),
    ("Crvena Zvezda", None, "Serbia"),
    ("Sturm Graz", None, "Austria"),
    ("Stuttgart", None, "Germany"),
    ("Young Boys", None, "Switzerland"),
    ("Salzburg", None, "Austria"),
    ("Lille", None, "France"),
    ("Ludogorets", None, "Bulgaria"),
    ("Utrecht", None, "Netherlands"),
]

# ─── UEFA Conference League — 36 clubs, 6 league-phase matches ─────────
UECL_PARTICIPANTS: list[tuple[str, int | None, str]] = [
    ("Aberdeen", None, "Scotland"),
    ("AEK Athens", None, "Greece"),
    ("AEK Larnaca", None, "Cyprus"),
    ("AZ Alkmaar", None, "Netherlands"),
    ("Breidablik", None, "Iceland"),
    ("Hamrun Spartans", None, "Malta"),
    ("Häcken", None, "Sweden"),
    ("Dynamo Kyiv", None, "Ukraine"),
    ("Drita", None, "Kosovo"),
    ("Crystal Palace", None, "England"),
    ("KuPS Kuopio", None, "Finland"),
    ("Legia Warsaw", None, "Poland"),
    ("Lech Poznań", None, "Poland"),
    ("Lincoln Red Imps", None, "Gibraltar"),
    ("Mainz 05", None, "Germany"),
    ("Noah", None, "Armenia"),
    ("Olympique Lyon", None, "France"),
    ("Omonia Nicosia", None, "Cyprus"),
    ("Raków Częstochowa", None, "Poland"),
    ("Rayo Vallecano", None, "Spain"),
    ("Rijeka", None, "Croatia"),
    ("Samsunspor", None, "Turkey"),
    ("Celta", None, "Spain"),
    ("Sigma Olomouc", None, "Czech Republic"),
    ("Slovan Bratislava", None, "Slovakia"),
    ("Sparta Prague", None, "Czech Republic"),
    ("Strasbourg", None, "France"),
    ("Universitatea Craiova", None, "Romania"),
    ("Fiorentina", None, "Italy"),
    ("Celje", None, "Slovenia"),
    ("Shakhtar Donetsk", None, "Ukraine"),
    ("Shamrock Rovers", None, "Ireland"),
    ("Shelbourne", None, "Ireland"),
    ("Shkëndija", None, "North Macedonia"),
    ("Jagiellonia Białystok", None, "Poland"),
    ("Lausanne-Sport", None, "Switzerland"),
]

assert len(UEL_PARTICIPANTS) == 36, (
    f"UEL_PARTICIPANTS must contain exactly 36 entries, got {len(UEL_PARTICIPANTS)}"
)
assert len(UECL_PARTICIPANTS) == 36, (
    f"UECL_PARTICIPANTS must contain exactly 36 entries, got {len(UECL_PARTICIPANTS)}"
)

# ─── How many league-phase matchdays each competition has ─────────────────
# UCL/UEL: 8 matches in the league phase (Swiss-system).
# UECL: 6 matches in the league phase (smaller competition).
LEAGUE_PHASE_MATCHES = {
    "uel": 8,
    "uecl": 6,
}

# ─── Qualification rules per league position (where the player's club
# winds up at the end of a domestic season). Source: user spec.
#
# Each league name maps to a dict of:
#    "ucl"  -> set of league positions that go to UCL
#    "uel"  -> set of league positions that go to UEL
#    "uecl" -> set of league positions that go to UECL
# Cup winners are NOT modelled here — only league-position rules.
# ──────────────────────────────────────────────────────────────────────────
EU_QUALIFICATION_BY_LEAGUE: dict[str, dict[str, set[int]]] = {
    # English Premier League (5 UCL, 1 UEL, 1 UECL)
    "Premier League":      {"ucl": {1, 2, 3, 4, 5}, "uel": {6}, "uecl": {7}},
    # La Liga (5 UCL via coefficient bonus, 1 UEL, 1 UECL)
    "La Liga":             {"ucl": {1, 2, 3, 4, 5}, "uel": {6}, "uecl": {7}},
    # Bundesliga (4 UCL, 1 UEL, 1 UECL)
    "Bundesliga":          {"ucl": {1, 2, 3, 4}, "uel": {5}, "uecl": {6}},
    # Serie A (4 UCL, 1 UEL, 1 UECL)
    "Serie A":             {"ucl": {1, 2, 3, 4}, "uel": {5}, "uecl": {6}},
    # Ligue 1 (3 UCL, 1 UEL, 1 UECL)
    "Ligue 1":             {"ucl": {1, 2, 3}, "uel": {4}, "uecl": {5}},
    # Eredivisie (2 UCL, 1 UEL, 1 UECL)
    "Eredivisie":          {"ucl": {1, 2}, "uel": {3}, "uecl": {4}},
    # Liga Portugal (2 UCL, 1 UEL, 1 UECL)
    "Liga Portugal":       {"ucl": {1, 2}, "uel": {3}, "uecl": {4}},
}


def get_eu_competition_for_position(league_name: str, position: int) -> str | None:
    """
    Return the European competition the club qualifies for given its
    final league position. ``None`` means no European football.
    """
    rules = EU_QUALIFICATION_BY_LEAGUE.get(league_name or "")
    if not rules:
        return None
    if position in rules.get("ucl", set()):
        return "ucl"
    if position in rules.get("uel", set()):
        return "uel"
    if position in rules.get("uecl", set()):
        return "uecl"
    return None
