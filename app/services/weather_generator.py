"""
Weather Generator Service for Club Calendar & Schedule.

Generates realistic weather conditions for match days based on city climate
profiles and calendar month. Used by CalendarEngine to populate weather_data
on match events.
"""

import json
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple


@dataclass
class WeatherData:
    """Weather conditions for a match day."""
    precipitation: str       # "clear", "rain", "snow", "overcast", "fog"
    temperature_celsius: int
    pitch_condition: str     # "dry", "wet", "muddy", "frozen", "artificial"


@dataclass
class CityClimate:
    """Climate profile for a city used in weather generation."""
    avg_temp_by_month: Dict[int, Tuple[int, int]]  # month -> (min, max)
    rain_probability_by_month: Dict[int, float]     # month -> 0.0-1.0
    snow_months: List[int]                          # months where snow is possible
    is_cold_climate: bool


# Climate profiles for major European football cities
CLIMATE_PROFILES: Dict[str, CityClimate] = {
    "london": CityClimate(
        avg_temp_by_month={
            1: (2, 8), 2: (2, 9), 3: (4, 12), 4: (5, 15),
            5: (8, 18), 6: (11, 22), 7: (13, 22), 8: (13, 22),
            9: (10, 19), 10: (8, 15), 11: (5, 11), 12: (3, 8),
        },
        rain_probability_by_month={
            1: 0.4, 2: 0.35, 3: 0.35, 4: 0.35,
            5: 0.3, 6: 0.3, 7: 0.3, 8: 0.3,
            9: 0.35, 10: 0.4, 11: 0.45, 12: 0.5,
        },
        snow_months=[],
        is_cold_climate=False,
    ),
    "manchester": CityClimate(
        avg_temp_by_month={
            1: (1, 7), 2: (1, 7), 3: (3, 10), 4: (4, 13),
            5: (7, 16), 6: (10, 19), 7: (12, 20), 8: (12, 20),
            9: (9, 17), 10: (7, 13), 11: (4, 9), 12: (2, 7),
        },
        rain_probability_by_month={
            1: 0.55, 2: 0.5, 3: 0.5, 4: 0.45,
            5: 0.4, 6: 0.45, 7: 0.5, 8: 0.5,
            9: 0.5, 10: 0.55, 11: 0.6, 12: 0.6,
        },
        snow_months=[12, 1, 2],
        is_cold_climate=True,
    ),
    "munich": CityClimate(
        avg_temp_by_month={
            1: (-4, 3), 2: (-3, 5), 3: (0, 10), 4: (3, 14),
            5: (7, 19), 6: (10, 22), 7: (12, 23), 8: (12, 23),
            9: (8, 19), 10: (4, 13), 11: (0, 7), 12: (-2, 4),
        },
        rain_probability_by_month={
            1: 0.35, 2: 0.3, 3: 0.3, 4: 0.35,
            5: 0.4, 6: 0.45, 7: 0.45, 8: 0.4,
            9: 0.35, 10: 0.3, 11: 0.35, 12: 0.35,
        },
        snow_months=[11, 12, 1, 2, 3],
        is_cold_climate=True,
    ),
    "madrid": CityClimate(
        avg_temp_by_month={
            1: (2, 10), 2: (3, 12), 3: (5, 16), 4: (7, 18),
            5: (10, 23), 6: (15, 30), 7: (18, 33), 8: (18, 33),
            9: (14, 28), 10: (9, 20), 11: (5, 14), 12: (3, 10),
        },
        rain_probability_by_month={
            1: 0.2, 2: 0.2, 3: 0.2, 4: 0.25,
            5: 0.2, 6: 0.1, 7: 0.1, 8: 0.1,
            9: 0.15, 10: 0.25, 11: 0.25, 12: 0.3,
        },
        snow_months=[],
        is_cold_climate=False,
    ),
    "barcelona": CityClimate(
        avg_temp_by_month={
            1: (6, 13), 2: (6, 14), 3: (8, 16), 4: (10, 18),
            5: (13, 21), 6: (17, 25), 7: (20, 28), 8: (20, 28),
            9: (17, 25), 10: (13, 21), 11: (9, 16), 12: (7, 13),
        },
        rain_probability_by_month={
            1: 0.2, 2: 0.15, 3: 0.2, 4: 0.25,
            5: 0.2, 6: 0.15, 7: 0.1, 8: 0.15,
            9: 0.25, 10: 0.3, 11: 0.25, 12: 0.2,
        },
        snow_months=[],
        is_cold_climate=False,
    ),
    "milan": CityClimate(
        avg_temp_by_month={
            1: (-1, 6), 2: (0, 9), 3: (4, 14), 4: (7, 18),
            5: (12, 23), 6: (15, 27), 7: (18, 28), 8: (17, 28),
            9: (13, 24), 10: (8, 17), 11: (3, 11), 12: (0, 6),
        },
        rain_probability_by_month={
            1: 0.3, 2: 0.3, 3: 0.35, 4: 0.4,
            5: 0.4, 6: 0.35, 7: 0.3, 8: 0.35,
            9: 0.35, 10: 0.4, 11: 0.4, 12: 0.3,
        },
        snow_months=[12, 1, 2],
        is_cold_climate=True,
    ),
    "paris": CityClimate(
        avg_temp_by_month={
            1: (2, 7), 2: (2, 8), 3: (4, 12), 4: (6, 16),
            5: (9, 20), 6: (12, 23), 7: (14, 25), 8: (14, 25),
            9: (11, 21), 10: (8, 16), 11: (5, 10), 12: (3, 7),
        },
        rain_probability_by_month={
            1: 0.4, 2: 0.35, 3: 0.35, 4: 0.35,
            5: 0.35, 6: 0.3, 7: 0.3, 8: 0.3,
            9: 0.3, 10: 0.35, 11: 0.4, 12: 0.4,
        },
        snow_months=[12, 1, 2],
        is_cold_climate=True,
    ),
    "amsterdam": CityClimate(
        avg_temp_by_month={
            1: (0, 5), 2: (0, 6), 3: (2, 10), 4: (4, 13),
            5: (8, 17), 6: (10, 19), 7: (12, 21), 8: (12, 21),
            9: (10, 18), 10: (7, 14), 11: (4, 9), 12: (2, 6),
        },
        rain_probability_by_month={
            1: 0.55, 2: 0.5, 3: 0.5, 4: 0.45,
            5: 0.4, 6: 0.45, 7: 0.5, 8: 0.5,
            9: 0.5, 10: 0.55, 11: 0.6, 12: 0.6,
        },
        snow_months=[12, 1, 2],
        is_cold_climate=True,
    ),
    "lisbon": CityClimate(
        avg_temp_by_month={
            1: (8, 15), 2: (9, 16), 3: (10, 18), 4: (11, 20),
            5: (13, 22), 6: (16, 26), 7: (18, 28), 8: (18, 28),
            9: (16, 26), 10: (14, 22), 11: (10, 18), 12: (8, 15),
        },
        rain_probability_by_month={
            1: 0.3, 2: 0.25, 3: 0.2, 4: 0.2,
            5: 0.15, 6: 0.1, 7: 0.05, 8: 0.05,
            9: 0.1, 10: 0.2, 11: 0.25, 12: 0.3,
        },
        snow_months=[],
        is_cold_climate=False,
    ),
    "istanbul": CityClimate(
        avg_temp_by_month={
            1: (3, 9), 2: (3, 9), 3: (5, 12), 4: (8, 17),
            5: (12, 21), 6: (16, 26), 7: (19, 27), 8: (19, 27),
            9: (16, 24), 10: (12, 19), 11: (8, 14), 12: (5, 10),
        },
        rain_probability_by_month={
            1: 0.45, 2: 0.4, 3: 0.35, 4: 0.3,
            5: 0.25, 6: 0.2, 7: 0.15, 8: 0.15,
            9: 0.2, 10: 0.3, 11: 0.35, 12: 0.45,
        },
        snow_months=[1, 2],
        is_cold_climate=True,
    ),
    "glasgow": CityClimate(
        avg_temp_by_month={
            1: (1, 6), 2: (1, 7), 3: (2, 9), 4: (4, 12),
            5: (6, 15), 6: (9, 17), 7: (11, 18), 8: (11, 18),
            9: (9, 15), 10: (6, 12), 11: (3, 8), 12: (1, 6),
        },
        rain_probability_by_month={
            1: 0.65, 2: 0.6, 3: 0.55, 4: 0.5,
            5: 0.5, 6: 0.5, 7: 0.55, 8: 0.55,
            9: 0.6, 10: 0.65, 11: 0.7, 12: 0.7,
        },
        snow_months=[11, 12, 1, 2, 3],
        is_cold_climate=True,
    ),
    "brussels": CityClimate(
        avg_temp_by_month={
            1: (0, 6), 2: (0, 7), 3: (2, 10), 4: (4, 14),
            5: (8, 18), 6: (10, 20), 7: (12, 22), 8: (12, 22),
            9: (10, 19), 10: (7, 14), 11: (3, 9), 12: (1, 6),
        },
        rain_probability_by_month={
            1: 0.5, 2: 0.45, 3: 0.45, 4: 0.4,
            5: 0.4, 6: 0.45, 7: 0.5, 8: 0.45,
            9: 0.45, 10: 0.5, 11: 0.55, 12: 0.55,
        },
        snow_months=[12, 1, 2],
        is_cold_climate=True,
    ),
    "dortmund": CityClimate(
        avg_temp_by_month={
            1: (-1, 4), 2: (-1, 6), 3: (1, 10), 4: (4, 15),
            5: (8, 19), 6: (11, 22), 7: (13, 23), 8: (12, 23),
            9: (9, 19), 10: (6, 14), 11: (2, 8), 12: (0, 5),
        },
        rain_probability_by_month={
            1: 0.4, 2: 0.35, 3: 0.35, 4: 0.35,
            5: 0.4, 6: 0.4, 7: 0.4, 8: 0.4,
            9: 0.35, 10: 0.35, 11: 0.4, 12: 0.4,
        },
        snow_months=[11, 12, 1, 2, 3],
        is_cold_climate=True,
    ),
    "rome": CityClimate(
        avg_temp_by_month={
            1: (3, 12), 2: (4, 13), 3: (5, 16), 4: (8, 19),
            5: (11, 24), 6: (15, 28), 7: (18, 30), 8: (18, 30),
            9: (15, 27), 10: (11, 22), 11: (7, 16), 12: (4, 12),
        },
        rain_probability_by_month={
            1: 0.25, 2: 0.25, 3: 0.2, 4: 0.2,
            5: 0.15, 6: 0.1, 7: 0.05, 8: 0.1,
            9: 0.2, 10: 0.25, 11: 0.3, 12: 0.25,
        },
        snow_months=[],
        is_cold_climate=False,
    ),
    "marseille": CityClimate(
        avg_temp_by_month={
            1: (3, 11), 2: (4, 12), 3: (6, 15), 4: (8, 18),
            5: (12, 22), 6: (15, 26), 7: (18, 28), 8: (18, 28),
            9: (15, 25), 10: (11, 20), 11: (7, 15), 12: (4, 12),
        },
        rain_probability_by_month={
            1: 0.2, 2: 0.2, 3: 0.15, 4: 0.2,
            5: 0.15, 6: 0.1, 7: 0.05, 8: 0.1,
            9: 0.2, 10: 0.25, 11: 0.25, 12: 0.2,
        },
        snow_months=[],
        is_cold_climate=False,
    ),
}

# Default temperate climate profile for unknown cities
_DEFAULT_CLIMATE = CityClimate(
    avg_temp_by_month={
        1: (1, 7), 2: (1, 8), 3: (3, 11), 4: (5, 15),
        5: (9, 19), 6: (12, 22), 7: (14, 24), 8: (14, 24),
        9: (11, 20), 10: (7, 15), 11: (4, 10), 12: (2, 7),
    },
    rain_probability_by_month={
        1: 0.4, 2: 0.35, 3: 0.35, 4: 0.35,
        5: 0.35, 6: 0.3, 7: 0.3, 8: 0.3,
        9: 0.35, 10: 0.4, 11: 0.4, 12: 0.4,
    },
    snow_months=[12, 1, 2],
    is_cold_climate=True,
)


class WeatherGenerator:
    """Generates weather conditions based on city climate and calendar month."""

    def generate_weather(
        self,
        city: str,
        country: str,
        month: int,
        stadium_type: str = "natural",
    ) -> WeatherData:
        """
        Generate weather for a match day.

        Uses city climate profile + randomization.
        Snow only for cold climates in snow_months when temp < 2.
        Rain probability proportional to historical data.

        Args:
            city: City name where the match is played.
            country: Country of the city (used for fallback profile).
            month: Calendar month (1-12).
            stadium_type: "natural" or "artificial".

        Returns:
            WeatherData with precipitation, temperature, and pitch condition.
        """
        climate = self.get_climate_profile(city, country)

        # Generate temperature: random int between min and max for that month
        temp_min, temp_max = climate.avg_temp_by_month[month]
        temperature = random.randint(temp_min, temp_max)

        # Generate precipitation
        rain_prob = climate.rain_probability_by_month[month]
        precipitation = self._generate_precipitation(
            climate, month, temperature, rain_prob
        )

        # Generate pitch condition
        pitch_condition = self._determine_pitch_condition(
            stadium_type, precipitation, temperature, rain_prob
        )

        return WeatherData(
            precipitation=precipitation,
            temperature_celsius=temperature,
            pitch_condition=pitch_condition,
        )

    def get_climate_profile(self, city: str, country: str) -> CityClimate:
        """
        Look up climate profile for a city (case-insensitive).

        If the city is not found in CLIMATE_PROFILES, returns a default
        temperate climate profile.

        Args:
            city: City name to look up.
            country: Country name (reserved for future country-level defaults).

        Returns:
            CityClimate profile for the city.
        """
        city_lower = city.lower().strip()
        if city_lower in CLIMATE_PROFILES:
            return CLIMATE_PROFILES[city_lower]
        return _DEFAULT_CLIMATE

    def _generate_precipitation(
        self,
        climate: CityClimate,
        month: int,
        temperature: int,
        rain_prob: float,
    ) -> str:
        """Determine precipitation type based on climate conditions."""
        # Snow check: cold climate, snow month, and temperature below 2°C
        if climate.is_cold_climate and month in climate.snow_months and temperature < 2:
            return "snow"

        # Rain check based on probability
        if random.random() < rain_prob:
            return "rain"

        # Overcast check (20% of remaining cases)
        if random.random() < 0.2:
            return "overcast"

        # Fog check (5% of remaining cases)
        if random.random() < 0.05:
            return "fog"

        return "clear"

    def _determine_pitch_condition(
        self,
        stadium_type: str,
        precipitation: str,
        temperature: int,
        rain_prob: float,
    ) -> str:
        """Determine pitch condition based on weather and stadium type."""
        if stadium_type == "artificial":
            return "artificial"

        if precipitation == "snow" and temperature < 0:
            return "frozen"

        if precipitation == "rain" and rain_prob > 0.5:
            return "muddy"

        if precipitation == "rain":
            return "wet"

        return "dry"


def to_json(weather_data: WeatherData) -> str:
    """
    Serialize WeatherData to a JSON string for database storage.

    Args:
        weather_data: WeatherData instance to serialize.

    Returns:
        JSON string representation of the weather data.
    """
    return json.dumps(asdict(weather_data))
