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
});
