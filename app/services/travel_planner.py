"""Travel Planner service for away match logistics.

Automatically plans transport mode, departure/arrival times, and return
schedules for away fixtures based on distance between cities.
"""

import json
import math
from dataclasses import dataclass, asdict


@dataclass
class TravelPlan:
    """Represents a complete travel plan for an away match."""

    transport_mode: str  # "bus" or "plane"
    departure_datetime: str  # "HH:MM" format (day context inferred)
    arrival_datetime: str  # "HH:MM" format
    return_datetime: str  # "HH:MM" format
    destination_city: str
    distance_km: int


# Approximate distances (km) between major football cities.
# Keys are tuples of (city_a, city_b) in lowercase.
CITY_DISTANCES: dict[tuple[str, str], int] = {
    # England
    ("london", "manchester"): 330,
    ("london", "liverpool"): 350,
    ("london", "birmingham"): 190,
    ("london", "leeds"): 310,
    ("london", "newcastle"): 450,
    ("manchester", "liverpool"): 55,
    ("manchester", "leeds"): 70,
    ("manchester", "newcastle"): 230,
    ("liverpool", "leeds"): 120,
    # Spain
    ("madrid", "barcelona"): 620,
    ("madrid", "sevilla"): 530,
    ("madrid", "valencia"): 360,
    ("barcelona", "valencia"): 350,
    # Germany
    ("munich", "dortmund"): 600,
    ("munich", "berlin"): 585,
    ("munich", "frankfurt"): 390,
    ("berlin", "dortmund"): 490,
    ("berlin", "frankfurt"): 550,
    ("dortmund", "frankfurt"): 260,
    # Italy
    ("milan", "rome"): 570,
    ("milan", "turin"): 145,
    ("milan", "naples"): 770,
    ("rome", "naples"): 225,
    ("turin", "rome"): 670,
    # France
    ("paris", "lyon"): 465,
    ("paris", "marseille"): 775,
    ("paris", "lille"): 225,
    ("lyon", "marseille"): 315,
    # Netherlands
    ("amsterdam", "rotterdam"): 80,
    ("amsterdam", "eindhoven"): 125,
    ("rotterdam", "eindhoven"): 110,
    # Portugal
    ("lisbon", "porto"): 315,
    # Turkey
    ("istanbul", "ankara"): 450,
    # Scotland
    ("glasgow", "edinburgh"): 75,
    # Belgium
    ("brussels", "bruges"): 100,
    ("brussels", "liege"): 100,
}


class TravelPlanner:
    """Plans travel for away matches based on distance and kick-off time."""

    BUS_THRESHOLD_KM: int = 300
    BUS_SPEED_KMH: int = 80
    PLANE_SPEED_KMH: int = 800
    ARRIVAL_BUFFER_HOURS: int = 3
    POST_MATCH_HOURS: int = 2
    MATCH_DURATION_HOURS: int = 2

    def plan_travel(
        self,
        home_city: str,
        away_city: str,
        kick_off_time: str,
        home_country: str,
        away_country: str,
    ) -> TravelPlan:
        """
        Calculate transport mode and full travel schedule for an away match.

        Args:
            home_city: The club's home city.
            away_city: The destination city for the away match.
            kick_off_time: Match kick-off time as "HH:MM" string.
            home_country: Country of the home city.
            away_country: Country of the away city.

        Returns:
            TravelPlan with mode, departure, arrival, return times, and distance.
        """
        distance = self.estimate_distance(home_city, away_city, home_country, away_country)

        # Select transport mode
        if distance < self.BUS_THRESHOLD_KM:
            transport_mode = "bus"
            speed = self.BUS_SPEED_KMH
        else:
            transport_mode = "plane"
            speed = self.PLANE_SPEED_KMH

        # Calculate travel time in hours
        travel_time_hours = distance / speed

        # Parse kick-off time
        kick_off_hours, kick_off_minutes = self._parse_time(kick_off_time)
        kick_off_total_minutes = kick_off_hours * 60 + kick_off_minutes

        # Arrival = kick_off - 3h buffer
        arrival_total_minutes = kick_off_total_minutes - (self.ARRIVAL_BUFFER_HOURS * 60)

        # Departure = arrival - travel_time
        travel_time_minutes = int(math.ceil(travel_time_hours * 60))
        departure_total_minutes = arrival_total_minutes - travel_time_minutes

        # Return = kick_off + match_duration + post_match
        return_total_minutes = kick_off_total_minutes + (
            (self.MATCH_DURATION_HOURS + self.POST_MATCH_HOURS) * 60
        )

        # Normalize times (handle day wrapping)
        departure_time = self._minutes_to_time(departure_total_minutes)
        arrival_time = self._minutes_to_time(arrival_total_minutes)
        return_time = self._minutes_to_time(return_total_minutes)

        return TravelPlan(
            transport_mode=transport_mode,
            departure_datetime=departure_time,
            arrival_datetime=arrival_time,
            return_datetime=return_time,
            destination_city=away_city,
            distance_km=distance,
        )

    def estimate_distance(
        self,
        city_a: str,
        city_b: str,
        country_a: str,
        country_b: str,
    ) -> int:
        """
        Estimate distance in km between two cities.

        Uses the CITY_DISTANCES lookup table first (case-insensitive).
        Falls back to defaults: 250km for domestic, 1500km for international.

        Args:
            city_a: First city name.
            city_b: Second city name.
            country_a: Country of city_a.
            country_b: Country of city_b.

        Returns:
            Estimated distance in kilometers.
        """
        key_a = city_a.lower()
        key_b = city_b.lower()

        # Check both orderings in the lookup table
        if (key_a, key_b) in CITY_DISTANCES:
            return CITY_DISTANCES[(key_a, key_b)]
        if (key_b, key_a) in CITY_DISTANCES:
            return CITY_DISTANCES[(key_b, key_a)]

        # Fallback based on whether same country
        if country_a.lower() == country_b.lower():
            return 250  # domestic default
        else:
            return 1500  # international default

    def validate_override(
        self,
        new_departure: str,
        kick_off_time: str,
        distance_km: int,
        transport_mode: str,
    ) -> bool:
        """
        Validate that a manual travel override still allows arrival before kick-off.

        Args:
            new_departure: Proposed new departure time as "HH:MM".
            kick_off_time: Match kick-off time as "HH:MM".
            distance_km: Distance to travel in km.
            transport_mode: "bus" or "plane".

        Returns:
            True if the override is valid (arrival before kick-off), False otherwise.
        """
        speed = self.BUS_SPEED_KMH if transport_mode == "bus" else self.PLANE_SPEED_KMH
        travel_time_minutes = int(math.ceil((distance_km / speed) * 60))

        dep_hours, dep_minutes = self._parse_time(new_departure)
        ko_hours, ko_minutes = self._parse_time(kick_off_time)

        departure_total = dep_hours * 60 + dep_minutes
        kick_off_total = ko_hours * 60 + ko_minutes

        # Calculate estimated arrival
        arrival_total = departure_total + travel_time_minutes

        # Handle day wrapping: if departure is late evening and kick-off is next day
        # We assume if departure > kick_off in minutes, it's the day before
        if departure_total > kick_off_total:
            # Departure is on the previous day
            arrival_total = departure_total + travel_time_minutes
            # Arrival wraps into next day: subtract 24h worth of minutes for comparison
            arrival_in_next_day = arrival_total - (24 * 60)
            return arrival_in_next_day <= kick_off_total
        else:
            # Same day travel
            return arrival_total <= kick_off_total

    @staticmethod
    def to_json(travel_plan: TravelPlan) -> str:
        """
        Serialize a TravelPlan to JSON string for database storage.

        Args:
            travel_plan: The TravelPlan to serialize.

        Returns:
            JSON string representation.
        """
        return json.dumps(asdict(travel_plan), ensure_ascii=False)

    @staticmethod
    def _parse_time(time_str: str) -> tuple[int, int]:
        """Parse a 'HH:MM' time string into (hours, minutes)."""
        parts = time_str.split(":")
        return int(parts[0]), int(parts[1])

    @staticmethod
    def _minutes_to_time(total_minutes: int) -> str:
        """
        Convert total minutes to 'HH:MM' format.

        Handles negative values (previous day) and values >= 1440 (next day)
        by wrapping within 0-1439 range.
        """
        # Normalize to 0-1439 range (24 hours)
        normalized = total_minutes % (24 * 60)
        hours = normalized // 60
        minutes = normalized % 60
        return f"{hours:02d}:{minutes:02d}"
