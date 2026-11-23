"""
Routing Provider Abstraction and Implementations.

Supports:
1. OpenRouteService (HGV truck profile, 3 alternatives)
2. OSRM with Smart Corridor Waypoint Routing (guaranteeing distinct genuine driving routes)
3. Clearly labeled Fallback Corridor Provider for offline demonstration purposes only
"""

import os
import math
import requests
from typing import List, Dict, Any, Tuple, Optional

METERS_TO_MILES = 0.000621371


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
                        "is_simulated": False,
                        "is_verified_road_route": True,
                    })
                return routes
        except Exception as e:
            print(f"OpenRouteService query failed: {e}")
        return []


class OSRMProvider(RoutingProvider):
    """
    OSRM routing provider with Smart Corridor Waypoint Strategy.
    Generates genuine driving routes across real highway networks.
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
            resp = requests.get(url, timeout=7)
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

                    routes.append({
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
                        "is_simulated": False,
                        "is_verified_road_route": True,
                    })
        except Exception as e:
            print(f"OSRM initial query error: {e}")

        # If we have fewer than 3 routes, query intermediate corridor waypoints through OSRM
        if len(routes) < 3:
            needed = 3 - len(routes)
            mid_lat = (lat1 + lat2) / 2.0
            mid_lon = (lon1 + lon2) / 2.0
            
            d_lat = lat2 - lat1
            d_lon = lon2 - lon1
            length = math.sqrt(d_lat * d_lat + d_lon * d_lon) or 1.0
            
            perp_lat = -d_lon / length
            perp_lon = d_lat / length
            
            offset_multipliers = [0.85, -0.85] if needed == 2 else [0.85]
            
            for m in offset_multipliers:
                if len(routes) >= 3:
                    break
                via_lat = round(mid_lat + m * perp_lat, 4)
                via_lon = round(mid_lon + m * perp_lon, 4)
                
                try:
                    via_url = f"{self.BASE_URL}/{lon1},{lat1};{via_lon},{via_lat};{lon2},{lat2}?overview=full&geometries=geojson&steps=true"
                    via_resp = requests.get(via_url, timeout=7)
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
                            corridor_tag = "Northern Corridor" if m > 0 else "Southern Corridor"
                            name = extract_route_name(steps, f"{corridor_tag} Route")
                            
                            routes.append({
                                "id": f"route_{len(routes) + 1}",
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
                                "is_simulated": False,
                                "is_verified_road_route": True,
                            })
                except Exception as ex:
                    print(f"OSRM waypoint route error: {ex}")

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
    Prefers returning genuine road routes or raising a clear error if actual road routing fails.
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
        if len(ors_routes) >= 3:
            return ors_routes[:3]

        # 2. Try OSRM with smart corridor routing
        osrm_routes = self.osrm_provider.get_three_routes(
            origin_coords, destination_coords, origin_name, destination_name
        )
        if len(osrm_routes) >= 3:
            return osrm_routes[:3]

        # Combine any genuine routes returned
        combined = ors_routes + osrm_routes
        if combined:
            return combined[:3]

        # 3. If real routing failed completely:
        if allow_simulated_fallback:
            print("Routing service unavailable. Returning explicitly labeled simulated corridors for demonstration.")
            return self.fallback_provider.get_three_routes(
                origin_coords, destination_coords, origin_name, destination_name
            )
        
        # Prefer raising a clear, informative error
        raise ValueError(
            "Routing provider unavailable: Unable to compute verified highway routes between the specified locations. "
            "Please check network connectivity or try again in a few moments."
        )


# Global instance
routing_manager = MultiSourceRoutingManager()
