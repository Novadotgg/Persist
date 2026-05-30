import httpx
import structlog
from typing import Dict, Any, List, Optional
from app.integrations.circuit_breaker import CircuitBreaker

logger = structlog.get_logger()
weather_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

OWM_API_BASE = "https://api.openweathermap.org/data/2.5"
OWM_API_V3_BASE = "https://api.openweathermap.org/data/3.0"
OWM_GEO_BASE = "http://api.openweathermap.org/geo/1.0"


class WeatherConnector:
    """
    HTTP connector for the OpenWeatherMap API.
    Supports current weather, 5-day forecast, and coordinate-based lookups.
    Uses an API key for authentication.
    Uses a Circuit Breaker to isolate connection failures.
    """

    @staticmethod
    @weather_circuit_breaker
    async def get_current_weather(
        api_key: str,
        city: str,
        units: str = "metric",
    ) -> Dict[str, Any]:
        """
        Retrieves current weather conditions for a given city name.
        units: "metric" (Celsius), "imperial" (Fahrenheit), "standard" (Kelvin)
        """
        logger.info("Fetching current weather", city=city, units=units)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OWM_API_BASE}/weather",
                params={"q": city, "appid": api_key, "units": units},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch current weather",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @weather_circuit_breaker
    async def get_weather_by_coords(
        api_key: str,
        lat: float,
        lon: float,
        units: str = "metric",
    ) -> Dict[str, Any]:
        """
        Retrieves current weather for geographic coordinates.
        """
        logger.info("Fetching weather by coordinates", lat=lat, lon=lon)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OWM_API_BASE}/weather",
                params={"lat": lat, "lon": lon, "appid": api_key, "units": units},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch weather by coords",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @weather_circuit_breaker
    async def get_forecast(
        api_key: str,
        city: str,
        days: int = 5,
        units: str = "metric",
    ) -> Dict[str, Any]:
        """
        Returns a 5-day weather forecast (3-hour interval entries) for a city.
        The `days` parameter limits the number of 3-hour data points returned (max 40 = 5 days).
        """
        logger.info("Fetching weather forecast", city=city, days=days)
        cnt = min(days * 8, 40)  # 8 x 3-hour blocks per day, max 40 entries
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OWM_API_BASE}/forecast",
                params={"q": city, "appid": api_key, "units": units, "cnt": cnt},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch weather forecast",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    @weather_circuit_breaker
    async def get_air_quality(
        api_key: str,
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        """
        Returns the Air Quality Index (AQI) and pollutant concentrations for coordinates.
        """
        logger.info("Fetching air quality", lat=lat, lon=lon)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{OWM_API_BASE}/air_pollution",
                params={"lat": lat, "lon": lon, "appid": api_key},
            )
            if response.status_code != 200:
                logger.error(
                    "Failed to fetch air quality",
                    status_code=response.status_code,
                    body=response.text[:200],
                )
                response.raise_for_status()
            return response.json()

    @staticmethod
    def parse_current_weather(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper to extract key fields from a current weather API response.
        Returns a simplified dict for easy display.
        """
        weather = data.get("weather", [{}])[0]
        main = data.get("main", {})
        wind = data.get("wind", {})
        return {
            "city": data.get("name", "Unknown"),
            "country": data.get("sys", {}).get("country", ""),
            "condition": weather.get("main", ""),
            "description": weather.get("description", ""),
            "temperature": main.get("temp"),
            "feels_like": main.get("feels_like"),
            "humidity": main.get("humidity"),
            "pressure": main.get("pressure"),
            "wind_speed": wind.get("speed"),
            "wind_direction": wind.get("deg"),
            "visibility": data.get("visibility"),
        }
