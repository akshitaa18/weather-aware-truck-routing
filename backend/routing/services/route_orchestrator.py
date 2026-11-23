"""
Route Orchestrator Service.

Executes the complete end-to-end routing analysis workflow:
Geocoding -> Alternative Routes -> Checkpoint Generation -> ETAs ->
Weather Retrieval -> Risk Engine & Load Rules -> Route Metrics ->
Heatmap Generation -> Lexicographical Recommendation.
"""

from typing import Dict, Any, List
from .geocoding import geocode_location
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
    sampling_interval_miles: float
) -> Dict[str, Any]:
    """
    Complete analysis workflow for 3 alternative driving routes.
    """
    # 1. Geocode locations
    origin_geo = geocode_location(origin_query)
    dest_geo = geocode_location(destination_query)

    origin_coords = (origin_geo["latitude"], origin_geo["longitude"])
    dest_coords = (dest_geo["latitude"], dest_geo["longitude"])

    # 2. Retrieve 3 alternative routes
    routes = routing_manager.get_three_routes(
        origin_coords, dest_coords, origin_geo["name"], dest_geo["name"]
    )

    if not routes:
        raise ValueError("Failed to calculate driving routes between specified locations.")

    # 3. Process each route
    processed_routes = []
    for r in routes:
        coords = r["coordinates"]
        total_dist = r["distance_miles"]
        total_dur = r["duration_seconds"]

        # Checkpoints along geometry
        checkpoints = generate_checkpoints(coords, sampling_interval_miles, total_dist)

        # ETAs at checkpoints
        checkpoints = calculate_checkpoint_etas(checkpoints, departure_time_iso, total_dur, total_dist)

        # Weather retrieval for ETA hours
        checkpoints = weather_provider.fetch_weather_for_checkpoints(checkpoints)

        # Risk classification for checkpoints
        for cp in checkpoints:
            w_mph = cp.get("wind_speed_mph", 0.0)
            r_in = cp.get("rain_intensity_in_hr", 0.0)
            s_in = cp.get("snow_intensity_in_hr", 0.0)
            
            risk_eval = evaluate_checkpoint_risk(w_mph, r_in, s_in, load_weight_lb)
            cp["wind_risk"] = risk_eval["wind_risk"]
            cp["rain_risk"] = risk_eval["rain_risk"]
            cp["snow_risk"] = risk_eval["snow_risk"]
            cp["weather_risk"] = risk_eval["weather_risk"]
            cp["load_adjusted_risk"] = risk_eval["load_adjusted_risk"]
            cp["final_risk"] = risk_eval["final_risk"]
            cp["risk_score"] = risk_eval["risk_score"]
            cp["risk_reason"] = risk_eval["reason"]

        # Route metrics and risk miles attribution
        metrics = analyze_route_metrics(r, checkpoints)
        r["metrics"] = metrics
        r["checkpoints"] = checkpoints

        # 0–48 hour heatmap timeline for route corridor
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
            "load_weight_lb": load_weight_lb,
            "sampling_interval_miles": sampling_interval_miles,
        },
        "routes": processed_routes,
        "recommendation": rec_result,
    }
