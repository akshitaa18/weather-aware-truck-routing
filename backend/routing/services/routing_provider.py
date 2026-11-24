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

from .checkpoint_generator import haversine_distance_miles, compute_cumulative_distances

logger = logging.getLogger(__name__)

METERS_TO_MILES = 0.000621371

# Reusable HTTP session with connection pooling for routing requests
_ROUTING_SESSION = requests.Session()
_ROUTING_ADAPTER = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=1)
_ROUTING_SESSION.mount("https://", _ROUTING_ADAPTER)
_ROUTING_SESSION.mount("http://", _ROUTING_ADAPTER)


def sample_polyline_by_distance(
    coordinates: List[List[float]], num_samples: int = 25
) -> List[Tuple[float, float]]:
    """
    Sample points along a polyline at regular distance intervals from 0% to 100% of physical distance.
    Uses linear interpolation between adjacent polyline vertices based on cumulative distance.
    """
    if not coordinates:
        return []
    if len(coordinates) == 1:
        return [(float(coordinates[0][0]), float(coordinates[0][1]))]

    tuple_coords = [(float(c[0]), float(c[1])) for c in coordinates]
    cum_dist = compute_cumulative_distances(tuple_coords)
    total_len = cum_dist[-1]
    if total_len <= 0.0:
        return [(tuple_coords[0][0], tuple_coords[0][1])] * num_samples

    samples: List[Tuple[float, float]] = []
    coord_idx = 0
    n_coords = len(tuple_coords)

    for i in range(num_samples):
        target = (i / float(num_samples - 1)) * total_len
        while coord_idx < n_coords - 2 and cum_dist[coord_idx + 1] < target:
            coord_idx += 1

        seg_start = cum_dist[coord_idx]
        seg_end = cum_dist[coord_idx + 1]
        seg_len = seg_end - seg_start

        if seg_len > 0:
            frac = (target - seg_start) / seg_len
            frac = max(0.0, min(1.0, frac))
            p1 = tuple_coords[coord_idx]
            p2 = tuple_coords[coord_idx + 1]
            lat = p1[0] + frac * (p2[0] - p1[0])
            lon = p1[1] + frac * (p2[1] - p1[1])
            samples.append((round(lat, 6), round(lon, 6)))
        else:
            samples.append((tuple_coords[coord_idx][0], tuple_coords[coord_idx][1]))

    return samples


def routes_are_substantially_different(r1: Dict[str, Any], r2: Dict[str, Any]) -> bool:
    """
    Check if two routes follow substantially distinct driving corridors based on actual geometry.
    
    Distance difference alone is NEVER sufficient to declare two routes distinct.
    Compares the geometry using physical-distance-based sampling along the complete polylines.
    Rejects identical and substantially overlapping routes as duplicates, even if reported distances differ.
    
    Distinctness Criterion:
    - Calculates the proportion of sampled points on each route that are at least 8.0 miles
      from the closest point on the other route.
    - Uses bidirectional comparison (checks divergence of route 1 from route 2, and route 2 from route 1).
    - Requires meaningful corridor divergence across a sufficient proportion of the route
      (at least 20% of sampled points on both routes must be >= 8.0 miles apart),
      rather than relying solely on an isolated maximum deviation.
    - Rejects routes that share most of their highway and diverge only for a short section or detour.
    - Preserves acceptance of genuinely distinct alternative highway corridors (e.g. northern vs southern).
    """
    coords1 = r1.get("coordinates", [])
    coords2 = r2.get("coordinates", [])
    if not coords1 or not coords2 or len(coords1) < 2 or len(coords2) < 2:
        return False

    # Sample both polylines at 25 regular distance intervals along the entire path
    samples1 = sample_polyline_by_distance(coords1, num_samples=25)
    samples2 = sample_polyline_by_distance(coords2, num_samples=25)

    if not samples1 or not samples2:
        return False

    # Bidirectional distance calculations for each sampled point
    dists_from_1_to_2 = [
        min(haversine_distance_miles(p1[0], p1[1], p2[0], p2[1]) for p2 in samples2)
        for p1 in samples1
    ]
    dists_from_2_to_1 = [
        min(haversine_distance_miles(p2[0], p2[1], p1[0], p1[1]) for p1 in samples1)
        for p2 in samples2
    ]

    # Calculate proportion of sampled points on each route that are at least 8.0 miles away
    prop1 = sum(1 for d in dists_from_1_to_2 if d >= 8.0) / float(len(samples1))
    prop2 = sum(1 for d in dists_from_2_to_1 if d >= 8.0) / float(len(samples2))

    # Meaningful corridor divergence requirement:
    # Requires at least 20% of sampled points on both routes to be at least 8.0 miles apart.
    # Isolated deviations on a shared highway (< 20%) are rejected as duplicates.
    return prop1 >= 0.20 and prop2 >= 0.20



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

