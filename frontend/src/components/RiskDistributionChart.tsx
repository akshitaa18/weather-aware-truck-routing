import React from 'react';
import type { RouteData } from '../types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';
import { AlertOctagon } from 'lucide-react';

interface RiskDistributionChartProps {
  routes: RouteData[];
}

export const RiskDistributionChart: React.FC<RiskDistributionChartProps> = ({ routes }) => {
  if (!routes || routes.length === 0) return null;

  const data = routes.map((r, idx) => {
    // Mutually exclusive stacked bar calculations:
    // A segment classified as Data Unavailable due to incomplete weather contributes to
    // 'Data Unavailable (mi)'. It must NOT also increase the stacked 'No Travel (mi)' category,
    // ensuring the stacked bar accurately represents 100% of the corridor without double-counting.
    const verifiedNoTravel = typeof r.metrics.verified_no_travel_miles === 'number'
      ? r.metrics.verified_no_travel_miles
      : (r.metrics.unknown_risk_miles > 0
          ? Math.max(0, r.metrics.no_travel_miles - (r.metrics.partial_data_hazard_miles ?? r.metrics.unknown_risk_miles))
          : r.metrics.no_travel_miles);

    const detectedNoTravel = r.metrics.no_travel_miles || 0;
    const unverifiedNoTravel = Math.max(0, detectedNoTravel - verifiedNoTravel);

    return {
      name: `Route ${idx + 1}: ${r.name.length > 20 ? r.name.slice(0, 18) + '...' : r.name}`,
      'Low Risk (mi)': r.metrics.low_risk_miles,
      'Moderate Risk (mi)': r.metrics.moderate_risk_miles,
      'High Risk (mi)': r.metrics.high_risk_miles,
      'Severe Risk (mi)': r.metrics.severe_risk_miles,
      'No Travel (mi)': verifiedNoTravel,
      'Data Unavailable (mi)': r.metrics.unknown_risk_miles || 0,
      detectedNoTravel,
      unverifiedNoTravel,
    };
  });

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Corridor Risk Exposure Breakdown (Miles)
          </h3>
          <p className="text-xs text-slate-500">
            Comparative stacked analysis of mutually exclusive corridor hazard segments and unforecasted zones.
          </p>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 10, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
            <XAxis type="number" unit=" mi" tick={{ fontSize: 11, fill: '#64748b' }} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#1e293b', fontWeight: 600 }} width={140} />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload || !payload.length) return null;
                const row = payload[0]?.payload;
                return (
                  <div className="bg-slate-900 text-white rounded-lg p-3 text-xs shadow-xl border border-slate-700 space-y-1.5 min-w-[200px]">
                    <div className="font-bold text-slate-100 border-b border-slate-800 pb-1">{label}</div>
                    {payload.map((entry: any, i: number) => {
                      const val = Number(entry.value || 0);
                      if (val <= 0) return null;
                      return (
                        <div key={i} className="flex items-center justify-between gap-4">
                          <span className="flex items-center gap-1.5 text-slate-300">
                            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
                            {entry.name}
                          </span>
                          <span className="font-semibold text-slate-100">{val.toFixed(1)} mi</span>
                        </div>
                      );
                    })}
                    {row && row.unverifiedNoTravel > 0 && (
                      <div className="mt-2 pt-1.5 border-t border-rose-900/60 text-rose-300 font-semibold flex items-center gap-1">
                        <span>⚠️ Active No-Travel hazard detected: {row.detectedNoTravel.toFixed(1)} mi ({row.unverifiedNoTravel.toFixed(1)} mi on unforecasted corridor)</span>
                      </div>
                    )}
                  </div>
                );
              }}
            />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
            <Bar dataKey="Low Risk (mi)" stackId="a" fill="#10b981" />
            <Bar dataKey="Moderate Risk (mi)" stackId="a" fill="#f59e0b" />
            <Bar dataKey="High Risk (mi)" stackId="a" fill="#f97316" />
            <Bar dataKey="Severe Risk (mi)" stackId="a" fill="#ef4444" />
            <Bar dataKey="No Travel (mi)" stackId="a" fill="#881337" />
            <Bar dataKey="Data Unavailable (mi)" stackId="a" fill="#64748b" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Annotations for detected No-Travel hazards */}
      {routes.some((r) => r.metrics.no_travel_miles > 0) && (
        <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-2 text-xs">
          {routes.map((r, idx) => {
            if (!r.metrics.no_travel_miles || r.metrics.no_travel_miles <= 0) return null;
            const verifiedNT = r.metrics.verified_no_travel_miles ?? 0;
            const hasUnverified = r.metrics.no_travel_miles > verifiedNT;
            return (
              <div
                key={r.id}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-[11px] font-semibold"
              >
                <AlertOctagon className="h-3.5 w-3.5 text-rose-600 shrink-0" />
                <span>
                  Route {idx + 1}: {r.metrics.no_travel_miles} mi active No-Travel hazard
                  {hasUnverified ? ' (on unforecasted corridor)' : ''}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

