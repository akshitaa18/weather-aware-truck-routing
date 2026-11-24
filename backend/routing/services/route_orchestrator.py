"""
Route Orchestrator Service.

Executes the complete end-to-end routing analysis workflow:
Geocoding -> Alternative Routes -> Checkpoint Generation -> ETAs in UTC ->
Weather Retrieval -> Risk Engine & Load Rules -> Route Metrics ->
Dynamic Heatmap Matrix -> Lexicographical Recommendation.
"""

from typing import Dict, Any, List, Optional
from .geocoding import geocode_location, geocode_locations_concurrent
from .routing_provider import routing_manager
from .checkpoint_generator import generate_checkpoints
from .arrival_time import calculate_checkpoint_etas
from .weather_provider import weather_provider
from .risk_engine import evaluate_checkpoint_risk
from .route_analyzer import analyze_route_metrics
from .recommendation import select_recommended_route
from .heatmap import generate_corridor_heatmap_timeline


def analyze_weather_truck_routes(
    origin_query: str,
    destination_query: str,
    departure_time_iso: str,
    load_weight_lb: float,
    sampling_interval_miles: float,
    user_timezone_offset_minutes: Optional[int] = None,
    allow_simulated_fallback: bool = False
) -> Dict[str, Any]:
    """
    Complete analysis workflow for 3 alternative driving routes.
    """
    # 1. Geocode locations concurrently to reduce latency
    origin_geo, dest_geo = geocode_locations_concurrent(origin_query, destination_query)

    origin_coords = (origin_geo["latitude"], origin_geo["longitude"])
    dest_coords = (dest_geo["latitude"], dest_geo["longitude"])

    # 2. Retrieve 3 alternative routes (real road routes preferred; error if unavailable)
    routes = routing_manager.get_three_routes(
        origin_coords,
        dest_coords,
        origin_geo["name"],
        dest_geo["name"],
        allow_simulated_fallback=allow_simulated_fallback
    )

    if not routes:
        raise ValueError("Failed to calculate driving routes between specified locations.")

    # 3. Generate checkpoints and ETAs for all routes
    dep_time_utc_global = None
    all_route_checkpoints = []

    for r in routes:
        coords = r["coordinates"]
        total_dist = r["distance_miles"]
        total_dur = r["duration_seconds"]

        # Checkpoints along true route polyline
        checkpoints = generate_checkpoints(coords, sampling_interval_miles, total_dist)

        # ETAs at checkpoints in UTC
        checkpoints, dep_time_utc = calculate_checkpoint_etas(
            checkpoints,
            departure_time_iso,
            total_dur,
            total_dist,
            user_timezone_offset_minutes=user_timezone_offset_minutes
        )
        if not dep_time_utc_global:
            dep_time_utc_global = dep_time_utc

        r["checkpoints"] = checkpoints
        all_route_checkpoints.append(checkpoints)

    # 4. Prefetch weather across all routes concurrently (deduplicating shared corridor points)
    weather_provider.prefetch_weather_for_multiple_routes(all_route_checkpoints)

    # 5. Process risk analysis and dynamic heatmap for each route
    processed_routes = []

    for r in routes:
        checkpoints = r["checkpoints"]

        # Weather retrieval for ETA hours (hits cache instantly from prefetch)
        checkpoints = weather_provider.fetch_weather_for_checkpoints(
            checkpoints,
            departure_time_utc_iso=dep_time_utc_global or departure_time_iso
        )

        # Risk classification for checkpoints (strict missing data handling)
        for cp in checkpoints:
            w_mph = cp.get("wind_speed_mph")
            r_in = cp.get("rain_intensity_in_hr")
            s_in = cp.get("snow_intensity_in_hr")
            is_avail = cp.get("forecast_available", False)
            
            risk_eval = evaluate_checkpoint_risk(
                w_mph, r_in, s_in, load_weight_lb, forecast_available=is_avail
            )
            cp["wind_risk"] = risk_eval["wind_risk"]
            cp["rain_risk"] = risk_eval["rain_risk"]
            cp["snow_risk"] = risk_eval["snow_risk"]
            cp["weather_risk"] = risk_eval["weather_risk"]
            cp["load_adjusted_risk"] = risk_eval["load_adjusted_risk"]
            cp["final_risk"] = risk_eval["final_risk"]
            cp["risk_score"] = risk_eval["risk_score"]
            cp["forecast_available"] = risk_eval["forecast_available"]
            cp["risk_reason"] = risk_eval["reason"]

        # Route metrics and risk miles attribution
        metrics = analyze_route_metrics(r, checkpoints)
        r["metrics"] = metrics
        r["checkpoints"] = checkpoints

        # 0–48 hour dynamic heatmap timeline for route corridor (relative to departure time)
        r["heatmap_timeline"] = generate_corridor_heatmap_timeline(checkpoints, load_weight_lb)

        processed_routes.append(r)

    # 4. Lexicographical Recommendation
    rec_result = select_recommended_route(processed_routes)

    return {
        "status": "success",
        "inputs": {
            "origin": origin_geo,
            "destination": dest_geo,
            "departure_time": departure_time_iso,
            "departure_time_utc": dep_time_utc_global or departure_time_iso,
            "load_weight_lb": load_weight_lb,
            "sampling_interval_miles": sampling_interval_miles,
        },
        "routes": processed_routes,
        "recommendation": rec_result,
    }
