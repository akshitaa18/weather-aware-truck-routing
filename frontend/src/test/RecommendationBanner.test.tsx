import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RecommendationBanner } from '../components/RecommendationBanner';
import type { RecommendationResult, RouteData } from '../types';

describe('RecommendationBanner Component', () => {
  const mockRoute: RouteData = {
    id: 'route_1',
    name: 'Primary Highway Corridor',
    distance_miles: 280.0,
    duration_seconds: 16800,
    duration_formatted: '4h 40m',
    coordinates: [[41.8781, -87.6298], [42.3314, -83.0458]],
    origin_name: 'Chicago, IL',
    destination_name: 'Detroit, MI',
    origin_coords: [41.8781, -87.6298],
    destination_coords: [42.3314, -83.0458],
    provider: 'OSRM Routing Engine',
    metrics: {
      severe_risk_miles: 0.0,
      high_risk_miles: 0.0,
      moderate_risk_miles: 40.0,
      low_risk_miles: 240.0,
      no_travel_miles: 0.0,
      unknown_risk_miles: 0.0,
      average_risk_score: 1.2,
      overall_route_risk: 'Low',
      is_safe_for_travel: true,
      has_missing_weather: false,
      checkpoint_count: 5,
      segments: [],
    },
    checkpoints: [],
  };

  it('renders recommended route banner when safe', () => {
    const rec: RecommendationResult = {
      recommended_route_id: 'route_1',
      recommended_route: mockRoute,
      is_any_safe: true,
      explanation: 'Optimal route selected with lowest exposure.',
      sorted_rankings: [],
    };

    const handleSelect = vi.fn();
    render(<RecommendationBanner recommendation={rec} routes={[mockRoute]} onSelectRoute={handleSelect} />);

    expect(screen.getByText('RECOMMENDED ROUTE')).toBeInTheDocument();
    expect(screen.getByText('Safe for Travel')).toBeInTheDocument();
    expect(screen.getByText('Primary Highway Corridor')).toBeInTheDocument();
  });

  it('renders clearance withheld warning when forecast data is missing', () => {
    const rec: RecommendationResult = {
      recommended_route_id: 'route_1',
      recommended_route: mockRoute,
      is_any_safe: false,
      explanation: 'Required weather forecast data is unavailable along route segments. Cannot verify safe passage.',
      sorted_rankings: [],
    };

    const handleSelect = vi.fn();
    render(<RecommendationBanner recommendation={rec} routes={[mockRoute]} onSelectRoute={handleSelect} />);

    expect(screen.getByText('Clearance Withheld')).toBeInTheDocument();
    expect(screen.getByText(/Weather Forecast Unavailable — Safety Clearance Withheld/i)).toBeInTheDocument();
    expect(screen.getByText('Inspect Best Route')).toBeInTheDocument();
  });

  it('renders unverified geometry warning when route is simulated', () => {
    const rec: RecommendationResult = {
      recommended_route_id: 'route_1',
      recommended_route: mockRoute,
      is_any_safe: false,
      explanation: 'Routes are based on simulated geometry corridors. Cannot certify simulated routes.',
      sorted_rankings: [],
    };

    const handleSelect = vi.fn();
    render(<RecommendationBanner recommendation={rec} routes={[mockRoute]} onSelectRoute={handleSelect} />);

    expect(screen.getByText('Unverified Geometry')).toBeInTheDocument();
    expect(screen.getByText(/Simulated Geometry Fallback — Safety Clearance Withheld/i)).toBeInTheDocument();
  });
});
