export type RiskLevel = 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel' | 'Data Unavailable';

export type SamplingInterval = 10 | 25 | 50;

export interface GeocodedLocation {
  query: string;
  name: string;
  latitude: number;
  longitude: number;
}

export interface CheckpointHourlyForecast {
  offset_hours: number;
  time: string;
  wind_speed_mph: number | null;
  rain_intensity_in_hr: number | null;
  snow_intensity_in_hr: number | null;
  forecast_available?: boolean;
}

export interface Checkpoint {
  id: string;
  checkpoint_index: number;
  latitude: number;
  longitude: number;
  distance_from_origin_miles: number;
  is_origin: boolean;
  is_destination: boolean;
  elapsed_seconds: number;
  elapsed_hours: number;
  estimated_arrival_time: string;
  arrival_time_formatted: string;
  forecast_lookup_hour: string;
  wind_speed_mph: number | null;
  rain_intensity_in_hr: number | null;
  snow_intensity_in_hr: number | null;
  temperature_f?: number | null;
  forecast_available: boolean;
  wind_risk: RiskLevel;
  rain_risk: RiskLevel;
  snow_risk: RiskLevel;
  weather_risk: RiskLevel;
  load_adjusted_risk: string;
  final_risk: RiskLevel;
  risk_score: number;
  risk_reason: string;
  hourly_timeline?: CheckpointHourlyForecast[];
}

export interface RouteSegment {
  segment_index: number;
  start_checkpoint_id: string;
  end_checkpoint_id: string;
  start_lat: number;
  start_lon: number;
  end_lat: number;
  end_lon: number;
  distance_miles: number;
  risk_level: RiskLevel;
  risk_score?: number;
}

export interface RouteMetrics {
  low_risk_miles: number;
  moderate_risk_miles: number;
  high_risk_miles: number;
  severe_risk_miles: number;
  no_travel_miles: number;
  unknown_risk_miles: number;
  verified_low_risk_miles?: number;
  verified_moderate_risk_miles?: number;
  verified_high_risk_miles?: number;
  verified_severe_risk_miles?: number;
  verified_no_travel_miles?: number;
  known_hazard_severe_miles?: number;

  known_hazard_high_miles?: number;
  known_hazard_moderate_miles?: number;
  partial_data_hazard_miles?: number;
  has_missing_weather: boolean;
  average_risk_score: number;
  overall_route_risk: RiskLevel;
  is_safe_for_travel: boolean;
  checkpoint_count: number;
  segments: RouteSegment[];
}


export interface DynamicHourlyCheckpoint {
  id: string;
  checkpoint_index: number;
  latitude: number;
  longitude: number;
  distance_from_origin_miles: number;
  is_origin?: boolean;
  is_destination?: boolean;
  wind_speed_mph: number | null;
  rain_intensity_in_hr: number | null;
  snow_intensity_in_hr: number | null;
  wind_risk: RiskLevel;
  rain_risk: RiskLevel;
  snow_risk: RiskLevel;
  load_adjusted_risk: string;
  final_risk: RiskLevel;
  risk_score: number;
  forecast_available: boolean;
  reason: string;
}

export interface DynamicHourlyTimelineEntry {
  checkpoints: DynamicHourlyCheckpoint[];
  segments: RouteSegment[];
}

export interface RouteData {
  id: string;
  name: string;
  distance_miles: number;
  duration_seconds: number;
  duration_formatted: string;
  coordinates: [number, number][]; // [lat, lon]
  origin_name: string;
  destination_name: string;
  origin_coords: [number, number];
  destination_coords: [number, number];
  provider: string;
  routing_profile?: string;
  truck_restrictions_enforced?: boolean;
  profile_disclosure?: string;
  is_simulated?: boolean;
  is_verified_road_route?: boolean;
  simulation_warning?: string;
  has_missing_weather?: boolean;
  metrics: RouteMetrics;
  checkpoints: Checkpoint[];
  heatmap_timeline?: Record<string | number, DynamicHourlyTimelineEntry>;
  is_recommended?: boolean;
  is_critically_unsafe?: boolean;
}

export interface RouteRanking {
  rank: number;
  route_id: string;
  name: string;
  severe_miles: number;
  high_miles: number;
  no_travel_miles: number;
  unknown_risk_miles?: number;
  has_missing_weather?: boolean;
  is_simulated?: boolean;
  average_risk_score: number;
  duration_formatted: string;
}

export interface RecommendationResult {
  recommended_route_id: string | null;
  recommended_route: RouteData | null;
  is_any_safe: boolean;
  explanation: string;
  sorted_rankings: RouteRanking[];
}

export interface AnalyzeRoutesResponse {
  status: 'success' | 'error';
  inputs: {
    origin: GeocodedLocation;
    destination: GeocodedLocation;
    departure_time: string;
    departure_time_utc?: string;
    load_weight_lb: number;
    sampling_interval_miles: number;
  };
  routes: RouteData[];
  recommendation: RecommendationResult;
  message?: string;
}

export interface AnalyzeRoutesRequest {
  origin: string;
  destination: string;
  departure_time: string;
  load_weight_lb: number;
  sampling_interval_miles: SamplingInterval;
  timezone_offset_minutes?: number;
  allow_simulated_fallback?: boolean;
}
