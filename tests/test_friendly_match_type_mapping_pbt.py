# Feature: friendly-matches, Property 3: Match-type to home/away mapping is deterministic
"""
Property-based test for ``FriendlyMatchService._resolve_home_away``.

**Validates: Requirements 3.4, 3.5, 3.6, 3.7**

The mapping from ``match_type`` to ``(home_club_id, away_club_id)`` is purely
mechanical: ``"away"`` swaps the two ids, every other valid match type keeps
the player at home. This test asserts that determinism on randomly generated
ids and match types.

  * ``home``           → ``(player, opponent)``       (Req 3.4)
  * ``away``           → ``(opponent, player)``       (Req 3.5)
  * ``commercial_tour``→ ``(player, opponent)``       (Req 3.6 — venue is neutral)
  * ``closed_door``    → ``(player, opponent)``       (Req 3.7 — stadium=training_ground)
"""

from __future__ import annotations

from hypothesis import assume, given, settings, strategies as st

from app.services.friendly_match_service import FriendlyMatchService


# A FriendlyMatchService with no DB session is fine here: ``_resolve_home_away``
# is a pure synchronous helper that does not touch ``self.session``.
_SERVICE = FriendlyMatchService(session=None)  # type: ignore[arg-type]


@given(
    player_club_id=st.integers(min_value=1, max_value=100),
    opponent_club_id=st.integers(min_value=1, max_value=100),
    match_type=st.sampled_from(
        ["home", "away", "closed_door", "commercial_tour"]
    ),
)
@settings(max_examples=100, deadline=None)
def test_resolve_home_away_is_deterministic(
    player_club_id: int,
    opponent_club_id: int,
    match_type: str,
) -> None:
    """**Validates: Requirements 3.4, 3.5, 3.6, 3.7**

    For any ``match_type`` and distinct club ids, ``_resolve_home_away``
    returns ``(opponent, player)`` for ``away`` and ``(player, opponent)``
    for every other valid match type.
    """
    # Per Property 3 the player and opponent are distinct clubs.
    assume(player_club_id != opponent_club_id)

    home_id, away_id = _SERVICE._resolve_home_away(
        match_type, player_club_id, opponent_club_id
    )

    if match_type == "away":
        # Req 3.5: player travels, opponent hosts.
        assert (home_id, away_id) == (opponent_club_id, player_club_id), (
            f"match_type='away' must swap ids; "
            f"got ({home_id}, {away_id}) for "
            f"player={player_club_id}, opponent={opponent_club_id}"
        )
    else:
        # Req 3.4 / 3.6 / 3.7: player nominally home, opponent away.
        assert (home_id, away_id) == (player_club_id, opponent_club_id), (
            f"match_type={match_type!r} must place player at home; "
            f"got ({home_id}, {away_id}) for "
            f"player={player_club_id}, opponent={opponent_club_id}"
        )

    # Both ids in the returned tuple are exactly the inputs (no leaks).
    assert {home_id, away_id} == {player_club_id, opponent_club_id}, (
        f"returned ids {{{home_id}, {away_id}}} differ from inputs "
        f"{{{player_club_id}, {opponent_club_id}}}"
    )
