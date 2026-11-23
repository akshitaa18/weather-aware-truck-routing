import type { AnalyzeRoutesRequest, AnalyzeRoutesResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function analyzeRoutes(request: AnalyzeRoutesRequest): Promise<AnalyzeRoutesResponse> {
  const url = `${API_BASE_URL}/api/routes/analyze/`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(request),
  });

  const data = await response.json();

  if (!response.ok) {
    let errorMsg = data.message || 'Failed to analyze routes. Please check your inputs and try again.';
    if (data.errors) {
      const details = Object.entries(data.errors)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join('; ');
      errorMsg = `${errorMsg} (${details})`;
    }
    throw new Error(errorMsg);
  }

  return data as AnalyzeRoutesResponse;
}

export async function checkBackendHealth(): Promise<{ status: string; routing_engines?: string[] }> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/routes/health/`, { method: 'GET' });
    if (res.ok) {
      return await res.json();
    }
    return { status: 'degraded' };
  } catch {
    return { status: 'offline' };
  }
}

export async function checkWeatherHealth(): Promise<{ status: string; response_time_ms?: number }> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/weather/health/`, { method: 'GET' });
    if (res.ok) {
      return await res.json();
    }
    return { status: 'degraded' };
  } catch {
    return { status: 'offline' };
  }
}
