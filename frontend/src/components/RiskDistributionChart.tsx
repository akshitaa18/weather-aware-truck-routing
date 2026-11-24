import React from 'react';
import type { RouteData } from '../types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';

interface RiskDistributionChartProps {
  routes: RouteData[];
}

export const RiskDistributionChart: React.FC<RiskDistributionChartProps> = ({ routes }) => {
  if (!routes || routes.length === 0) return null;

  const data = routes.map((r, idx) => ({
    name: `Route ${idx + 1}: ${r.name.length > 20 ? r.name.slice(0, 18) + '...' : r.name}`,
    'Low Risk (mi)': r.metrics.low_risk_miles,
    'Moderate Risk (mi)': r.metrics.moderate_risk_miles,
    'High Risk (mi)': r.metrics.high_risk_miles,
    'Severe Risk (mi)': r.metrics.severe_risk_miles,
    'No Travel (mi)': r.metrics.no_travel_miles,
    'Data Unavailable (mi)': r.metrics.unknown_risk_miles || 0,
  }));

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 p-5 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Corridor Risk Exposure Breakdown (Miles)
          </h3>
          <p className="text-xs text-slate-500">
            Comparative stacked analysis of verified hazard exposure (Low, Moderate, High, Severe, No Travel) and unforecasted corridors (Data Unavailable).
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
              contentStyle={{
                backgroundColor: '#0f172a',
                color: '#ffffff',
                borderRadius: '8px',
                border: 'none',
                fontSize: '12px',
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
    </div>
  );
};
