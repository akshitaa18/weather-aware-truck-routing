import React, { useState } from 'react';
import type { Checkpoint } from '../types';
import { RISK_COLORS } from '../utils/colors';
import { Search } from 'lucide-react';

interface CheckpointTableProps {
  checkpoints: Checkpoint[];
  routeName: string;
}

export const CheckpointTable: React.FC<CheckpointTableProps> = ({
  checkpoints,
  routeName,
}) => {
  const [filterRisk, setFilterRisk] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filtered = checkpoints.filter((cp) => {
    if (filterRisk !== 'ALL' && cp.final_risk !== filterRisk) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = cp.id.toLowerCase().includes(q);
      const matchDist = cp.distance_from_origin_miles.toString().includes(q);
      const matchReason = cp.risk_reason.toLowerCase().includes(q);
      return matchId || matchDist || matchReason;
    }
    return true;
  });

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-sm space-y-4">
      {/* Table Header with Search and Filter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Checkpoint Hazard Inspector ({checkpoints.length} Checkpoints)
          </h3>
          <p className="text-xs text-slate-500">
            Granular weather metrics and load rule evaluations for {routeName}.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="h-3.5 w-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search checkpoints..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 text-slate-800 font-medium"
            />
          </div>

          {/* Risk Level Filter Pill */}
          <select
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value)}
            className="text-xs font-semibold px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
          >
            <option value="ALL">All Risk Levels</option>
            <option value="No Travel">No Travel Only</option>
            <option value="Severe">Severe Only</option>
            <option value="High">High Risk Only</option>
            <option value="Moderate">Moderate Only</option>
            <option value="Low">Low Risk Only</option>
          </select>
        </div>
      </div>

      {/* Checkpoint Scrollable Table */}
      <div className="overflow-x-auto max-h-[380px] rounded-xl border border-slate-100">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50/90 text-slate-600 font-bold sticky top-0 z-10 border-b border-slate-200">
            <tr>
              <th className="py-2.5 px-3">Point</th>
              <th className="py-2.5 px-3">Distance</th>
              <th className="py-2.5 px-3">ETA</th>
              <th className="py-2.5 px-3">Wind (mph)</th>
              <th className="py-2.5 px-3">Rain (in/hr)</th>
              <th className="py-2.5 px-3">Snow (in/hr)</th>
              <th className="py-2.5 px-3">Load Rule Impact</th>
              <th className="py-2.5 px-3 text-right">Final Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-400">
                  No checkpoints match the selected filters.
                </td>
              </tr>
            ) : (
              filtered.map((cp) => {
                const riskConfig = RISK_COLORS[cp.final_risk] || RISK_COLORS.Low;
                return (
                  <tr key={cp.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-2 px-3 font-bold text-slate-800">
                      {cp.is_origin ? 'Origin' : cp.is_destination ? 'Destination' : cp.id}
                    </td>
                    <td className="py-2 px-3 text-slate-600 font-medium">
                      {cp.distance_from_origin_miles} mi
                    </td>
                    <td className="py-2 px-3 text-slate-700 font-medium">
                      {cp.arrival_time_formatted || cp.estimated_arrival_time}
                    </td>
                    <td className="py-2 px-3">
                      <span className="font-semibold text-slate-800">{cp.wind_speed_mph}</span>
                      <span className="text-[10px] text-slate-400 ml-1">({cp.wind_risk})</span>
                    </td>
                    <td className="py-2 px-3">
                      <span className="font-semibold text-slate-800">{cp.rain_intensity_in_hr}</span>
                      <span className="text-[10px] text-slate-400 ml-1">({cp.rain_risk})</span>
                    </td>
                    <td className="py-2 px-3">
                      <span className="font-semibold text-slate-800">{cp.snow_intensity_in_hr}</span>
                      <span className="text-[10px] text-slate-400 ml-1">({cp.snow_risk})</span>
                    </td>
                    <td className="py-2 px-3">
                      {cp.load_adjusted_risk !== 'None' ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-200">
                          Elevated: {cp.load_adjusted_risk}
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-400 font-normal">—</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <span
                        className={`inline-block text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${riskConfig.badge}`}
                      >
                        {cp.final_risk}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
