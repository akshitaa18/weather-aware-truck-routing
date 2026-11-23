import React, { useEffect, useState } from 'react';
import { Truck, Activity } from 'lucide-react';
import { checkBackendHealth, checkWeatherHealth } from '../services/api';

export const Header: React.FC = () => {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'healthy' | 'offline'>('checking');
  const [weatherStatus, setWeatherStatus] = useState<'checking' | 'healthy' | 'offline'>('checking');
  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(
        now.toLocaleDateString('en-US', {
          weekday: 'short',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      );
    };
    updateTime();
    const timer = setInterval(updateTime, 60000);

    const checkHealth = async () => {
      const bRes = await checkBackendHealth();
      setBackendStatus(bRes.status === 'healthy' ? 'healthy' : 'offline');
      const wRes = await checkWeatherHealth();
      setWeatherStatus(wRes.status === 'healthy' ? 'healthy' : 'offline');
    };
    checkHealth();
    const healthInterval = setInterval(checkHealth, 30000);

    return () => {
      clearInterval(timer);
      clearInterval(healthInterval);
    };
  }, []);

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-blue-600 to-teal-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Truck className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">Weather-Aware Truck Routing</h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
                Fleet Pro
              </span>
            </div>
            <p className="text-xs text-slate-400">Intelligent Hazard Mitigation & Lexicographical Dispatch Safety</p>
          </div>
        </div>

        {/* System Status Indicators */}
        <div className="flex items-center gap-4 text-xs">
          {/* Time */}
          <div className="hidden md:flex items-center gap-1.5 text-slate-400 bg-slate-800/60 px-3 py-1.5 rounded-lg border border-slate-700/60">
            <Activity className="h-3.5 w-3.5 text-blue-400" />
            <span>{currentTime || 'Syncing clock...'}</span>
          </div>

          {/* Engine Status */}
          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
            <div className="flex items-center gap-1.5">
              <span
                className={`h-2 w-2 rounded-full ${
                  backendStatus === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                }`}
              />
              <span className="text-slate-300 font-medium">Routing Engine</span>
            </div>
            <span className="text-slate-600">|</span>
            <div className="flex items-center gap-1.5">
              <span
                className={`h-2 w-2 rounded-full ${
                  weatherStatus === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                }`}
              />
              <span className="text-slate-300 font-medium">Open-Meteo</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
