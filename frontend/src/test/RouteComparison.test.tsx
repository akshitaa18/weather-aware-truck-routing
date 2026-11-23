import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RouteComparison } from '../components/RouteComparison';
import type { RouteData } from '../types';

describe('RouteComparison Component', () => {
  const mockRouteVerified: RouteData = {
    id: 'route_1',
    name: 'Verified Road Route',
    distance_miles: 280.0,
    duration_seconds: 16800,
    duration_formatted: '4h 40m',
    coordinates: [[41.8781, -87.6298], [42.3314, -83.0458]],
    origin_name: 'Chicago, IL',
    destination_name: 'Detroit, MI',
    origin_coords: [41.8781, -87.6298],
    destination_coords: [42.3314, -83.0458],
    provider: 'OSRM Routing Engine',
    is_simulated: false,
    is_verified_road_route: true,
    metrics: {
      severe_risk_miles: 0.0,
      high_risk_miles: 15.0,
      moderate_risk_miles: 45.0,
      low_risk_miles: 220.0,
      no_travel_miles: 0.0,
      unknown_risk_miles: 0.0,
      average_risk_score: 1.4,
      overall_route_risk: 'Moderate',
      is_safe_for_travel: true,
      has_missing_weather: false,
      checkpoint_count: 5,
      segments: [],
    },
    checkpoints: [],
  };

  const mockRouteSimulated: RouteData = {
    ...mockRouteVerified,
    id: 'route_2',
    name: 'Simulated Corridor',
    provider: 'Simulated Geometry Engine (Unverified)',
    is_simulated: true,
    is_verified_road_route: false,
    simulation_warning: 'SIMULATED CORRIDOR: Synthetic geometry fallback.',
  };

  const mockRouteMissingData: RouteData = {
    ...mockRouteVerified,
    id: 'route_3',
    name: 'Route With Missing Forecast',
    has_missing_weather: true,
    metrics: {
      ...mockRouteVerified.metrics,
      has_missing_weather: true,
      unknown_risk_miles: 35.0,
      is_safe_for_travel: false,
    },
  };

  it('renders simulated badge and warning when route is simulated geometry', () => {
    const handleSelect = vi.fn();
    render(
      <RouteComparison
        routes={[mockRouteSimulated]}
        selectedRouteId="route_2"
        onSelectRoute={handleSelect}
      />
    );

    expect(screen.getByText('Simulated')).toBeInTheDocument();
    expect(screen.getByText(/Synthetic geometry — not a verified road corridor/i)).toBeInTheDocument();
  });

  it('renders missing data badge and notice when forecast is unavailable', () => {
    const handleSelect = vi.fn();
    render(
      <RouteComparison
        routes={[mockRouteMissingData]}
        selectedRouteId="route_3"
        onSelectRoute={handleSelect}
      />
    );

    expect(screen.getByText('Missing Data')).toBeInTheDocument();
    expect(screen.getByText(/35 mi unforecasted; safety clearance withheld/i)).toBeInTheDocument();
  });
});
