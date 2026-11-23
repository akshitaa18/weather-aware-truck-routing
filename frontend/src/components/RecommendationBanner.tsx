import React from 'react';
import { ShieldCheck, XCircle, Award, ArrowRight } from 'lucide-react';
import type { RecommendationResult, RouteData } from '../types';

interface RecommendationBannerProps {
  recommendation: RecommendationResult;
  routes: RouteData[];
  onSelectRoute: (routeId: string) => void;
}

export const RecommendationBanner: React.FC<RecommendationBannerProps> = ({
  recommendation,
  routes,
  onSelectRoute,
}) => {
  const { is_any_safe, explanation, recommended_route_id } = recommendation;
  const recommendedRoute = routes.find((r) => r.id === recommended_route_id);

  if (!is_any_safe || !recommendedRoute) {
    return (
      <div className="bg-rose-50 border-2 border-rose-400 rounded-2xl p-5 shadow-sm text-rose-950">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-rose-200/80 rounded-xl text-rose-800 shrink-0">
            <XCircle className="h-6 w-6" />
          </div>
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-900 text-white">
                No Safe Route Available
              </span>
              <span className="text-xs font-semibold text-rose-800">Dispatch Warning</span>
            </div>
            <h3 className="text-base font-bold text-rose-950">Active Hazard / No-Travel Weather Detected</h3>
            <p className="text-sm text-rose-900/90 leading-relaxed">{explanation}</p>
          </div>
        </div>
      </div>
    );
  }

  const metrics = recommendedRoute.metrics;

  return (
    <div className="bg-gradient-to-r from-emerald-50 via-teal-50/50 to-blue-50/40 border border-emerald-200 rounded-2xl p-5 md:p-6 shadow-sm transition-all">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Badge & Title */}
        <div className="space-y-2 max-w-2xl">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-600 text-white text-xs font-bold tracking-wide shadow-sm">
              <Award className="h-3.5 w-3.5" />
              <span>RECOMMENDED ROUTE</span>
            </div>
            <div className="flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>Safe for Travel</span>
            </div>
            <span className="text-xs text-slate-500 font-medium">
              Provider: {recommendedRoute.provider}
            </span>
          </div>

          <h3 className="text-lg md:text-xl font-bold text-slate-900 tracking-tight">
            {recommendedRoute.name}
          </h3>

          <p className="text-xs md:text-sm text-slate-700 leading-relaxed font-medium">
            {explanation}
          </p>
        </div>

        {/* Right: Key Safety Metrics & Action */}
        <div className="flex flex-wrap items-center gap-3 bg-white/80 backdrop-blur-sm p-3.5 rounded-xl border border-emerald-100/80 shadow-xs">
          <div className="px-3 py-1 text-center border-r border-slate-200">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Distance</div>
            <div className="text-base font-bold text-slate-900">{recommendedRoute.distance_miles} mi</div>
          </div>

          <div className="px-3 py-1 text-center border-r border-slate-200">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Duration</div>
            <div className="text-base font-bold text-slate-900">{recommendedRoute.duration_formatted}</div>
          </div>

          <div className="px-3 py-1 text-center border-r border-slate-200">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Severe Miles</div>
            <div className={`text-base font-bold ${metrics.severe_risk_miles > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
              {metrics.severe_risk_miles} mi
            </div>
          </div>

          <div className="px-3 py-1 text-center border-r border-slate-200">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">High Miles</div>
            <div className={`text-base font-bold ${metrics.high_risk_miles > 0 ? 'text-orange-600' : 'text-emerald-600'}`}>
              {metrics.high_risk_miles} mi
            </div>
          </div>

          <div className="px-3 py-1 text-center">
            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Risk Score</div>
            <div className="text-base font-bold text-blue-700">{metrics.average_risk_score} / 5.0</div>
          </div>

          <button
            onClick={() => onSelectRoute(recommendedRoute.id)}
            className="w-full sm:w-auto mt-2 sm:mt-0 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg shadow-xs flex items-center justify-center gap-1.5 transition-all"
          >
            <span>Focus on Map</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
