import React, { useState } from 'react';
import { Header } from '../components/Header';
import { RouteForm } from '../components/RouteForm';
import { RecommendationBanner } from '../components/RecommendationBanner';
import { RouteComparison } from '../components/RouteComparison';
import { RouteMap } from '../components/Map/RouteMap';
import { ForecastSlider } from '../components/ForecastSlider';
import { CheckpointTable } from '../components/CheckpointTable';
import { RiskDistributionChart } from '../components/RiskDistributionChart';
import { RiskLegend } from '../components/RiskLegend';
import { analyzeRoutes } from '../services/api';
import type { AnalyzeRoutesRequest, AnalyzeRoutesResponse } from '../types';
import { AlertCircle, RefreshCw, Navigation } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalyzeRoutesResponse | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);
  const [forecastOffsetHours, setForecastOffsetHours] = useState<number>(0);

  const handleAnalyze = async (req: AnalyzeRoutesRequest) => {
    if (isLoading) return; // Prevent duplicate requests
    setIsLoading(true);
    setError(null);
    try {
      const data = await analyzeRoutes(req);
      setAnalysisResult(data);
      const bestId = data.recommendation.recommended_route_id || data.routes[0]?.id || null;
      setSelectedRouteId(bestId);
      setForecastOffsetHours(0);
    } catch (err: any) {
      setError(err.message || 'An error occurred while analyzing routes.');
    } finally {
      setIsLoading(false);
    }
  };

  const activeRoute =
    analysisResult?.routes.find((r) => r.id === selectedRouteId) ||
    analysisResult?.routes[0] ||
    null;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Route Planning Form Panel */}
        <RouteForm onSubmit={handleAnalyze} isLoading={isLoading} />

        {/* Error Banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-xs text-red-800 flex items-start gap-3 shadow-xs">
            <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <span className="font-bold block text-sm">Route Analysis Error</span>
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700 font-bold text-xs"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Loading State Skeleton */}
        {isLoading && !analysisResult && (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center space-y-3 shadow-xs">
            <RefreshCw className="h-8 w-8 text-blue-600 animate-spin mx-auto" />
            <h3 className="text-base font-bold text-slate-800">
              Querying Routing Providers & Weather Satellites...
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Calculating 3 alternative driving corridors, interpolating checkpoint arrival times, and applying gross vehicle weight hazard rules.
            </p>
          </div>
        )}

        {/* Welcome Empty State */}
        {!analysisResult && !isLoading && !error && (
          <div className="bg-white rounded-2xl border border-slate-200 p-8 sm:p-12 text-center space-y-4 shadow-xs">
            <div className="inline-flex p-3 rounded-2xl bg-blue-50 text-blue-600 mb-1">
              <Navigation className="h-8 w-8" />
            </div>
            <h3 className="text-lg font-bold text-slate-800">
              Weather-Aware Corridor Planning Ready
            </h3>
            <p className="text-sm text-slate-500 max-w-lg mx-auto">
              Enter your trip origin and destination above, select truck load weight and departure time, then click <strong className="text-slate-700">"Analyze Alternative Routes"</strong>. The system will evaluate alternative road corridors against real-time Open-Meteo forecasts and truck rollover risk rules.
            </p>
            <div className="pt-2 flex flex-wrap justify-center gap-2 text-xs text-slate-500">
              <span className="px-3 py-1 rounded-full bg-slate-100 font-medium">3 Highway Alternatives</span>
              <span className="px-3 py-1 rounded-full bg-slate-100 font-medium">Gross Weight Rollover Rules</span>
              <span className="px-3 py-1 rounded-full bg-slate-100 font-medium">0–48h Forecast Timeline</span>
              <span className="px-3 py-1 rounded-full bg-slate-100 font-medium">Severe Miles Minimization</span>
            </div>
          </div>
        )}

        {/* Analysis Results Display */}
        {analysisResult && (
          <div className="space-y-6">
            {/* Recommended Route Hero Banner */}
            <RecommendationBanner
              recommendation={analysisResult.recommendation}
              routes={analysisResult.routes}
              onSelectRoute={setSelectedRouteId}
            />

            {/* Route Cards Comparison Section */}
            <RouteComparison
              routes={analysisResult.routes}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
            />

            {/* Forecast Timeline Slider */}
            <ForecastSlider
              departureTimeIso={analysisResult.inputs.departure_time}
              forecastOffsetHours={forecastOffsetHours}
              onOffsetChange={setForecastOffsetHours}
            />

            {/* Interactive Leaflet Map (Centerpiece) */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                  Interactive Route & Hazard Corridor Map
                </h3>
                <span className="text-xs text-slate-500">
                  Showing {activeRoute ? activeRoute.name : 'All Routes'}
                </span>
              </div>
              <RouteMap
                routes={analysisResult.routes}
                selectedRouteId={selectedRouteId}
                onSelectRoute={setSelectedRouteId}
                forecastOffsetHours={forecastOffsetHours}
              />
            </div>

            {/* Risk Distribution Chart & Legend */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <RiskDistributionChart routes={analysisResult.routes} />
              </div>
              <div className="lg:col-span-1">
                <RiskLegend />
              </div>
            </div>

            {/* Granular Checkpoint Table */}
            {activeRoute && (
              <CheckpointTable
                checkpoints={activeRoute.checkpoints}
                routeName={activeRoute.name}
              />
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 mt-12 py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Weather-Aware Truck Routing & Hazard Mitigation System</span>
          <span>Lexicographical Safety Priority • Real-Time Open-Meteo Satellites & OSRM Engine</span>
        </div>
      </footer>
    </div>
  );
};
