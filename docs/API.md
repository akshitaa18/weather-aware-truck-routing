# REST API Documentation: Weather-Aware Truck Routing

This document provides complete technical specifications for the backend REST endpoints.

---

## 1. Analyze Routes

### `POST /api/routes/analyze/`

Initiates end-to-end geocoding, multi-alternative routing, checkpoint generation, hourly weather matching, vehicle load risk adjustment, and lexicographical safety recommendation.

#### Request Headers
| Header | Value | Required |
|---|---|---|
| `Content-Type` | `application/json` | Yes |
| `Accept` | `application/json` | Yes |

#### Request Body
```json
{
  "origin": "Chicago, IL",
  "destination": "Detroit, MI",
  "departure_time": "2026-11-24T08:00",
  "load_weight_lb": 42000.0,
  "sampling_interval_miles": 25
}
```

#### Field Specifications & Validation Rules
| Field | Type | Description | Constraints |
|---|---|---|---|
| `origin` | String | Origin location | Required, non-empty, distinct from destination |
| `destination` | String | Destination location | Required, non-empty, distinct from origin |
| `departure_time` | String | Planned departure timestamp | Required, ISO 8601 (`YYYY-MM-DDTHH:MM`) |
| `load_weight_lb` | Float | Vehicle gross cargo load weight in pounds | Required, `0.0 <= load <= 120,000.0` |
| `sampling_interval_miles` | Integer | Distance interval between weather samples | Required, choice: `10`, `25`, or `50` |

#### Success Response (`200 OK`)
```json
{
  "status": "success",
  "inputs": {
    "origin": {
      "query": "Chicago, IL",
      "name": "Chicago, Cook County, Illinois, United States",
      "latitude": 41.875562,
      "longitude": -87.624421
    },
    "destination": {
      "query": "Detroit, MI",
      "name": "Detroit, Wayne County, Michigan, United States",
      "latitude": 42.331427,
      "longitude": -83.045754
    },
    "departure_time": "2026-11-24T08:00",
    "load_weight_lb": 42000.0,
    "sampling_interval_miles": 25.0
  },
  "routes": [
    {
      "id": "route_1",
      "name": "Primary Route via I-94 E",
      "distance_miles": 281.5,
      "duration_seconds": 19020.0,
      "duration_formatted": "5h 17m",
      "coordinates": [[41.875562, -87.624421], [41.880123, -87.618991]],
      "origin_name": "Chicago, IL",
      "destination_name": "Detroit, MI",
      "provider": "OSRM Routing Engine",
      "metrics": {
        "low_risk_miles": 281.5,
        "moderate_risk_miles": 0.0,
        "high_risk_miles": 0.0,
        "severe_risk_miles": 0.0,
        "no_travel_miles": 0.0,
        "average_risk_score": 1.0,
        "overall_route_risk": "Low",
        "is_safe_for_travel": true,
        "checkpoint_count": 13,
        "segments": []
      },
      "checkpoints": [
        {
          "id": "cp_0",
          "checkpoint_index": 0,
          "latitude": 41.875562,
          "longitude": -87.624421,
          "distance_from_origin_miles": 0.0,
          "is_origin": true,
          "is_destination": false,
          "elapsed_seconds": 0.0,
          "elapsed_hours": 0.0,
          "estimated_arrival_time": "2026-11-24T08:00:00",
          "arrival_time_formatted": "Nov 24, 2026 08:00 AM",
          "wind_speed_mph": 8.5,
          "rain_intensity_in_hr": 0.0,
          "snow_intensity_in_hr": 0.0,
          "wind_risk": "Low",
          "rain_risk": "Low",
          "snow_risk": "Low",
          "weather_risk": "Low",
          "load_adjusted_risk": "None",
          "final_risk": "Low",
          "risk_score": 1,
          "risk_reason": "Favorable driving conditions"
        }
      ],
      "heatmap_timeline": {},
      "is_recommended": true,
      "is_critically_unsafe": false
    }
  ],
  "recommendation": {
    "recommended_route_id": "route_1",
    "is_any_safe": true,
    "explanation": "Recommended Primary Route via I-94 E as the safest driving corridor. Lowest overall risk score (1.00). Optimal travel time (5h 17m) among safest options. Total distance: 281.5 miles, estimated duration: 5h 17m.",
    "sorted_rankings": [
      {
        "rank": 1,
        "route_id": "route_1",
        "name": "Primary Route via I-94 E",
        "severe_miles": 0.0,
        "high_miles": 0.0,
        "no_travel_miles": 0.0,
        "average_risk_score": 1.0,
        "duration_formatted": "5h 17m"
      }
    ]
  }
}
```

#### Error Response (`400 Bad Request`)
```json
{
  "status": "error",
  "errors": {
    "load_weight_lb": ["Ensure this value is greater than or equal to 0.0."]
  },
  "message": "Validation failed for route analysis request."
}
```

---

## 2. Compare Routes

### `POST /api/routes/compare/`
Alias to `POST /api/routes/analyze/` supporting identical parameters for route comparison workflows.

---

## 3. Routing Engine Health Check

### `GET /api/routes/health/`
Checks the operational status of routing services.

#### Response (`200 OK`)
```json
{
  "status": "healthy",
  "service": "weather-aware-truck-routing",
  "routing_engines": [
    "OSRM Smart Corridor",
    "OpenRouteService",
    "Highway Corridor Fallback"
  ],
  "geocoding_engine": "OpenStreetMap Nominatim / Photon"
}
```

---

## 4. Weather Provider Health Check

### `GET /api/weather/health/`
Verifies live connectivity and latency to the Open-Meteo API.

#### Response (`200 OK`)
```json
{
  "status": "healthy",
  "provider": "Open-Meteo",
  "response_time_ms": 142.5
}
```
