import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskDistributionChart } from '../components/RiskDistributionChart';
import type { RouteData } from '../types';

describe('RiskDistributionChart Component', () => {
  const baseRoute: RouteData = {
    id: 'route_1',
    name: 'I-94 Corridor',
    distance_miles: 100.0,
    duration_seconds: 7200,
    duration_formatted: '2h 0m',
    coordinates: [[41.8781, -87.6298], [42.3314, -83.0458]],
    origin_name: 'Chicago, IL',
    destination_name: 'Detroit, MI',
    origin_coords: [41.8781, -87.6298],
    destination_coords: [42.3314, -83.0458],
    provider: 'OSRM',
    is_simulated: false,
    is_verified_road_route: true,
    metrics: {
      severe_risk_miles: 0.0,
      high_risk_miles: 0.0,
      moderate_risk_miles: 0.0,
      low_risk_miles: 60.0,
      no_travel_miles: 0.0,
      unknown_risk_miles: 0.0,
      verified_no_travel_miles: 0.0,
      average_risk_score: 1.0,
      overall_route_risk: 'Low',
      is_safe_for_travel: true,
      has_missing_weather: false,
      checkpoint_count: 5,
      segments: [],
    },
    checkpoints: [],
  };

  it('renders title and stacked breakdown description', () => {
    render(<RiskDistributionChart routes={[baseRoute]} />);
    expect(screen.getByText(/Corridor Risk Exposure Breakdown/i)).toBeInTheDocument();
  });

  it('displays detected No-Travel hazard annotation when an incomplete-weather segment encounters hurricane wind', () => {
    // 100-mile corridor: 60 miles verified Low, 40 miles unforecasted with detected No-Travel wind (60 mph)
    const routeWithIncompleteNoTravel: RouteData = {
      ...baseRoute,
      id: 'route_nt_partial',
      name: 'Corridor With Unforecasted No-Travel',
      metrics: {
        ...baseRoute.metrics,
        low_risk_miles: 60.0,
        no_travel_miles: 40.0, // preserved hazard
        unknown_risk_miles: 40.0, // incomplete weather mileage
        verified_no_travel_miles: 0.0, // 0 verified No-Travel miles
        partial_data_hazard_miles: 40.0,
        has_missing_weather: true,
        is_safe_for_travel: false,
        overall_route_risk: 'No Travel',
      },
    };

    render(<RiskDistributionChart routes={[routeWithIncompleteNoTravel]} />);

    // Annotation banner must be visible and explicitly state the detected hazard on unforecasted segment
    expect(screen.getByText(/40 mi active No-Travel hazard/i)).toBeInTheDocument();
    expect(screen.getByText(/on unforecasted corridor/i)).toBeInTheDocument();
  });

  it('displays verified No-Travel hazard annotation without unforecasted qualifier when verified', () => {
    // 100-mile corridor: 75 miles verified Low, 25 miles verified No-Travel
    const routeWithVerifiedNoTravel: RouteData = {
      ...baseRoute,
      id: 'route_nt_verified',
      name: 'Corridor With Verified No-Travel',
      metrics: {
        ...baseRoute.metrics,
        low_risk_miles: 75.0,
        no_travel_miles: 25.0,
        unknown_risk_miles: 0.0,
        verified_no_travel_miles: 25.0,
        has_missing_weather: false,
        is_safe_for_travel: false,
        overall_route_risk: 'No Travel',
      },
    };

    render(<RiskDistributionChart routes={[routeWithVerifiedNoTravel]} />);

    expect(screen.getByText(/25 mi active No-Travel hazard/i)).toBeInTheDocument();
    expect(screen.queryByText(/on unforecasted corridor/i)).not.toBeInTheDocument();
  });
});
