"""
Geocoding Service for Weather-Aware Truck Routing.

Resolves address and city queries into geographic coordinates (lat, lon)
using Photon (Komoot OSM) and OpenStreetMap Nominatim with strict rate limiting.
Configurable via GEOCODING_PROVIDER ('photon' [default] or 'nominatim').
"""

import os
import time
import threading
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

# Nominatim rate-limiting state (max 1 request per second policy)
_NOMINATIM_LOCK = threading.Lock()
_LAST_NOMINATIM_CALL = 0.0


def _query_nominatim(clean_query: str) -> Optional[Dict[str, Any]]:
    """Query OpenStreetMap Nominatim with strict <= 1 req/sec rate limiting."""
    global _LAST_NOMINATIM_CALL

    with _NOMINATIM_LOCK:
        elapsed = time.time() - _LAST_NOMINATIM_CALL
        if elapsed < 1.05:
            time.sleep(1.05 - elapsed)
        _LAST_NOMINATIM_CALL = time.time()

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
                return {
                    "query": clean_query,
                    "name": first.get("display_name", clean_query),
                    "latitude": round(float(first["lat"]), 6),
                    "longitude": round(float(first["lon"]), 6),
                }
        elif resp.status_code in (429, 403):
            logger.warning("Nominatim rate limit or forbidden (HTTP %s) for '%s'. Falling back immediately.", resp.status_code, clean_query)
            return None
    except Exception as e:
        logger.warning("Nominatim geocode failed for '%s': %s", clean_query, e)
    return None


def _query_photon(clean_query: str) -> Optional[Dict[str, Any]]:
    """Query Photon API (Komoot OpenStreetMap search) without strict 1 req/s delay."""
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
                    return {
                        "query": clean_query,
                        "name": display_name,
                        "latitude": round(float(coords[1]), 6),
                        "longitude": round(float(coords[0]), 6),
                    }
        elif resp.status_code in (429, 403):
            logger.warning("Photon rate limit (HTTP %s) for '%s'.", resp.status_code, clean_query)
            return None
    except Exception as e:
        logger.warning("Photon geocode failed for '%s': %s", clean_query, e)
    return None


def geocode_location(query: str) -> Dict[str, Any]:
    """
    Geocode a location query string to latitude and longitude.
    Uses configurable provider preference (GEOCODING_PROVIDER: 'photon' [default] or 'nominatim')
    with automatic graceful fallback between them.
    """
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("Location query cannot be empty.")

    cache_k = clean_query.lower()
    if cache_k in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_k]

    provider_pref = os.getenv("GEOCODING_PROVIDER", "photon").lower()

    if provider_pref == "nominatim":
        result = _query_nominatim(clean_query) or _query_photon(clean_query)
    else:
        # Default: Photon first for high speed and no rate-limit latency, Nominatim as fallback
        result = _query_photon(clean_query) or _query_nominatim(clean_query)

    if result:
        _GEOCODE_CACHE[cache_k] = result
        return result

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
