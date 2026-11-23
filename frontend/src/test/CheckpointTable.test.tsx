import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CheckpointTable } from '../components/CheckpointTable';
import type { Checkpoint } from '../types';

describe('CheckpointTable Component', () => {
  const mockCheckpoints: Checkpoint[] = [
    {
      id: 'cp_0',
      checkpoint_index: 0,
      latitude: 41.8781,
      longitude: -87.6298,
      distance_from_origin_miles: 0.0,
      elapsed_seconds: 0,
      elapsed_hours: 0,
      estimated_arrival_time: '2026-11-24T08:00:00Z',
      arrival_time_formatted: '08:00 AM',
      forecast_lookup_hour: '2026-11-24T08:00',
      wind_speed_mph: 15.0,
      rain_intensity_in_hr: 0.0,
      snow_intensity_in_hr: 0.0,
      wind_risk: 'Low',
      rain_risk: 'Low',
      snow_risk: 'Low',
      weather_risk: 'Low',
      load_adjusted_risk: 'None',
      final_risk: 'Low',
      risk_score: 1.0,
      risk_reason: 'Normal weather conditions',
      forecast_available: true,
      is_origin: true,
      is_destination: false,
      hourly_timeline: [],
    },
    {
      id: 'cp_1',
      checkpoint_index: 1,
      latitude: 42.0,
      longitude: -85.0,
      distance_from_origin_miles: 150.0,
      elapsed_seconds: 9000,
      elapsed_hours: 2.5,
      estimated_arrival_time: '2026-11-24T10:30:00Z',
      arrival_time_formatted: '10:30 AM',
      forecast_lookup_hour: '2026-11-24T10:00',
      wind_speed_mph: null,
      rain_intensity_in_hr: null,
      snow_intensity_in_hr: null,
      wind_risk: 'Data Unavailable',
      rain_risk: 'Data Unavailable',
      snow_risk: 'Data Unavailable',
      weather_risk: 'Data Unavailable',
      load_adjusted_risk: 'None',
      final_risk: 'Data Unavailable',
      risk_score: 2.0,
      risk_reason: 'Weather forecast unavailable',
      forecast_available: false,
      is_origin: false,
      is_destination: true,
      hourly_timeline: [],
    },
  ];

  it('renders table headers and checkpoint rows', () => {
    render(<CheckpointTable checkpoints={mockCheckpoints} routeName="Test Route" />);

    expect(screen.getByText(/Checkpoint Hazard Inspector/i)).toBeInTheDocument();
    expect(screen.getByText('Origin')).toBeInTheDocument();
    expect(screen.getByText('Destination')).toBeInTheDocument();
  });

  it('displays N/A and Data Unavailable badge for checkpoint with missing forecast', () => {
    render(<CheckpointTable checkpoints={mockCheckpoints} routeName="Test Route" />);

    // Checkpoint 1 has null weather -> displays N/A
    const naItems = screen.getAllByText('N/A');
    expect(naItems.length).toBeGreaterThanOrEqual(3);

    // Displays Data Unavailable badge
    expect(screen.getByText('Data Unavailable')).toBeInTheDocument();

    // Displays Missing forecast in load rule impact
    expect(screen.getByText('Missing forecast')).toBeInTheDocument();
  });

  it('includes Data Unavailable Only in risk level filter', () => {
    render(<CheckpointTable checkpoints={mockCheckpoints} routeName="Test Route" />);

    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Data Unavailable Only' })).toBeInTheDocument();
  });
});
