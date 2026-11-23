import React, { useState } from 'react';
import { Info, ChevronDown, ChevronUp, Wind, CloudRain, Snowflake, Weight } from 'lucide-react';

export const RiskLegend: React.FC = () => {
  const [isOpen, setIsOpen] = useState<boolean>(false);

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-md bg-blue-50 text-blue-600">
            <Info className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Safety Classification & Weather Risk Rules Reference
            </h4>
            <p className="text-[11px] text-slate-500">
              Deterministic threshold criteria for wind, precipitation, snowfall, and gross vehicle load weight.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Quick pills */}
          <div className="hidden sm:flex items-center gap-1.5 text-[10px] font-bold">
            <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">Low</span>
            <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">Moderate</span>
            <span className="px-2 py-0.5 rounded-full bg-orange-100 text-orange-800">High</span>
            <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-800">Severe</span>
            <span className="px-2 py-0.5 rounded-full bg-rose-900 text-white">No Travel</span>
            <span className="px-2 py-0.5 rounded-full bg-slate-200 text-slate-800">Data Unavailable</span>
          </div>

          <div className="text-slate-400">
            {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </div>
        </div>
      </button>

      {isOpen && (
        <div className="p-5 border-t border-slate-100 bg-slate-50/50 space-y-4 text-xs">
          {/* Grid of Weather Rules */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Wind */}
            <div className="bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-2xs space-y-2">
              <div className="flex items-center gap-1.5 font-bold text-slate-900 pb-1 border-b border-slate-100">
                <Wind className="h-3.5 w-3.5 text-blue-600" />
                <span>Wind Speed (mph)</span>
              </div>
              <ul className="space-y-1 text-[11px]">
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">&lt; 25 mph</span>
                  <span className="font-bold text-emerald-700">Low</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">25–34 mph</span>
                  <span className="font-bold text-amber-700">Moderate</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">35–44 mph</span>
                  <span className="font-bold text-orange-700">High</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">45–54 mph</span>
                  <span className="font-bold text-red-700">Severe</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">&ge; 55 mph</span>
                  <span className="font-bold text-rose-900">No Travel</span>
                </li>
              </ul>
            </div>

            {/* Rain */}
            <div className="bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-2xs space-y-2">
              <div className="flex items-center gap-1.5 font-bold text-slate-900 pb-1 border-b border-slate-100">
                <CloudRain className="h-3.5 w-3.5 text-blue-600" />
                <span>Rain Intensity (in/hr)</span>
              </div>
              <ul className="space-y-1 text-[11px]">
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">&lt; 0.10 in/hr</span>
                  <span className="font-bold text-emerald-700">Low</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">0.10–0.25 in/hr</span>
                  <span className="font-bold text-amber-700">Moderate</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">0.25–0.50 in/hr</span>
                  <span className="font-bold text-orange-700">High</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">0.50–1.00 in/hr</span>
                  <span className="font-bold text-red-700">Severe</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">&gt; 1.00 in/hr</span>
                  <span className="font-bold text-rose-900">No Travel</span>
                </li>
              </ul>
            </div>

            {/* Snow */}
            <div className="bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-2xs space-y-2">
              <div className="flex items-center gap-1.5 font-bold text-slate-900 pb-1 border-b border-slate-100">
                <Snowflake className="h-3.5 w-3.5 text-blue-600" />
                <span>Snow Intensity (in/hr)</span>
              </div>
              <ul className="space-y-1 text-[11px]">
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">&lt; 0.5 in/hr</span>
                  <span className="font-bold text-emerald-700">Low</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">0.5–1.0 in/hr</span>
                  <span className="font-bold text-amber-700">Moderate</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">1.0–2.0 in/hr</span>
                  <span className="font-bold text-orange-700">High</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">2.0–3.0 in/hr</span>
                  <span className="font-bold text-red-700">Severe</span>
                </li>
                <li className="flex justify-between py-0.5">
                  <span className="text-slate-600">&gt; 3.0 in/hr</span>
                  <span className="font-bold text-rose-900">No Travel</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Load Rules Box */}
          <div className="bg-blue-50/70 p-3.5 rounded-xl border border-blue-200 text-blue-950 space-y-1.5">
            <div className="flex items-center gap-1.5 font-bold">
              <Weight className="h-3.5 w-3.5 text-blue-700" />
              <span>Load-Based Weight Rules (Applied at every checkpoint)</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] font-medium pt-1">
              <div className="p-2 bg-white rounded-lg border border-blue-100">
                <span className="font-bold text-rose-900 block">Rule 1 (Any Weight)</span>
                Wind &ge; 55 mph &rarr; Mandatory No Travel.
              </div>
              <div className="p-2 bg-white rounded-lg border border-blue-100">
                <span className="font-bold text-rose-900 block">Rule 2 (&gt; 30,000 lb)</span>
                Wind 45–54 mph &amp; Load &gt; 30k lb &rarr; No Travel.
              </div>
              <div className="p-2 bg-white rounded-lg border border-blue-100">
                <span className="font-bold text-red-700 block">Rule 3 (&gt; 40,000 lb)</span>
                Wind 35–44 mph &amp; Load &gt; 40k lb &rarr; Severe.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
