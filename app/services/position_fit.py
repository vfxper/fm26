"""
Position fit calculator.

Each player has a `position` string like ``"AM/ST RL"``, ``"D C"``, ``"GK"``,
``"DM/M C"``. The match engine picks the top 11 players by CA, but not all
of them are natural for the role they end up filling. A goalkeeper played
as a striker should perform terribly. A natural CB asked to play AM should
be much weaker than the CA suggests.

`fit(player_position, role_zone)` returns a multiplier in roughly
``[0.20, 1.00]`` that scales the player's CA when computing per-event
probabilities (shots, saves, passes).

Role zones used by the engine:
    "GK"   — goalkeeper
    "DEF"  — central / wide defenders (D, WB, FB)
    "MID"  — defensive / central / attacking mids (DM, M, AM)
    "ATT"  — strikers (ST, F, FW)

Heuristic: parse the position string into a set of FM-style codes,
map each to a role zone, and look up the best match in a small fit
table. Players with multiple positions take the BEST fit (e.g.
"D/WB/DM RC" can play DEF or MID).
"""

from __future__ import annotations

import re
from typing import Iterable

# ──────────────────────────────────────────────────────────────────────
# 1. Parse "AM/ST RL" → {"AM", "ST"} (we ignore L/R/C side info here)
# ──────────────────────────────────────────────────────────────────────
_TOKEN_RE = re.compile(r"[A-Z]+")

# Set of recognised FM position tokens. Order matters for longest-match.
_KNOWN_POSITIONS = {
    "GK",
    # defenders
    "D", "DC", "DL", "DR",
    "WB", "WBL", "WBR",
    "SW",  # sweeper
    # mids
    "DM",
    "M", "MC", "ML", "MR",
    "AM", "AMC", "AML", "AMR",
    # attackers
    "F", "FC", "FW",
    "ST", "STC",
}


def _normalise(position: str) -> set[str]:
    """Extract the set of FM position codes from a position string."""
    if not position:
        return set()
    # "AM/ST RL" → "AM ST RL", upper-case.
    s = position.upper().replace("/", " ").replace(",", " ")
    raw = _TOKEN_RE.findall(s)
    out: set[str] = set()
    for tok in raw:
        # Strip trailing side letters (R, L, C, RC, LC, RL, RLC...) — they
        # mean "this position on the right/left/centre" and don't change
        # the role zone.
        core = tok
        while core and core not in _KNOWN_POSITIONS and core[-1] in "RLC":
            core = core[:-1]
        if core in _KNOWN_POSITIONS:
            out.add(core)
        elif tok in _KNOWN_POSITIONS:
            out.add(tok)
    return out


# ──────────────────────────────────────────────────────────────────────
# 2. Map position code → role zone
# ──────────────────────────────────────────────────────────────────────
_TOKEN_TO_ZONE: dict[str, str] = {
    "GK": "GK",
    "D": "DEF", "DC": "DEF", "DL": "DEF", "DR": "DEF",
    "WB": "DEF", "WBL": "DEF", "WBR": "DEF",
    "SW": "DEF",
    "DM": "MID",
    "M": "MID", "MC": "MID", "ML": "MID", "MR": "MID",
    "AM": "MID", "AMC": "MID", "AML": "MID", "AMR": "MID",
    "F": "ATT", "FC": "ATT", "FW": "ATT",
    "ST": "ATT", "STC": "ATT",
}


# ──────────────────────────────────────────────────────────────────────
# 3. Fit table: rows = role zone, cols = natural zone of player
# ──────────────────────────────────────────────────────────────────────
# A goalkeeper at striker is catastrophic; a striker at GK is also useless.
# Adjacent zones (DEF↔MID, MID↔ATT) lose ~20–30%.
# Same zone is 1.00.
_FIT_TABLE: dict[tuple[str, str], float] = {
    # GK
    ("GK",  "GK"):  1.00,
    ("GK",  "DEF"): 0.30,
    ("GK",  "MID"): 0.20,
    ("GK",  "ATT"): 0.20,

    # DEF
    ("DEF", "GK"):  0.35,
    ("DEF", "DEF"): 1.00,
    ("DEF", "MID"): 0.75,
    ("DEF", "ATT"): 0.50,

    # MID
    ("MID", "GK"):  0.25,
    ("MID", "DEF"): 0.78,
    ("MID", "MID"): 1.00,
    ("MID", "ATT"): 0.82,

    # ATT
    ("ATT", "GK"):  0.20,
    ("ATT", "DEF"): 0.55,
    ("ATT", "MID"): 0.80,
    ("ATT", "ATT"): 1.00,
}


def fit(player_position: str, role_zone: str) -> float:
    """
    Return a fit multiplier in [0.20, 1.00] for a player asked to play
    ``role_zone``.

    ``role_zone`` must be one of: "GK", "DEF", "MID", "ATT".
    Multi-position players take the best fit among their zones.
    """
    if not role_zone:
        return 1.0
    role_zone = role_zone.upper()
    if role_zone not in ("GK", "DEF", "MID", "ATT"):
        return 1.0

    tokens = _normalise(player_position)
    if not tokens:
        # Unknown / empty → assume MID (least costly fallback).
        natural_zones: set[str] = {"MID"}
    else:
        natural_zones = {_TOKEN_TO_ZONE[t] for t in tokens if t in _TOKEN_TO_ZONE}
        if not natural_zones:
            natural_zones = {"MID"}

    return max(
        _FIT_TABLE.get((role_zone, nz), 0.5) for nz in natural_zones
    )


def role_zone_of(position: str) -> str:
    """Best-effort: pick the dominant natural zone of a player.
    Priority GK > ATT > MID > DEF when multiple are present, because
    the picker (top-N by CA) tends to favour DEF naturals; if a player
    can also play ATT we'd rather use them as ATT."""
    tokens = _normalise(position)
    zones = {_TOKEN_TO_ZONE[t] for t in tokens if t in _TOKEN_TO_ZONE}
    for preferred in ("GK", "ATT", "MID", "DEF"):
        if preferred in zones:
            return preferred
    return "MID"


def assign_roles(players: Iterable[dict]) -> list[dict]:
    """
    Greedily assign role_zone to each of (up to) 11 players to fill a
    1 GK + 4 DEF + 4 MID + 2 ATT formation, given as natural a fit as
    possible. Each input dict must carry a ``"position"`` key. Output
    adds a ``"role_zone"`` key in-place.

    Strategy:
      1. The first player whose tokens contain GK is the keeper
         (or, if none, the worst CA outfielder is shoved in goal).
      2. Remaining 10 are sorted by CA descending. Each is offered
         the role with the highest ``fit(player_pos, role_zone)``
         that still has a free slot (slots: 4 DEF, 4 MID, 2 ATT).
      3. If all slots are full, role_zone defaults to "MID".
    """
    pool = [dict(p) for p in players]  # don't mutate caller copies
    if not pool:
        return pool

    # 1. Keeper
    keeper = None
    for p in pool:
        if "GK" in _normalise(p.get("position", "")):
            keeper = p
            break
    if keeper is None:
        keeper = min(pool, key=lambda p: p.get("ca", 0))
    keeper["role_zone"] = "GK"

    outfield = [p for p in pool if p is not keeper]
    outfield.sort(key=lambda p: p.get("ca", 0), reverse=True)

    slots = {"DEF": 4, "MID": 4, "ATT": 2}
    for p in outfield:
        # Score each open slot for this player. Pick the slot where
        # the player's NATURAL fit is highest. This keeps a striker who
        # also lists ST as a striker even if a higher-CA winger could
        # fill that slot — the winger is a better natural ATT, but the
        # ST is the natural striker.
        best_zone, best_score = "MID", -1.0
        for zone, free in slots.items():
            if free <= 0:
                continue
            score = fit(p.get("position", ""), zone)
            # Tie-breaker: a pure attacker (ATT zone in their tokens)
            # MUST go ATT before any "can also play ATT" forward.
            if score > best_score:
                best_zone, best_score = zone, score
        if slots.get(best_zone, 0) > 0:
            slots[best_zone] -= 1
        p["role_zone"] = best_zone

    return [keeper] + outfield
