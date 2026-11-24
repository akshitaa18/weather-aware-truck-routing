"""
Geocoding Service for Weather-Aware Truck Routing.

Resolves address and city queries into geographic coordinates (lat, lon)
using OpenStreetMap Nominatim with Photon fallback. No API key required.
"""

import logging
import requests
from requests.adapters import HTTPAdapter
from typing import Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_GEOCODE_CACHE: Dict[str, Dict[str, Any]] = {}

# Reusable HTTP session with connection pooling
_SESSION = requests.Session()
_ADAPTER = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=1)
_SESSION.mount("https://", _ADAPTER)
_SESSION.mount("http://", _ADAPTER)


def geocode_location(query: str) -> Dict[str, Any]:
    """
    Geocode a location query string to latitude and longitude.
    
    Returns:
    {
        "query": str,
        "name": str,
        "latitude": float,
        "longitude": float
    }
    Raises ValueError if location cannot be found.
    """
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Location query cannot be empty.")

    cache_k = clean_query.lower()
    if cache_k in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_k]

    # Try OpenStreetMap Nominatim first
    headers = {
        "User-Agent": "WeatherAwareTruckRouting/1.0 (contact: takshita241@gmail.com)",
        "Accept": "application/json",
    }
    params = {
        "q": clean_query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }

    try:
        resp = _SESSION.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers=headers,
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                first = data[0]
                result = {
                    "query": clean_query,
                    "name": first.get("display_name", clean_query),
                    "latitude": round(float(first["lat"]), 6),
                    "longitude": round(float(first["lon"]), 6),
                }
                _GEOCODE_CACHE[cache_k] = result
                return result
    except Exception as e:
        logger.warning("Nominatim geocode failed for '%s': %s", clean_query, e)

    # Fallback: Photon API (Komoot OpenStreetMap search)
    try:
        photon_url = f"https://photon.komoot.io/api/?q={requests.utils.quote(clean_query)}&limit=1"
        resp = _SESSION.get(photon_url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])
            if features:
                geom = features[0].get("geometry", {})
                props = features[0].get("properties", {})
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    name_parts = [
                        props.get("name"),
                        props.get("city"),
                        props.get("state"),
                        props.get("country"),
                    ]
                    display_name = ", ".join([p for p in name_parts if p]) or clean_query
                    result = {
                        "query": clean_query,
                        "name": display_name,
                        "latitude": round(float(coords[1]), 6),
                        "longitude": round(float(coords[0]), 6),
                    }
                    _GEOCODE_CACHE[cache_k] = result
                    return result
    except Exception as e:
        logger.warning("Photon fallback geocode failed for '%s': %s", clean_query, e)

    raise ValueError(f"Unable to geocode location '{clean_query}'. Please check spelling or provide city and state.")


def geocode_locations_concurrent(origin_query: str, dest_query: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Geocode origin and destination locations concurrently when uncached
    to minimize user wait time during route planning.
    """
    cache_orig = origin_query.strip().lower()
    cache_dest = dest_query.strip().lower()

    if cache_orig in _GEOCODE_CACHE and cache_dest in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_orig], _GEOCODE_CACHE[cache_dest]

    with ThreadPoolExecutor(max_workers=2) as executor:
        fut_orig = executor.submit(geocode_location, origin_query)
        fut_dest = executor.submit(geocode_location, dest_query)
        origin_res = fut_orig.result()
        dest_res = fut_dest.result()

    return origin_res, dest_res

