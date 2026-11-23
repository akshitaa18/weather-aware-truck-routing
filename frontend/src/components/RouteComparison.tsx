import React from 'react';
import type { RouteData } from '../types';
import { getRouteColor } from '../utils/colors';
import { AlertOctagon, Award, Check, AlertTriangle, AlertCircle } from 'lucide-react';

interface RouteComparisonProps {
  routes: RouteData[];
  selectedRouteId: string | null;
  onSelectRoute: (id: string) => void;
}

export const RouteComparison: React.FC<RouteComparisonProps> = ({
  routes,
  selectedRouteId,
  onSelectRoute,
}) => {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
          Alternative Route Profiles ({routes.length})
        </h2>
        <span className="text-xs text-slate-500">Select any route card to inspect on interactive map</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {routes.map((route, idx) => {
          const isSelected = route.id === selectedRouteId;
          const isRecommended = route.is_recommended;
          const isUnsafe = route.is_critically_unsafe;
          const palette = getRouteColor(route.id, idx);
          const metrics = route.metrics;
          const hasMissingData = route.has_missing_weather || (metrics.unknown_risk_miles && metrics.unknown_risk_miles > 0);

          return (
            <div
              key={route.id}
              onClick={() => onSelectRoute(route.id)}
              className={`relative bg-white rounded-xl p-4 cursor-pointer transition-all border ${
                isSelected
                  ? 'border-blue-600 ring-2 ring-blue-500/20 shadow-md'
                  : 'border-slate-200/80 hover:border-slate-300 hover:shadow-xs'
              }`}
            >
              {/* Header Badges */}
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-1.5">
                  <span
                    className="h-3 w-3 rounded-full shrink-0 border border-white shadow-xs"
                    style={{ backgroundColor: palette.stroke }}
                  />
                  <span className="text-xs font-bold text-slate-900 truncate">
                    {route.name}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-1 justify-end">
                  {route.is_simulated && (
                    <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300">
                      <AlertTriangle className="h-3 w-3 text-amber-600" />
                      Simulated
                    </span>
                  )}
                  {hasMissingData && (
                    <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-200 text-slate-800 border border-slate-300">
                      <AlertCircle className="h-3 w-3 text-slate-600" />
                      Missing Data
                    </span>
                  )}
                  {isRecommended && (
                    <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                      <Award className="h-3 w-3" />
                      Best Choice
                    </span>
                  )}
                  {isUnsafe && (
                    <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-900 border border-rose-300">
                      <AlertOctagon className="h-3 w-3 text-rose-600" />
                      No Travel Hazard
                    </span>
                  )}
                </div>
              </div>

              {/* Distance & Duration */}
              <div className="flex items-center justify-between py-2 border-y border-slate-100 text-xs mb-3">
                <div>
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Distance</span>
                  <span className="font-bold text-slate-800 text-sm">{route.distance_miles} mi</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 block text-[10px] uppercase font-semibold">Est. Duration</span>
                  <span className="font-bold text-slate-800 text-sm">{route.duration_formatted}</span>
                </div>
              </div>

              {/* Risk Miles Grid */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs mb-3">
                <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                  <div className="text-[10px] font-semibold text-slate-500">Severe</div>
                  <div
                    className={`font-bold mt-0.5 ${
                      metrics.severe_risk_miles > 0 ? 'text-red-600' : 'text-slate-700'
                    }`}
                  >
                    {metrics.severe_risk_miles} mi
                  </div>
                </div>

                <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                  <div className="text-[10px] font-semibold text-slate-500">High Risk</div>
                  <div
                    className={`font-bold mt-0.5 ${
                      metrics.high_risk_miles > 0 ? 'text-orange-600' : 'text-slate-700'
                    }`}
                  >
                    {metrics.high_risk_miles} mi
                  </div>
                </div>

                <div className="bg-slate-50 p-2 rounded-lg border border-slate-100">
                  <div className="text-[10px] font-semibold text-slate-500">Avg Risk</div>
                  <div className="font-bold text-blue-700 mt-0.5">
                    {metrics.average_risk_score}
                  </div>
                </div>
              </div>

              {/* No-Travel Warning if present */}
              {metrics.no_travel_miles > 0 && (
                <div className="mb-2 p-1.5 rounded bg-rose-50 border border-rose-200 text-[11px] font-medium text-rose-800 flex items-center justify-center gap-1">
                  <AlertOctagon className="h-3 w-3 shrink-0" />
                  <span>{metrics.no_travel_miles} miles of No-Travel conditions</span>
                </div>
              )}

              {/* Simulated Geometry Warning if present */}
              {route.is_simulated && (
                <div className="mb-2 p-1.5 rounded bg-amber-50 border border-amber-200 text-[10px] font-medium text-amber-900 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3 shrink-0 text-amber-600" />
                  <span>Synthetic geometry — not a verified road corridor</span>
                </div>
              )}

              {/* Missing Data Warning if present */}
              {hasMissingData && (
                <div className="mb-2 p-1.5 rounded bg-slate-100 border border-slate-200 text-[10px] font-medium text-slate-700 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3 shrink-0 text-slate-500" />
                  <span>{metrics.unknown_risk_miles || 0} mi unforecasted; safety clearance withheld</span>
                </div>
              )}

              {/* Selection Indicator Button */}
              <div className="pt-1">
                <button
                  type="button"
                  className={`w-full py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                    isSelected
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {isSelected ? (
                    <>
                      <Check className="h-3.5 w-3.5" />
                      <span>Active on Map</span>
                    </>
                  ) : (
                    <span>View Route on Map</span>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
