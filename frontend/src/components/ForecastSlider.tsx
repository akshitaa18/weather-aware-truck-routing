import React, { useEffect, useState } from 'react';
import { Play, Pause, RotateCcw, Clock, FastForward, Rewind } from 'lucide-react';

interface ForecastSliderProps {
  departureTimeIso: string;
  forecastOffsetHours: number;
  onOffsetChange: (offset: number) => void;
}

export const ForecastSlider: React.FC<ForecastSliderProps> = ({
  departureTimeIso,
  forecastOffsetHours,
  onOffsetChange,
}) => {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Play animation loop
  useEffect(() => {
    let interval: any = null;
    if (isPlaying) {
      interval = setInterval(() => {
        if (forecastOffsetHours >= 48) {
          setIsPlaying(false);
        } else {
          onOffsetChange(forecastOffsetHours + 1);
        }
      }, 900); // 900ms per step
    }
    return () => clearInterval(interval);
  }, [isPlaying, forecastOffsetHours, onOffsetChange]);

  // Compute selected forecast datetime
  const calculateDisplayTime = () => {
    try {
      const depDate = new Date(departureTimeIso);
      const targetDate = new Date(depDate.getTime() + forecastOffsetHours * 3600 * 1000);
      return targetDate.toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return `+${forecastOffsetHours} hrs`;
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-sm space-y-3">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
            <Clock className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Weather Forecast Corridor Slider (0 to 48 Hours)
            </h4>
            <p className="text-[11px] text-slate-500">
              Explore how weather hazards, crosswinds, and precipitation evolve along the trip corridor over time.
            </p>
          </div>
        </div>

        {/* Selected Hour Pill */}
        <div className="flex items-center gap-2 bg-slate-900 text-white px-3 py-1.5 rounded-lg shadow-xs">
          <span className="text-xs font-bold text-blue-400">
            {forecastOffsetHours === 0 ? 'Departure Time' : `+${forecastOffsetHours}h Forecast`}
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-xs font-medium text-slate-200">{calculateDisplayTime()}</span>
        </div>
      </div>

      {/* Slider Controls */}
      <div className="flex items-center gap-3">
        {/* Play / Pause button */}
        <button
          type="button"
          onClick={() => setIsPlaying(!isPlaying)}
          className={`h-9 w-9 rounded-lg flex items-center justify-center transition-all ${
            isPlaying
              ? 'bg-amber-600 hover:bg-amber-700 text-white shadow-xs'
              : 'bg-blue-600 hover:bg-blue-700 text-white shadow-xs'
          }`}
          title={isPlaying ? 'Pause timeline animation' : 'Play timeline animation'}
        >
          {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4 ml-0.5" />}
        </button>

        {/* Step back */}
        <button
          type="button"
          onClick={() => onOffsetChange(Math.max(0, forecastOffsetHours - 1))}
          disabled={forecastOffsetHours <= 0}
          className="h-8 w-8 rounded-lg bg-slate-100 hover:bg-slate-200 disabled:opacity-40 text-slate-700 flex items-center justify-center transition-all"
          title="Previous hour"
        >
          <Rewind className="h-3.5 w-3.5" />
        </button>

        {/* Range Slider */}
        <div className="flex-1 relative flex items-center">
          <input
            type="range"
            min={0}
            max={48}
            step={1}
            value={forecastOffsetHours}
            onChange={(e) => {
              setIsPlaying(false);
              onOffsetChange(Number(e.target.value));
            }}
            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
          />
        </div>

        {/* Step forward */}
        <button
          type="button"
          onClick={() => onOffsetChange(Math.min(48, forecastOffsetHours + 1))}
          disabled={forecastOffsetHours >= 48}
          className="h-8 w-8 rounded-lg bg-slate-100 hover:bg-slate-200 disabled:opacity-40 text-slate-700 flex items-center justify-center transition-all"
          title="Next hour"
        >
          <FastForward className="h-3.5 w-3.5" />
        </button>

        {/* Reset to 0 */}
        <button
          type="button"
          onClick={() => {
            setIsPlaying(false);
            onOffsetChange(0);
          }}
          className="h-8 px-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 text-[11px] font-semibold flex items-center gap-1 transition-all"
          title="Reset to departure"
        >
          <RotateCcw className="h-3 w-3" />
          <span>Reset</span>
        </button>
      </div>

      {/* Tick Marks / Time Bar */}
      <div className="flex justify-between text-[10px] text-slate-400 font-medium px-1">
        <span>0h (Departure)</span>
        <span>+12h</span>
        <span>+24h (Day 1)</span>
        <span>+36h</span>
        <span>+48h (Day 2)</span>
      </div>
    </div>
  );
};
