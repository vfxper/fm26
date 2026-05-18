"""
Squad role assignment.

Each `squad_players.status` row is one of six roles describing how the
player fits into the team:

    star      — звезда команды
    important — важный игрок
    starter   — стартовый состав
    rotation  — игрок ротации
    backup    — игрок замены
    prospect  — молодой подающий надежды (age < 22)

Role is computed RELATIVELY to the rest of the squad, so a CA-160
player at Burnley can be a `star` while the same CA at Real Madrid
would only be `important`. This is what makes weak teams have stars
even though their players are objectively mediocre.

Assignment algorithm (per career, run once at career start and again
when the squad composition changes a lot, e.g. mass-buy):

  1. Compute squad CA percentile for each player (0..100).
  2. Anyone < 22 years old with above-median CA -> `prospect`
     (potential is what matters for them, not current CA).
  3. The TOP 2 by CA become `star` if they are clearly above the rest
     (CA gap to median >= 8). Otherwise no stars (e.g. evenly spread
     squads).
  4. The next 4 by CA -> `important`.
  5. The next 5 by CA -> `starter`.
  6. The next 6 by CA -> `rotation`.
  7. Everyone else -> `backup`.

The function operates on a list of dicts:
    [{"sp_id": 1, "ca": 178, "age": 28}, ...]
and returns a parallel list of role strings, one per input dict.

A separate helper `recommended_role_for_signing(player_ca, squad_cas)`
returns what role a *new* player would naturally fit into when joining
the squad — used during transfer negotiations to push back if the
player is over-/under-valued for the offered role.
"""
from __future__ import annotations

from statistics import median
from typing import Iterable, List, Sequence

ROLE_STAR = "star"
ROLE_IMPORTANT = "important"
ROLE_STARTER = "starter"
ROLE_ROTATION = "rotation"
ROLE_BACKUP = "backup"
ROLE_PROSPECT = "prospect"

ALL_ROLES = (
    ROLE_STAR, ROLE_IMPORTANT, ROLE_STARTER,
    ROLE_ROTATION, ROLE_BACKUP, ROLE_PROSPECT,
)

# Display labels (Russian) for the UI.
ROLE_LABELS_RU: dict[str, str] = {
    ROLE_STAR:      "Звезда",
    ROLE_IMPORTANT: "Важный игрок",
    ROLE_STARTER:   "Стартовый состав",
    ROLE_ROTATION:  "Ротация",
    ROLE_BACKUP:    "Запасной",
    ROLE_PROSPECT:  "Подающий надежды",
}

# Sort priority — used to display the squad sorted by role (stars first).
ROLE_SORT_KEY: dict[str, int] = {
    ROLE_STAR: 0,
    ROLE_IMPORTANT: 1,
    ROLE_STARTER: 2,
    ROLE_ROTATION: 3,
    ROLE_BACKUP: 4,
    ROLE_PROSPECT: 5,
}


def auto_assign_roles(squad: Sequence[dict]) -> List[str]:
    """
    Given a squad as a sequence of dicts each containing ``ca`` and
    ``age``, return a parallel list of role strings.

    The order of the input list is preserved (the function does not
    sort it in place).
    """
    if not squad:
        return []

    n = len(squad)
    cas = [int(p.get("ca") or 0) for p in squad]
    ages = [int(p.get("age") or 25) for p in squad]
    med = median(cas) if cas else 0

    # Sort indices by CA descending — that gives us the ranking.
    order = sorted(range(n), key=lambda i: cas[i], reverse=True)

    # Decide if "star" tier exists. Two conditions:
    # (1) the top player must be at least 8 CA above the squad median
    #     (otherwise the squad has no clear leader), AND
    # (2) the top must be at least 3 CA above the SECOND-best (otherwise
    #     they're peers and there's no single "star").
    top_ca = cas[order[0]] if order else 0
    second_ca = cas[order[1]] if len(order) > 1 else top_ca
    has_stars = (top_ca - med) >= 8 and (top_ca - second_ca) >= 3

    # Tiers, by sorted-rank position.
    star_slots     = 2 if has_stars else 0
    important_slots = 4
    starter_slots  = 5
    rotation_slots = 6

    role_for_rank: list[str] = []
    consumed = 0
    for slots, role in (
        (star_slots,      ROLE_STAR),
        (important_slots, ROLE_IMPORTANT),
        (starter_slots,   ROLE_STARTER),
        (rotation_slots,  ROLE_ROTATION),
    ):
        for _ in range(slots):
            role_for_rank.append(role)
            consumed += 1
            if consumed >= n:
                break
        if consumed >= n:
            break
    while len(role_for_rank) < n:
        role_for_rank.append(ROLE_BACKUP)

    # Map rank -> original index, then build the result list.
    out = [ROLE_BACKUP] * n
    for rank, idx in enumerate(order):
        out[idx] = role_for_rank[rank]

    # Override: anyone under 22 with above-median CA becomes a prospect,
    # regardless of where they ranked. This lets weak players who are
    # young still be marked as future prospects, AND prevents young
    # superstars who'd otherwise be stars from blocking that label
    # (a 19yo Yamal IS a star — so we only re-tag mid-tier youngsters,
    # not the top-3).
    top_3_idx = set(order[:3])
    for i, (age, ca) in enumerate(zip(ages, cas)):
        if age < 22 and ca >= med and i not in top_3_idx:
            out[i] = ROLE_PROSPECT

    return out


def recommended_role_for_signing(player_ca: int, squad_cas: Iterable[int]) -> str:
    """
    What role would a *new* player naturally slot into?

    Used by negotiation flow: if the user offers a "backup" role to a
    player whose CA puts them in star territory for this squad, the
    agent would push back / break off talks.
    """
    cas = sorted([int(c or 0) for c in squad_cas], reverse=True)
    if not cas:
        return ROLE_STARTER
    med = median(cas)
    top = cas[0] if cas else 0
    pca = int(player_ca or 0)

    # Star tier: better than current top OR 8+ above median.
    if pca >= top + 1 or pca >= med + 12:
        return ROLE_STAR
    if pca >= med + 6:
        return ROLE_IMPORTANT
    if pca >= med:
        return ROLE_STARTER
    if pca >= med - 6:
        return ROLE_ROTATION
    return ROLE_BACKUP


def role_acceptable(player_ca: int, offered_role: str, squad_cas: Iterable[int]) -> bool:
    """
    Will the agent accept the given role? An agent rejects if the
    offered role is two tiers lower than what their CA deserves.
    A star will never accept rotation or below; an important player
    won't accept backup.
    """
    expected = recommended_role_for_signing(player_ca, squad_cas)
    rank = {
        ROLE_STAR: 0, ROLE_IMPORTANT: 1, ROLE_STARTER: 2,
        ROLE_ROTATION: 3, ROLE_BACKUP: 4, ROLE_PROSPECT: 2,
    }
    return rank[offered_role] <= rank[expected] + 1
