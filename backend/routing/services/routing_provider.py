"""
Routing Provider Abstraction and Implementations.

Supports:
1. OpenRouteService (HGV truck profile, 3 alternatives)
2. OSRM with Smart Corridor Waypoint Routing (guaranteeing distinct genuine driving routes)
3. Clearly labeled Fallback Corridor Provider for offline demonstration purposes only
"""

import os
import math
import logging
import requests
from requests.adapters import HTTPAdapter
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

from .checkpoint_generator import haversine_distance_miles

logger = logging.getLogger(__name__)

METERS_TO_MILES = 0.000621371

# Reusable HTTP session with connection pooling for routing requests
_ROUTING_SESSION = requests.Session()
_ROUTING_ADAPTER = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=1)
_ROUTING_SESSION.mount("https://", _ROUTING_ADAPTER)
_ROUTING_SESSION.mount("http://", _ROUTING_ADAPTER)


def routes_are_substantially_different(r1: Dict[str, Any], r2: Dict[str, Any]) -> bool:
    """
    Check if two routes follow substantially distinct driving corridors.
    Routes are considered distinct if:
    1. Their distance differs by more than 5 miles or 3%, OR
    2. Any intermediate checkpoint / coordinate along the path diverges by > 10 miles.
    """
    d1 = r1.get("distance_miles", 0.0)
    d2 = r2.get("distance_miles", 0.0)
    if abs(d1 - d2) > 5.0 or (max(d1, d2) > 0 and abs(d1 - d2) / max(d1, d2) > 0.03):
        return True

    coords1 = r1.get("coordinates", [])
    coords2 = r2.get("coordinates", [])
    if not coords1 or not coords2:
        return False

    # Check divergence at 25%, 50%, and 75% along the polylines
    for frac in (0.25, 0.50, 0.75):
        idx1 = min(int(len(coords1) * frac), len(coords1) - 1)
        idx2 = min(int(len(coords2) * frac), len(coords2) - 1)
        lat1, lon1 = coords1[idx1]
        lat2, lon2 = coords2[idx2]
        if haversine_distance_miles(lat1, lon1, lat2, lon2) > 10.0:
            return True

    return False


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string like '12h 45m'."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def extract_route_name(steps: List[Dict[str, Any]], default_name: str) -> str:
    """Extract prominent highway or street names from route steps."""
    highways = []
    for step in steps:
        name = step.get("name", "")
        ref = step.get("ref", "")
        identifier = ref or name
        if identifier and ("I-" in identifier or "US-" in identifier or "Hwy" in identifier or "Turnpike" in identifier or "Route" in identifier):
            if identifier not in highways:
                highways.append(identifier)
        elif identifier and len(identifier) > 3 and identifier not in highways:
            highways.append(identifier)

    if highways:
        return f"Via {', '.join(highways[:2])}"
    return default_name


class RoutingProvider:
    """Abstract routing provider."""
    def get_three_routes(
        self,
        origin_coords: Tuple[float, float],
        destination_coords: Tuple[float, float],
        origin_name: str,
        destination_name: str
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class OpenRouteServiceProvider(RoutingProvider):
    """OpenRouteService routing provider using HGV truck profile."""
    BASE_URL = "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTESERVICE_API_KEY")

    def get_three_routes(
        self,
        origin_coords: Tuple[float, float],
        destination_coords: Tuple[float, float],
        origin_name: str,
        destination_name: str
    ) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []

        lat1, lon1 = origin_coords
        lat2, lon2 = destination_coords

        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "coordinates": [[lon1, lat1], [lon2, lat2]],
            "alternative_routes": {
                "target_count": 3,
                "weight_factor": 1.4,
                "share_factor": 0.6
            },
            "instructions": True
        }

        try:
            resp = requests.post(self.BASE_URL, json=body, headers=headers, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                routes = []
                for i, feat in enumerate(features[:3]):
                    geom = feat.get("geometry", {})
                    props = feat.get("properties", {})
                    summary = props.get("summary", {})
                    raw_coords = geom.get("coordinates", [])
                    coords = [[round(c[1], 6), round(c[0], 6)] for c in raw_coords]
                    dist_meters = summary.get("distance", 0.0)
                    duration_secs = summary.get("duration", 0.0)

                    route_name = f"Route {i + 1}"
                    segments = props.get("segments", [])
                    if segments:
                        steps = segments[0].get("steps", [])
                        route_name = extract_route_name(steps, f"Route {i + 1}")

                    routes.append({
                        "id": f"route_{i + 1}",
                        "name": route_name,
                        "distance_miles": round(dist_meters * METERS_TO_MILES, 1),
                        "duration_seconds": round(duration_secs, 1),
                        "duration_formatted": format_duration(duration_secs),
                        "coordinates": coords,
                        "origin_name": origin_name,
                        "destination_name": destination_name,
                        "origin_coords": list(origin_coords),
                        "destination_coords": list(destination_coords),
                        "provider": "OpenRouteService (HGV)",
                        "routing_profile": "driving-hgv",
                        "truck_restrictions_enforced": True,
                        "profile_disclosure": "OpenRouteService HGV — Heavy goods vehicle profile enforcing commercial truck dimensions and restrictions.",
                        "is_simulated": False,
                        "is_verified_road_route": True,
                    })
                return routes
        except Exception as e:
            logger.warning("OpenRouteService query failed: %s", e)
        return []


class OSRMProvider(RoutingProvider):
    """
    OSRM routing provider with Smart Corridor Waypoint Strategy.
    Generates genuine driving routes across real highway networks.
    Discloses that OSRM driving profile does not enforce commercial truck height/weight limits.
    """
    BASE_URL = "https://router.project-osrm.org/route/v1/driving"

    def get_three_routes(
        self,
        origin_coords: Tuple[float, float],
        destination_coords: Tuple[float, float],
        origin_name: str,
        destination_name: str
    ) -> List[Dict[str, Any]]:
        lat1, lon1 = origin_coords
        lat2, lon2 = destination_coords

        routes: List[Dict[str, Any]] = []

        # 1. First query OSRM with alternatives=true
        try:
            url = f"{self.BASE_URL}/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson&alternatives=true&steps=true"
            resp = _ROUTING_SESSION.get(url, timeout=7)
            if resp.status_code == 200:
                data = resp.json()
                raw_routes = data.get("routes", [])
                for i, r in enumerate(raw_routes):
                    dist_meters = r.get("distance", 0.0)
                    dur_secs = r.get("duration", 0.0)
                    raw_coords = r.get("geometry", {}).get("coordinates", [])
                    coords = [[round(c[1], 6), round(c[0], 6)] for c in raw_coords]
                    
                    steps = []
                    for leg in r.get("legs", []):
                        steps.extend(leg.get("steps", []))
                    name = extract_route_name(steps, f"Route {len(routes) + 1}")

                    candidate = {
                        "id": f"route_{len(routes) + 1}",
                        "name": name,
                        "distance_miles": round(dist_meters * METERS_TO_MILES, 1),
                        "duration_seconds": round(dur_secs, 1),
                        "duration_formatted": format_duration(dur_secs),
                        "coordinates": coords,
                        "origin_name": origin_name,
                        "destination_name": destination_name,
                        "origin_coords": list(origin_coords),
                        "destination_coords": list(destination_coords),
                        "provider": "OSRM Routing Engine",
                        "routing_profile": "driving (general)",
                        "truck_restrictions_enforced": False,
                        "profile_disclosure": "OSRM Driving — General road network; commercial truck height/weight restrictions not enforced.",
                        "is_simulated": False,
                        "is_verified_road_route": True,
                    }
                    if not any(not routes_are_substantially_different(candidate, existing) for existing in routes):
                        routes.append(candidate)
        except Exception as e:
            logger.warning("OSRM initial query error: %s", e)

        # If we have fewer than 3 routes, query intermediate corridor waypoints through OSRM concurrently
        if len(routes) < 3:
            needed = 3 - len(routes)
            mid_lat = (lat1 + lat2) / 2.0
            mid_lon = (lon1 + lon2) / 2.0
            
            d_lat = lat2 - lat1
            d_lon = lon2 - lon1
            length = math.sqrt(d_lat * d_lat + d_lon * d_lon) or 1.0
            
            perp_lat = -d_lon / length
            perp_lon = d_lat / length
            
            offset_multipliers = [0.85, -0.85] if needed >= 2 else [0.85]

            def fetch_via_corridor(m: float) -> Optional[Dict[str, Any]]:
                via_lat = round(mid_lat + m * perp_lat, 4)
                via_lon = round(mid_lon + m * perp_lon, 4)
                
                # Geographically correct corridor labeling
                delta_lat = via_lat - mid_lat
                delta_lon = via_lon - mid_lon
                if abs(delta_lat) >= abs(delta_lon):
                    corridor_tag = "Northern Corridor" if delta_lat > 0 else "Southern Corridor"
                else:
                    corridor_tag = "Eastern Corridor" if delta_lon > 0 else "Western Corridor"

                try:
                    via_url = f"{self.BASE_URL}/{lon1},{lat1};{via_lon},{via_lat};{lon2},{lat2}?overview=full&geometries=geojson&steps=true"
                    via_resp = _ROUTING_SESSION.get(via_url, timeout=7)
                    if via_resp.status_code == 200:
                        via_data = via_resp.json()
                        v_routes = via_data.get("routes", [])
                        if v_routes:
                            r = v_routes[0]
                            dist_meters = r.get("distance", 0.0)
                            dur_secs = r.get("duration", 0.0)
                            raw_coords = r.get("geometry", {}).get("coordinates", [])
                            coords = [[round(c[1], 6), round(c[0], 6)] for c in raw_coords]
                            
                            steps = []
                            for leg in r.get("legs", []):
                                steps.extend(leg.get("steps", []))
                            name = extract_route_name(steps, f"{corridor_tag} Route")
                            return {
                                "name": f"{corridor_tag} ({name})",
                                "distance_miles": round(dist_meters * METERS_TO_MILES, 1),
                                "duration_seconds": round(dur_secs, 1),
                                "duration_formatted": format_duration(dur_secs),
                                "coordinates": coords,
                                "origin_name": origin_name,
                                "destination_name": destination_name,
                                "origin_coords": list(origin_coords),
                                "destination_coords": list(destination_coords),
                                "provider": f"OSRM ({corridor_tag})",
                                "routing_profile": "driving (general)",
                                "truck_restrictions_enforced": False,
                                "profile_disclosure": "OSRM Driving — General road network; commercial truck height/weight restrictions not enforced.",
                                "is_simulated": False,
                                "is_verified_road_route": True,
                            }
                except Exception as ex:
                    logger.warning("OSRM waypoint route error: %s", ex)
                return None

            with ThreadPoolExecutor(max_workers=min(len(offset_multipliers), 2)) as executor:
                corridor_results = list(executor.map(fetch_via_corridor, offset_multipliers))

            for res in corridor_results:
                if res and len(routes) < 3:
                    if not any(not routes_are_substantially_different(res, existing) for existing in routes):
                        res["id"] = f"route_{len(routes) + 1}"
                        routes.append(res)

        return routes[:3]


class FallbackCorridorProvider(RoutingProvider):
    """
    Simulated Demonstration Fallback Provider.
    
    IMPORTANT: Generates mathematical curved paths between points rather than actual road routes.
    Explicitly labeled as simulated and NEVER presented as verified highway routes.
    Used ONLY when actual routing services are unreachable or specifically in offline demo mode.
    """
    def get_three_routes(
        self,
        origin_coords: Tuple[float, float],
        destination_coords: Tuple[float, float],
        origin_name: str,
        destination_name: str
    ) -> List[Dict[str, Any]]:
        lat1, lon1 = origin_coords
        lat2, lon2 = destination_coords

        from .checkpoint_generator import haversine_distance_miles
        direct_dist = haversine_distance_miles(lat1, lon1, lat2, lon2)

        corridor_configs = [
            {"id": "route_1", "name": "Primary Corridor", "curve_factor": 0.0, "dist_mult": 1.15, "speed_mph": 58.0},
            {"id": "route_2", "name": "Northern Corridor", "curve_factor": 0.12, "dist_mult": 1.24, "speed_mph": 55.0},
            {"id": "route_3", "name": "Southern Corridor", "curve_factor": -0.12, "dist_mult": 1.28, "speed_mph": 54.0},
        ]

        routes = []
        d_lat = lat2 - lat1
        d_lon = lon2 - lon1
        length = math.sqrt(d_lat * d_lat + d_lon * d_lon) or 1.0
        perp_lat = -d_lon / length
        perp_lon = d_lat / length

        for conf in corridor_configs:
            num_points = max(20, int(direct_dist / 10))
            coords = []
            c_factor = conf["curve_factor"]
            
            for step in range(num_points + 1):
                t = step / float(num_points)
                displacement = math.sin(t * math.pi) * c_factor * length
                jitter = math.sin(t * 8 * math.pi) * 0.005
                pt_lat = lat1 + t * d_lat + (displacement + jitter) * perp_lat
                pt_lon = lon1 + t * d_lon + (displacement + jitter) * perp_lon
                coords.append([round(pt_lat, 6), round(pt_lon, 6)])

            total_dist_miles = round(direct_dist * conf["dist_mult"], 1)
            duration_hours = total_dist_miles / conf["speed_mph"]
            duration_secs = round(duration_hours * 3600.0, 1)

            routes.append({
                "id": conf["id"],
                "name": f"[Simulated] {conf['name']}",
                "distance_miles": total_dist_miles,
                "duration_seconds": duration_secs,
                "duration_formatted": format_duration(duration_secs),
                "coordinates": coords,
                "origin_name": origin_name,
                "destination_name": destination_name,
                "origin_coords": list(origin_coords),
                "destination_coords": list(destination_coords),
                "provider": "Simulated Geometry Engine (Unverified)",
                "routing_profile": "simulated",
                "truck_restrictions_enforced": False,
                "profile_disclosure": "Simulated Corridor — Mathematical curve for offline demonstration only; not a verified road route.",
                "is_simulated": True,
                "is_verified_road_route": False,
                "simulation_warning": (
                    "SIMULATED ROUTE: Path was generated via mathematical interpolation. "
                    "It is NOT a verified road route and must not be used for actual navigation."
                ),
            })

        return routes


class MultiSourceRoutingManager:
    """
    Coordinates primary (OpenRouteService) and secondary (OSRM with smart corridor routing).
    Deduplicates overlapping routes, re-indexes unique IDs, and requires 3 distinct routes.
    Simulated fallback is only used when allow_simulated_fallback=True or as a clearly labeled last resort.
    """
    def __init__(self):
        self.ors_provider = OpenRouteServiceProvider()
        self.osrm_provider = OSRMProvider()
        self.fallback_provider = FallbackCorridorProvider()

    def get_three_routes(
        self,
        origin_coords: Tuple[float, float],
        destination_coords: Tuple[float, float],
        origin_name: str,
        destination_name: str,
        allow_simulated_fallback: bool = False
    ) -> List[Dict[str, Any]]:
        # 1. Try OpenRouteService if API key configured
        ors_routes = self.ors_provider.get_three_routes(
            origin_coords, destination_coords, origin_name, destination_name
        )

        # 2. Try OSRM with smart corridor routing
        osrm_routes = self.osrm_provider.get_three_routes(
            origin_coords, destination_coords, origin_name, destination_name
        )

        # Combine candidates (prioritize HGV routes from ORS, followed by OSRM)
        candidates = ors_routes + osrm_routes

        distinct_routes: List[Dict[str, Any]] = []
        for cand in candidates:
            # Check if cand is distinct from all already accepted routes
            is_dup = False
            for existing in distinct_routes:
                if not routes_are_substantially_different(cand, existing):
                    is_dup = True
                    break
            if not is_dup:
                distinct_routes.append(cand)
            if len(distinct_routes) == 3:
                break

        if len(distinct_routes) >= 3:
            # Re-index unique sequential IDs: route_1, route_2, route_3
            for idx, r in enumerate(distinct_routes[:3]):
                r["id"] = f"route_{idx + 1}"
            return distinct_routes[:3]

        # 3. If real routing failed to provide 3 distinct routes:
        if allow_simulated_fallback:
            logger.info("Routing service returned fewer than 3 verified routes. Returning explicitly labeled simulated corridors for demonstration.")
            return self.fallback_provider.get_three_routes(
                origin_coords, destination_coords, origin_name, destination_name
            )
        
        # Raise a clear, informative error
        raise ValueError(
            "Routing provider unavailable: Unable to compute 3 distinct verified highway routes between the specified locations. "
            "Please check network connectivity or enable simulated demonstration mode."
        )


# Global instance
routing_manager = MultiSourceRoutingManager()

