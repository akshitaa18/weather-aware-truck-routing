import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ForecastSlider } from '../components/ForecastSlider';

describe('ForecastSlider Component', () => {
  it('renders slider and selected forecast offset indicator', () => {
    const handleOffset = vi.fn();
    render(
      <ForecastSlider
        departureTimeIso="2026-11-24T08:00"
        forecastOffsetHours={0}
        onOffsetChange={handleOffset}
      />
    );

    expect(screen.getByText('Departure Time')).toBeInTheDocument();
    expect(screen.getByText(/Weather Forecast Corridor Slider/i)).toBeInTheDocument();
  });

  it('triggers offset change when slider input moves', () => {
    const handleOffset = vi.fn();
    render(
      <ForecastSlider
        departureTimeIso="2026-11-24T08:00"
        forecastOffsetHours={0}
        onOffsetChange={handleOffset}
      />
    );

    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '12' } });

    expect(handleOffset).toHaveBeenCalledWith(12);
  });
});
