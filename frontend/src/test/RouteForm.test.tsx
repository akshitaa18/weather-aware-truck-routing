import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RouteForm } from '../components/RouteForm';

describe('RouteForm Component', () => {
  it('renders all form inputs and submit button', () => {
    const handleSubmit = vi.fn();
    render(<RouteForm onSubmit={handleSubmit} isLoading={false} />);

    expect(screen.getByText('Origin Location')).toBeInTheDocument();
    expect(screen.getByText('Destination Location')).toBeInTheDocument();
    expect(screen.getByText('Departure Date & Time')).toBeInTheDocument();
    expect(screen.getByText('Truck Load Weight (lb)')).toBeInTheDocument();
    expect(screen.getByText('Weather Sampling Granularity')).toBeInTheDocument();
    expect(screen.getByText('Analyze Alternative Routes')).toBeInTheDocument();
  });

  it('clicking a preset corridor updates origin and destination inputs', () => {
    const handleSubmit = vi.fn();
    render(<RouteForm onSubmit={handleSubmit} isLoading={false} />);

    // Click Dallas -> Denver preset
    const presetBtn = screen.getByText('Dallas → Denver');
    fireEvent.click(presetBtn);

    const originInput = screen.getByPlaceholderText(/Chicago, IL/i) as HTMLInputElement;
    const destInput = screen.getByPlaceholderText(/Detroit, MI/i) as HTMLInputElement;

    expect(originInput.value).toBe('Dallas, TX');
    expect(destInput.value).toBe('Denver, CO');
  });

  it('prevents submission when origin and destination are identical', () => {
    const handleSubmit = vi.fn();
    render(<RouteForm onSubmit={handleSubmit} isLoading={false} />);

    const originInput = screen.getByPlaceholderText(/Chicago, IL/i);
    const destInput = screen.getByPlaceholderText(/Detroit, MI/i);
    const submitBtn = screen.getByText('Analyze Alternative Routes');

    fireEvent.change(originInput, { target: { value: 'Chicago, IL' } });
    fireEvent.change(destInput, { target: { value: 'Chicago, IL' } });
    fireEvent.click(submitBtn);

    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/Origin and destination must be different cities/i)).toBeInTheDocument();
  });
  it('renders empty origin and destination fields by default with helpful placeholders', () => {
    const handleSubmit = vi.fn();
    render(<RouteForm onSubmit={handleSubmit} isLoading={false} />);

    const originInput = screen.getByPlaceholderText(/Enter origin city/i) as HTMLInputElement;
    const destInput = screen.getByPlaceholderText(/Enter destination city/i) as HTMLInputElement;

    expect(originInput.value).toBe('');
    expect(destInput.value).toBe('');
  });

  it('prevents submission when origin or destination is empty', () => {
    const handleSubmit = vi.fn();
    render(<RouteForm onSubmit={handleSubmit} isLoading={false} />);

    const submitBtn = screen.getByText('Analyze Alternative Routes');
    fireEvent.click(submitBtn);

    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/Please enter a valid trip origin/i)).toBeInTheDocument();
  });

  it('submits form payload including timezone_offset_minutes', () => {
    const handleSubmit = vi.fn();
    render(<RouteForm onSubmit={handleSubmit} isLoading={false} />);

    const originInput = screen.getByPlaceholderText(/Enter origin city/i);
    const destInput = screen.getByPlaceholderText(/Enter destination city/i);
    fireEvent.change(originInput, { target: { value: 'Chicago, IL' } });
    fireEvent.change(destInput, { target: { value: 'Detroit, MI' } });

    const submitBtn = screen.getByText('Analyze Alternative Routes');
    fireEvent.click(submitBtn);

    expect(handleSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        origin: 'Chicago, IL',
        destination: 'Detroit, MI',
        load_weight_lb: 38000,
        sampling_interval_miles: 25,
        timezone_offset_minutes: expect.any(Number),
      })
    );
  });

  it('computes timezone_offset_minutes based on the selected departure date', () => {
    const handleSubmit = vi.fn();
    const { container } = render(<RouteForm onSubmit={handleSubmit} isLoading={false} />);

    const originInput = screen.getByPlaceholderText(/Enter origin city/i);
    const destInput = screen.getByPlaceholderText(/Enter destination city/i);
    fireEvent.change(originInput, { target: { value: 'Chicago, IL' } });
    fireEvent.change(destInput, { target: { value: 'Detroit, MI' } });

    const dateInput = container.querySelector('input[type="datetime-local"]') as HTMLInputElement;
    expect(dateInput).not.toBeNull();

    const testDeparture = '2026-07-15T08:00';
    fireEvent.change(dateInput, { target: { value: testDeparture } });

    const submitBtn = screen.getByText('Analyze Alternative Routes');
    fireEvent.click(submitBtn);

    const expectedOffset = new Date(testDeparture).getTimezoneOffset();
    expect(handleSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        origin: 'Chicago, IL',
        destination: 'Detroit, MI',
        departure_time: testDeparture,
        timezone_offset_minutes: expectedOffset,
      })
    );
  });

  it('submits correct timezone offset for departure dates across daylight-saving time transitions', () => {
    const handleSubmit = vi.fn();
    const { container } = render(<RouteForm onSubmit={handleSubmit} isLoading={false} />);

    const originInput = screen.getByPlaceholderText(/Enter origin city/i);
    const destInput = screen.getByPlaceholderText(/Enter destination city/i);
    fireEvent.change(originInput, { target: { value: 'Chicago, IL' } });
    fireEvent.change(destInput, { target: { value: 'Detroit, MI' } });

    const dateInput = container.querySelector('input[type="datetime-local"]') as HTMLInputElement;
    const submitBtn = screen.getByText('Analyze Alternative Routes');

    // 1. Summer date (July)
    const summerDate = '2026-07-15T12:00';
    fireEvent.change(dateInput, { target: { value: summerDate } });
    fireEvent.click(submitBtn);

    expect(handleSubmit).toHaveBeenLastCalledWith(
      expect.objectContaining({
        departure_time: summerDate,
        timezone_offset_minutes: new Date(summerDate).getTimezoneOffset(),
      })
    );

    // 2. Winter date (November)
    const winterDate = '2026-11-24T12:00';
    fireEvent.change(dateInput, { target: { value: winterDate } });
    fireEvent.click(submitBtn);

    expect(handleSubmit).toHaveBeenLastCalledWith(
      expect.objectContaining({
        departure_time: winterDate,
        timezone_offset_minutes: new Date(winterDate).getTimezoneOffset(),
      })
    );
  });
});
