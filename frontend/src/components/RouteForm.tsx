import React, { useState } from 'react';
import { MapPin, Calendar, Weight, Navigation, ArrowRight, Loader2 } from 'lucide-react';
import type { AnalyzeRoutesRequest, SamplingInterval } from '../types';

interface RouteFormProps {
  onSubmit: (request: AnalyzeRoutesRequest) => void;
  isLoading: boolean;
}

const PRESET_CORRIDORS = [
  { origin: 'Chicago, IL', dest: 'Detroit, MI', label: 'Midwest Highway (I-94)' },
  { origin: 'Chicago, IL', dest: 'New York, NY', label: 'Interstate Long-Haul (I-80)' },
  { origin: 'Dallas, TX', dest: 'Denver, CO', label: 'High Plains Corridor (US-287 / I-25)' },
  { origin: 'Atlanta, GA', dest: 'Miami, FL', label: 'Southeast Corridor (I-75)' },
];

const WEIGHT_PRESETS = [
  { label: 'Empty (15k lb)', weight: 15000 },
  { label: 'Standard (32k lb)', weight: 32000 },
  { label: 'Heavy Load (42k lb)', weight: 42000 },
  { label: 'Max Freight (55k lb)', weight: 55000 },
];

export const RouteForm: React.FC<RouteFormProps> = ({ onSubmit, isLoading }) => {
  const getInitialDateTime = () => {
    const now = new Date();
    now.setMinutes(0, 0, 0);
    now.setHours(now.getHours() + 1);
    const tzOffset = now.getTimezoneOffset() * 60000;
    return new Date(now.getTime() - tzOffset).toISOString().slice(0, 16);
  };

  const [origin, setOrigin] = useState<string>('Chicago, IL');
  const [destination, setDestination] = useState<string>('Detroit, MI');
  const [departureTime, setDepartureTime] = useState<string>(getInitialDateTime());
  const [loadWeight, setLoadWeight] = useState<number>(38000);
  const [samplingInterval, setSamplingInterval] = useState<SamplingInterval>(25);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const cleanOrigin = origin.trim();
    const cleanDest = destination.trim();

    if (!cleanOrigin) {
      setValidationError('Please enter a valid trip origin.');
      return;
    }
    if (!cleanDest) {
      setValidationError('Please enter a valid trip destination.');
      return;
    }
    if (cleanOrigin.toLowerCase() === cleanDest.toLowerCase()) {
      setValidationError('Origin and destination must be different cities.');
      return;
    }
    if (!departureTime) {
      setValidationError('Please choose a departure date and time.');
      return;
    }
    if (loadWeight < 0 || loadWeight > 120000) {
      setValidationError('Load weight must be between 0 and 120,000 lbs.');
      return;
    }

    onSubmit({
      origin: cleanOrigin,
      destination: cleanDest,
      departure_time: departureTime,
      load_weight_lb: Number(loadWeight),
      sampling_interval_miles: samplingInterval,
    });
  };

  const handleApplyPreset = (o: string, d: string) => {
    setOrigin(o);
    setDestination(d);
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200/80 p-5 md:p-6 transition-all">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-slate-100 gap-2">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Navigation className="h-4 w-4 text-blue-600" />
            Route Planning & Hazard Analysis
          </h2>
          <p className="text-xs text-slate-500">Configure journey parameters, cargo specifications, and sampling granularity.</p>
        </div>

        {/* Quick presets */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mr-1">Presets:</span>
          {PRESET_CORRIDORS.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplyPreset(p.origin, p.dest)}
              className="text-xs font-medium px-2.5 py-1 rounded-md bg-slate-100 hover:bg-blue-50 hover:text-blue-600 text-slate-600 transition-colors border border-slate-200/60"
            >
              {p.origin.split(',')[0]} → {p.dest.split(',')[0]}
            </button>
          ))}
        </div>
      </div>

      {validationError && (
        <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700 flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          <span>{validationError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Origin & Destination */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Origin Location
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-emerald-600">
                <MapPin className="h-4 w-4" />
              </div>
              <input
                type="text"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                placeholder="e.g. Chicago, IL or City, State"
                required
                className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50/50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-slate-900 transition-all font-medium"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Destination Location
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-red-600">
                <MapPin className="h-4 w-4" />
              </div>
              <input
                type="text"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                placeholder="e.g. Detroit, MI or City, State"
                required
                className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50/50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-slate-900 transition-all font-medium"
              />
            </div>
          </div>
        </div>

        {/* Departure Time & Load Weight */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Departure Date & Time
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-blue-600">
                <Calendar className="h-4 w-4" />
              </div>
              <input
                type="datetime-local"
                value={departureTime}
                onChange={(e) => setDepartureTime(e.target.value)}
                required
                className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50/50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-slate-900 transition-all font-medium"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                Truck Load Weight (lb)
              </label>
              <span className="text-[11px] font-semibold text-slate-500">
                {loadWeight > 40000 ? (
                  <span className="text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                    Rule 3 Active (&gt;40k lb)
                  </span>
                ) : loadWeight > 30000 ? (
                  <span className="text-blue-700 font-bold bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    Rule 2 Active (&gt;30k lb)
                  </span>
                ) : (
                  <span>Standard Weight</span>
                )}
              </span>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <Weight className="h-4 w-4" />
              </div>
              <input
                type="number"
                min="0"
                max="120000"
                step="500"
                value={loadWeight}
                onChange={(e) => setLoadWeight(Number(e.target.value))}
                required
                className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50/50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-slate-900 transition-all font-medium"
              />
            </div>

            {/* Quick Weight Selectors */}
            <div className="flex flex-wrap items-center gap-1.5 mt-2">
              {WEIGHT_PRESETS.map((wp, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setLoadWeight(wp.weight)}
                  className={`text-[11px] px-2 py-0.5 rounded-md border transition-all ${
                    loadWeight === wp.weight
                      ? 'bg-blue-600 text-white border-blue-600 font-semibold'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {wp.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Weather Sampling Interval */}
        <div>
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            Weather Sampling Granularity
          </label>
          <div className="grid grid-cols-3 gap-3">
            {[10, 25, 50].map((intVal) => (
              <label
                key={intVal}
                className={`relative flex flex-col items-center justify-center p-3 rounded-xl border cursor-pointer transition-all ${
                  samplingInterval === intVal
                    ? 'border-blue-600 bg-blue-50/60 ring-2 ring-blue-500/20 text-blue-900'
                    : 'border-slate-200 bg-white hover:border-slate-300 text-slate-700'
                }`}
              >
                <input
                  type="radio"
                  name="sampling_interval"
                  value={intVal}
                  checked={samplingInterval === intVal}
                  onChange={() => setSamplingInterval(intVal as SamplingInterval)}
                  className="sr-only"
                />
                <span className="text-sm font-bold">{intVal} Miles</span>
                <span className="text-[11px] text-slate-500 mt-0.5">
                  {intVal === 10 ? 'High Precision' : intVal === 25 ? 'Standard Sampling' : 'Long Corridor'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isLoading}
            className="w-full h-11 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold text-sm rounded-xl shadow-md shadow-blue-500/25 flex items-center justify-center gap-2 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Geocoding & Analyzing Weather Corridors...</span>
              </>
            ) : (
              <>
                <span>Analyze Alternative Routes</span>
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
