"""
FixtureGenerator — Generate real round-robin league fixture schedules
for La Liga, Premier League, and Serie A.

Implements the standard circle method round-robin algorithm:
- 20 teams play every other team home and away (38 matchdays, 380 matches)
- First half: 19 matchdays of 10 matches each
- Second half: mirror of first half with home/away swapped
- Each pair of teams meets exactly twice (once home, once away)

Fixtures are distributed across Saturdays in the season window, skipping
international break windows and winter breaks. ~30% of matches receive
randomized TV slots; the rest default to Saturday 15:00.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import List, Optional, Tuple

from app.data.club_budgets import CLUBS
from app.data.league_configs import (
    FIFA_INTERNATIONAL_WINDOWS,
    get_league_config,
)


# ─── Country → league-name keyword mapping ────────────────────────────────────

# Only these three leagues are supported for now.
_COUNTRY_TO_LEAGUE_KEYWORD = {
    "England": "Premier League",
    "Spain": "La Liga",
    "Italy": "Serie A",
}


# ─── TV / kick-off slot pool ──────────────────────────────────────────────────

# Default kick-off is Saturday 15:00. ~30% of league matches get a TV slot
# drawn uniformly from this list. (Day shifts are not applied to the date —
# the slot affects only the kick-off time; the match still falls on the
# scheduled Saturday for a simple model.)
_TV_SLOTS = ["12:30", "17:30", "20:00", "21:00"]

# Probability that a given league match is moved to a TV slot.
_TV_SLOT_PROBABILITY = 0.30


# ─── Round-robin generation (circle method) ───────────────────────────────────


def generate_round_robin(team_ids: List[int]) -> List[List[Tuple[int, int]]]:
    """
    Generate a full home-and-away round-robin schedule.

    Uses the classic circle method:
      - team_ids[0] is fixed
      - remaining teams rotate by one position each round
      - n−1 rounds in the first half, mirrored for the second half
      - home/away alternates by round so each team's home/away count balances

    With an odd number of teams, a None placeholder is added; pairs involving
    None are skipped (giving that team a bye for the round).

    Args:
        team_ids: list of unique team identifiers (e.g., 1-based club ids)

    Returns:
        List of matchdays. Each matchday is a list of (home_id, away_id) tuples.
        For 20 teams: 38 matchdays × 10 matches = 380 unique fixtures.
    """
    teams = list(team_ids)
    n = len(teams)

    if n % 2 == 1:
        teams = teams + [None]
        n += 1

    half = n // 2
    matchdays_first_half: List[List[Tuple[int, int]]] = []

    for round_num in range(n - 1):
        round_matches: List[Tuple[int, int]] = []
        for i in range(half):
            home = teams[i]
            away = teams[n - 1 - i]
            if home is None or away is None:
                continue
            # Alternate home/away by round to balance home games per team.
            if round_num % 2 == 0:
                round_matches.append((home, away))
            else:
                round_matches.append((away, home))
        matchdays_first_half.append(round_matches)

        # Rotate: keep teams[0] fixed, rotate the rest one step clockwise.
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    # Second half mirrors first half with home/away reversed.
    matchdays_second_half: List[List[Tuple[int, int]]] = [
        [(away, home) for (home, away) in matchday]
        for matchday in matchdays_first_half
    ]

    return matchdays_first_half + matchdays_second_half


# ─── League team lookup ───────────────────────────────────────────────────────


def get_league_teams(league_country: str) -> List[Tuple[int, str]]:
    """
    Get all clubs in the specified league.

    The club_id returned is the 1-based index of the club in the CLUBS
    list from app.data.club_budgets — this matches the club_id convention
    used elsewhere in the codebase.

    Args:
        league_country: one of "England", "Spain", "Italy"

    Returns:
        List of (club_id_1based, club_name) tuples.

    Raises:
        ValueError: if league_country is not one of the three supported leagues.
    """
    keyword = _COUNTRY_TO_LEAGUE_KEYWORD.get(league_country)
    if keyword is None:
        supported = ", ".join(sorted(_COUNTRY_TO_LEAGUE_KEYWORD.keys()))
        raise ValueError(
            f"Unsupported league_country '{league_country}'. "
            f"Supported: {supported}"
        )

    teams: List[Tuple[int, str]] = []
    for idx, (name, _scout, _transfer, league_field) in enumerate(CLUBS, start=1):
        if keyword in league_field:
            teams.append((idx, name))
    return teams


# ─── Date helpers ─────────────────────────────────────────────────────────────


def _parse_md(md_str: str) -> Tuple[int, int]:
    """Parse a 'MM-DD' string into (month, day)."""
    month_str, day_str = md_str.split("-")
    return int(month_str), int(day_str)


def _resolve_md_year(month: int, season_start: date, season_end: date) -> int:
    """
    Decide which calendar year a 'MM-DD' belongs to within a season window.
    Uses the season_start year for late-year months (>= start month) and
    season_end year otherwise.
    """
    if month >= season_start.month:
        return season_start.year
    return season_end.year


def _build_skip_ranges(
    season_start: date,
    season_end: date,
    league_config: dict,
) -> List[Tuple[date, date]]:
    """Build a list of (start, end) date ranges to skip when assigning matchdays."""
    skip: List[Tuple[date, date]] = []

    # FIFA international windows
    for window in FIFA_INTERNATIONAL_WINDOWS:
        start_month, start_day = _parse_md(window["start"])
        end_month, end_day = _parse_md(window["end"])
        start_year = _resolve_md_year(start_month, season_start, season_end)
        end_year = _resolve_md_year(end_month, season_start, season_end)
        try:
            w_start = date(start_year, start_month, start_day)
            w_end = date(end_year, end_month, end_day)
        except ValueError:
            continue
        if w_end < w_start:
            # Window crosses year boundary; bump end year forward.
            w_end = date(end_year + 1, end_month, end_day)
        skip.append((w_start, w_end))

    # Winter break
    if league_config.get("has_winter_break"):
        wb_start_str = league_config.get("winter_break_start")
        wb_end_str = league_config.get("winter_break_end")
        if wb_start_str and wb_end_str:
            wb_start_month, wb_start_day = _parse_md(wb_start_str)
            wb_end_month, wb_end_day = _parse_md(wb_end_str)
            wb_start_year = _resolve_md_year(wb_start_month, season_start, season_end)
            wb_end_year = _resolve_md_year(wb_end_month, season_start, season_end)
            try:
                wb_start = date(wb_start_year, wb_start_month, wb_start_day)
                wb_end = date(wb_end_year, wb_end_month, wb_end_day)
                if wb_end < wb_start:
                    wb_end = date(wb_end_year + 1, wb_end_month, wb_end_day)
                skip.append((wb_start, wb_end))
            except ValueError:
                pass

    return skip


def _is_skipped(d: date, skip_ranges: List[Tuple[date, date]]) -> bool:
    return any(start <= d <= end for start, end in skip_ranges)


def _first_saturday_on_or_after(d: date) -> date:
    """Return the first Saturday on or after d (Saturday = weekday 5)."""
    delta = (5 - d.weekday()) % 7
    return d + timedelta(days=delta)


def _pick_kick_off_time(rng: random.Random) -> str:
    """Return default 15:00, or a random TV slot ~30% of the time."""
    if rng.random() < _TV_SLOT_PROBABILITY:
        return rng.choice(_TV_SLOTS)
    return "15:00"


# ─── Assign fixtures to dates ─────────────────────────────────────────────────


def assign_fixtures_to_dates(
    matchdays: List[List[Tuple[int, int]]],
    season_start: date,
    season_end: date,
    league_config: dict,
    rng: Optional[random.Random] = None,
) -> List[dict]:
    """
    Distribute round-robin matchdays across Saturdays in the season window.

    - Iterates Saturdays from season_start through season_end.
    - Skips any Saturday inside an international break or winter break.
    - One matchday per available Saturday, in order.
    - Each match dict contains:
        event_date, home_club_id, away_club_id, matchday_number,
        description, kick_off_time
    - kick_off_time defaults to "15:00"; ~30% of matches get a TV slot
      drawn from {"12:30", "17:30", "20:00", "21:00"}.

    Args:
        matchdays: output of generate_round_robin
        season_start: inclusive season start date
        season_end: inclusive season end date
        league_config: league configuration dict (from league_configs)
        rng: optional random.Random for deterministic output

    Returns:
        Flat list of match event dicts in chronological order.
    """
    if rng is None:
        rng = random.Random()

    skip_ranges = _build_skip_ranges(season_start, season_end, league_config)

    # Collect all available Saturdays.
    available_saturdays: List[date] = []
    cursor = _first_saturday_on_or_after(season_start)
    while cursor <= season_end:
        if not _is_skipped(cursor, skip_ranges):
            available_saturdays.append(cursor)
        cursor += timedelta(days=7)

    league_name = league_config.get("league_name", "League")

    matches: List[dict] = []
    for matchday_idx, matchday in enumerate(matchdays):
        if matchday_idx >= len(available_saturdays):
            # Not enough Saturdays — silently truncate. Callers expecting a full
            # 38-matchday schedule should ensure their season window is wide
            # enough relative to the number of skip ranges.
            break

        match_date = available_saturdays[matchday_idx]
        matchday_number = matchday_idx + 1

        for home_id, away_id in matchday:
            kick_off_time = _pick_kick_off_time(rng)
            matches.append({
                "event_date": match_date,
                "home_club_id": home_id,
                "away_club_id": away_id,
                "matchday_number": matchday_number,
                "description": f"{league_name} Matchday {matchday_number}",
                "kick_off_time": kick_off_time,
            })

    return matches


# ─── Top-level entry point ────────────────────────────────────────────────────


def generate_league_fixtures(
    league_country: str,
    year: int,
    rng: Optional[random.Random] = None,
) -> List[dict]:
    """
    Generate a full season's worth of league fixtures for the given country.

    Combines:
      1. get_league_teams — pull clubs from CLUBS for the requested league
      2. generate_round_robin — circle-method schedule (home & away)
      3. assign_fixtures_to_dates — place matchdays on Saturdays,
         skipping international breaks and winter break

    Args:
        league_country: "England", "Spain", or "Italy"
        year: season start year (e.g. 2026 for the 2026/27 season)
        rng: optional random.Random for deterministic kick-off time selection

    Returns:
        List of match event dicts ready to insert into calendar_events:
            {event_date, home_club_id, away_club_id,
             matchday_number, description, kick_off_time}

    Raises:
        ValueError: if league_country is unsupported or league config missing.
    """
    teams = get_league_teams(league_country)
    if len(teams) < 2:
        raise ValueError(
            f"Not enough clubs found for league_country '{league_country}' "
            f"(found {len(teams)})."
        )

    league_config = get_league_config(league_country)
    if league_config is None:
        raise ValueError(
            f"No league config found for country '{league_country}'."
        )

    # Build round-robin from the 1-based club ids.
    team_ids = [club_id for club_id, _name in teams]
    matchdays = generate_round_robin(team_ids)

    # Compute season window from league config.
    start_month, start_day = _parse_md(league_config["season_start_date"])
    end_month, end_day = _parse_md(league_config["season_end_date"])
    season_start = date(year, start_month, start_day)
    # Season end is in the following calendar year if it falls before season start month.
    end_year = year + 1 if end_month < start_month else year
    season_end = date(end_year, end_month, end_day)

    return assign_fixtures_to_dates(
        matchdays=matchdays,
        season_start=season_start,
        season_end=season_end,
        league_config=league_config,
        rng=rng,
    )
