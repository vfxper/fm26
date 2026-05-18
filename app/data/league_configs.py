"""
Static league configuration data for the 10 supported leagues.
Includes season dates, winter breaks, mandatory fixtures, blackout dates,
custom milestones, and FIFA international windows.
"""

from typing import Optional

from app.data.club_budgets import CLUBS


# FIFA international break windows (MM-DD format)
FIFA_INTERNATIONAL_WINDOWS = [
    {"start": "09-01", "end": "09-10", "name": "September international break"},
    {"start": "10-06", "end": "10-14", "name": "October international break"},
    {"start": "11-10", "end": "11-18", "name": "November international break"},
    {"start": "03-17", "end": "03-25", "name": "March international break"},
]


# League configuration data for 10 leagues
LEAGUE_CONFIGS = [
    {
        "country": "England",
        "league_name": "Premier League",
        "has_winter_break": False,
        "winter_break_start": None,
        "winter_break_end": None,
        "mandatory_fixture_dates": ["12-26", "01-01"],
        "blackout_dates": ["12-25"],
        "custom_milestones": [{"date": "12-26", "name": "Boxing Day fixtures"}],
        "season_start_date": "08-10",
        "season_end_date": "05-19",
        "european_competition": None,
    },
    {
        "country": "Germany",
        "league_name": "Bundesliga",
        "has_winter_break": True,
        "winter_break_start": "01-01",
        "winter_break_end": "01-31",
        "mandatory_fixture_dates": [],
        "blackout_dates": ["12-25"],
        "custom_milestones": [],
        "season_start_date": "08-16",
        "season_end_date": "05-17",
        "european_competition": None,
    },
    {
        "country": "Spain",
        "league_name": "La Liga",
        "has_winter_break": True,
        "winter_break_start": "01-01",
        "winter_break_end": "01-31",
        "mandatory_fixture_dates": [],
        "blackout_dates": ["12-25"],
        "custom_milestones": [],
        "season_start_date": "08-12",
        "season_end_date": "05-25",
        "european_competition": None,
    },
    {
        "country": "Italy",
        "league_name": "Serie A",
        "has_winter_break": False,
        "winter_break_start": None,
        "winter_break_end": None,
        "mandatory_fixture_dates": [],
        "blackout_dates": ["12-25"],
        "custom_milestones": [],
        "season_start_date": "08-18",
        "season_end_date": "05-25",
        "european_competition": None,
    },
    {
        "country": "France",
        "league_name": "Ligue 1",
        "has_winter_break": False,
        "winter_break_start": None,
        "winter_break_end": None,
        "mandatory_fixture_dates": [],
        "blackout_dates": ["12-25"],
        "custom_milestones": [],
        "season_start_date": "08-10",
        "season_end_date": "05-18",
        "european_competition": None,
    },
    {
        "country": "Netherlands",
        "league_name": "Eredivisie",
        "has_winter_break": True,
        "winter_break_start": "12-23",
        "winter_break_end": "01-14",
        "mandatory_fixture_dates": [],
        "blackout_dates": ["12-25"],
        "custom_milestones": [],
        "season_start_date": "08-09",
        "season_end_date": "05-15",
        "european_competition": None,
    },
    {
        "country": "Portugal",
        "league_name": "Primeira Liga",
        "has_winter_break": False,
        "winter_break_start": None,
        "winter_break_end": None,
        "mandatory_fixture_dates": [],
        "blackout_dates": ["12-25"],
        "custom_milestones": [],
        "season_start_date": "08-10",
        "season_end_date": "05-19",
        "european_competition": None,
    },
    {
        "country": "Turkey",
        "league_name": "Süper Lig",
        "has_winter_break": True,
        "winter_break_start": "01-01",
        "winter_break_end": "01-31",
        "mandatory_fixture_dates": [],
        "blackout_dates": ["12-25"],
        "custom_milestones": [],
        "season_start_date": "08-16",
        "season_end_date": "05-25",
        "european_competition": None,
    },
    {
        "country": "Scotland",
        "league_name": "Premiership",
        "has_winter_break": False,
        "winter_break_start": None,
        "winter_break_end": None,
        "mandatory_fixture_dates": ["12-26", "01-02"],
        "blackout_dates": ["12-25"],
        "custom_milestones": [],
        "season_start_date": "08-03",
        "season_end_date": "05-18",
        "european_competition": None,
    },
    {
        "country": "Belgium",
        "league_name": "Pro League",
        "has_winter_break": True,
        "winter_break_start": "12-26",
        "winter_break_end": "01-14",
        "mandatory_fixture_dates": [],
        "blackout_dates": ["12-25"],
        "custom_milestones": [],
        "season_start_date": "07-26",
        "season_end_date": "05-25",
        "european_competition": None,
    },
    {
        "country": "Saudi Arabia",
        "league_name": "Saudi Pro League",
        "has_winter_break": False,
        "winter_break_start": None,
        "winter_break_end": None,
        "mandatory_fixture_dates": [],
        "blackout_dates": [],
        "custom_milestones": [],
        # SPL season runs roughly Aug → May; we keep the same envelope as
        # other leagues so the round-robin slots into the same Saturdays.
        "season_start_date": "08-15",
        "season_end_date": "05-25",
        "european_competition": None,
    },
    {
        "country": "USA",
        "league_name": "MLS",
        "has_winter_break": False,
        "winter_break_start": None,
        "winter_break_end": None,
        "mandatory_fixture_dates": [],
        "blackout_dates": [],
        "custom_milestones": [],
        # MLS realistically runs Feb → Dec, but we map it onto the same
        # Aug → May envelope here so the calendar generator (which is
        # tied to that envelope) still produces a valid schedule.
        # Real-world MLS scheduling can be revisited in a follow-up.
        "season_start_date": "08-10",
        "season_end_date": "05-25",
        "european_competition": None,
    },
]


# Mapping from league name keywords to country for club lookup
_LEAGUE_TO_COUNTRY = {
    "premier league": "England",
    "bundesliga": "Germany",
    "la liga": "Spain",
    "serie a": "Italy",
    "ligue 1": "France",
    "eredivisie": "Netherlands",
    "liga portugal": "Portugal",
    "primeira liga": "Portugal",
    "süper lig": "Turkey",
    "super lig": "Turkey",
    "premiership": "Scotland",
    "pro league": "Belgium",
    "saudi pro league": "Saudi Arabia",
    "mls": "USA",
}


def get_league_config(country: str) -> Optional[dict]:
    """
    Get league configuration by country name.
    Case-insensitive fuzzy match on country name.

    Args:
        country: Country name (e.g. "England", "germany", "SPAIN")

    Returns:
        League config dict or None if not found.
    """
    country_lower = country.strip().lower()
    for config in LEAGUE_CONFIGS:
        if config["country"].lower() == country_lower:
            return config
    # Fuzzy: check if input is a substring of country or vice versa
    for config in LEAGUE_CONFIGS:
        config_country = config["country"].lower()
        if country_lower in config_country or config_country in country_lower:
            return config
    return None


def get_league_config_for_club(club_name: str) -> Optional[dict]:
    """
    Get league configuration for a club by matching against the CLUBS list
    from club_budgets.py.

    Args:
        club_name: Club name (e.g. "Manchester City", "Bayern Munich")

    Returns:
        League config dict or None if club/league not found.
    """
    club_lower = club_name.strip().lower()

    # Find the club's league from CLUBS list
    league_field = None
    for name, _, _, league in CLUBS:
        if name.lower() == club_lower:
            league_field = league
            break

    # Fuzzy match if exact match failed
    if league_field is None:
        for name, _, _, league in CLUBS:
            if club_lower in name.lower() or name.lower() in club_lower:
                league_field = league
                break

    if league_field is None:
        return None

    # Extract league name from the field (format: "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League" or "🇩🇪 Bundesliga")
    # The league field has a flag emoji followed by a space and the league name
    league_name_part = league_field.split(" ", 1)[-1] if " " in league_field else league_field
    league_name_lower = league_name_part.strip().lower()

    # Look up country from league name
    country = _LEAGUE_TO_COUNTRY.get(league_name_lower)
    if country:
        return get_league_config(country)

    # Fallback: try matching league_name in configs directly
    for config in LEAGUE_CONFIGS:
        if config["league_name"].lower() == league_name_lower:
            return config

    return None
