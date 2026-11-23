"""
Weather Checkpoint Generation Service.

Generates weather checkpoints along the actual route polyline geometry
at user-selected intervals (10, 25, or 50 miles) and ensures the destination
is always included without duplicate checkpoints.
"""

import math
from typing import List, Tuple, Dict, Any

EARTH_RADIUS_MILES = 3958.8


def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points in miles using Haversine formula.
    """
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_MILES * c


def compute_cumulative_distances(coordinates: List[Tuple[float, float]]) -> List[float]:
    """
    Given a list of (lat, lon) coordinates, return cumulative distances in miles.
    """
    if not coordinates:
        return []
    
    cumulative = [0.0]
    total = 0.0
    for i in range(len(coordinates) - 1):
        lat1, lon1 = coordinates[i]
        lat2, lon2 = coordinates[i + 1]
        dist = haversine_distance_miles(lat1, lon1, lat2, lon2)
        total += dist
        cumulative.append(total)
    return cumulative


def interpolate_coordinate(
    p1: Tuple[float, float], p2: Tuple[float, float], fraction: float
) -> Tuple[float, float]:
    """
    Linearly interpolate between two (lat, lon) points given fraction [0.0, 1.0].
    """
    lat = p1[0] + fraction * (p2[0] - p1[0])
    lon = p1[1] + fraction * (p2[1] - p1[1])
    return (round(lat, 6), round(lon, 6))


def generate_checkpoints(
    coordinates: List[Tuple[float, float]],
    interval_miles: float,
    total_route_distance_miles: float = None
) -> List[Dict[str, Any]]:
    """
    Generate checkpoints along the route polyline at specified interval miles.
    
    Ensures:
    - Origin is checkpoint 0 (distance 0.0)
    - Checkpoints placed at exact interval increments (e.g. 25, 50, 75 miles)
    - Destination is included as the final checkpoint
    - Duplicate checkpoints near the destination are prevented
    """
    if not coordinates or len(coordinates) < 2:
        return []
    
    cumulative_distances = compute_cumulative_distances(coordinates)
    computed_total_dist = cumulative_distances[-1]
    total_dist = total_route_distance_miles if total_route_distance_miles is not None else computed_total_dist
    
    # Scale factor if route total distance differs slightly from polyline haversine sum
    scale = (total_dist / computed_total_dist) if computed_total_dist > 0 else 1.0

    checkpoints: List[Dict[str, Any]] = []
    
    # Origin checkpoint
    origin_coord = coordinates[0]
    checkpoints.append({
        "id": "cp_0",
        "checkpoint_index": 0,
        "latitude": round(origin_coord[0], 6),
        "longitude": round(origin_coord[1], 6),
        "distance_from_origin_miles": 0.0,
        "is_origin": True,
        "is_destination": False,
    })
    
    target_dist = interval_miles
    coord_idx = 0
    cp_count = 1
    
    while target_dist < total_dist:
        # Don't place a sample point if it's within 1.0 mile of destination
        if (total_dist - target_dist) < 1.0:
            break
            
        scaled_target = target_dist / scale
        
        while coord_idx < len(coordinates) - 1 and cumulative_distances[coord_idx + 1] < scaled_target:
            coord_idx += 1
            
        if coord_idx >= len(coordinates) - 1:
            break
            
        d_start = cumulative_distances[coord_idx]
        d_end = cumulative_distances[coord_idx + 1]
        seg_len = d_end - d_start
        
        if seg_len > 0:
            fraction = (scaled_target - d_start) / seg_len
            fraction = max(0.0, min(1.0, fraction))
            interp_lat, interp_lon = interpolate_coordinate(
                coordinates[coord_idx], coordinates[coord_idx + 1], fraction
            )
        else:
            interp_lat, interp_lon = coordinates[coord_idx]
            
        checkpoints.append({
            "id": f"cp_{cp_count}",
            "checkpoint_index": cp_count,
            "latitude": interp_lat,
            "longitude": interp_lon,
            "distance_from_origin_miles": round(target_dist, 2),
            "is_origin": False,
            "is_destination": False,
        })
        cp_count += 1
        target_dist += interval_miles

    # Destination checkpoint: ALWAYS included
    dest_coord = coordinates[-1]
    
    # If the last checkpoint is within 0.5 miles of the destination, replace it with exact destination
    if len(checkpoints) > 1 and (total_dist - checkpoints[-1]["distance_from_origin_miles"]) < 0.5:
        checkpoints[-1]["latitude"] = round(dest_coord[0], 6)
        checkpoints[-1]["longitude"] = round(dest_coord[1], 6)
        checkpoints[-1]["distance_from_origin_miles"] = round(total_dist, 2)
        checkpoints[-1]["is_destination"] = True
    else:
        checkpoints.append({
            "id": f"cp_{cp_count}",
            "checkpoint_index": cp_count,
            "latitude": round(dest_coord[0], 6),
            "longitude": round(dest_coord[1], 6),
            "distance_from_origin_miles": round(total_dist, 2),
            "is_origin": False,
            "is_destination": True,
        })

    return checkpoints
