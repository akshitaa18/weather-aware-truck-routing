import React, { useEffect, useState } from 'react';
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  useMap,
} from 'react-leaflet';
import L from 'leaflet';
import type { RouteData, Checkpoint } from '../../types';
import { getRouteColor, RISK_COLORS } from '../../utils/colors';
import { Wind, CloudRain, Snowflake, Layers } from 'lucide-react';

interface RouteMapProps {
  routes: RouteData[];
  selectedRouteId: string | null;
  onSelectRoute: (id: string) => void;
  forecastOffsetHours: number;
}

const MapBoundsAdjuster: React.FC<{ routes: RouteData[]; selectedRouteId: string | null }> = ({
  routes,
  selectedRouteId,
}) => {
  const map = useMap();

  useEffect(() => {
    if (!routes || routes.length === 0) return;

    const activeRoute = routes.find((r) => r.id === selectedRouteId) || routes[0];
    if (activeRoute && activeRoute.coordinates.length > 0) {
      const bounds = L.latLngBounds(activeRoute.coordinates.map((c) => [c[0], c[1]]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 13 });
    }
  }, [map, routes, selectedRouteId]);

  return null;
};

const createCustomIcon = (colorHex: string, isPulse?: boolean) => {
  const html = `
    <div style="position: relative; display: flex; align-items: center; justify-content: center;">
      ${
        isPulse
          ? `<span style="position: absolute; width: 22px; height: 22px; border-radius: 50%; background-color: ${colorHex}; opacity: 0.35; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></span>`
          : ''
      }
      <div style="width: 14px; height: 14px; border-radius: 50%; background-color: ${colorHex}; border: 2.5px solid #ffffff; box-shadow: 0 1px 4px rgba(0,0,0,0.35);"></div>
    </div>
  `;
  return L.divIcon({
    html,
    className: 'custom-checkpoint-marker',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
    popupAnchor: [0, -10],
  });
};

const createTerminalIcon = (isOrigin: boolean) => {
  const bg = isOrigin ? '#10b981' : '#dc2626';
  const html = `
    <div style="background-color: ${bg}; color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2.5px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.4); font-weight: bold; font-size: 11px;">
      ${isOrigin ? 'A' : 'B'}
    </div>
  `;
  return L.divIcon({
    html,
    className: 'terminal-marker',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  });
};

export const RouteMap: React.FC<RouteMapProps> = ({
  routes,
  selectedRouteId,
  onSelectRoute,
  forecastOffsetHours,
}) => {
  const [showAllRoutes, setShowAllRoutes] = useState<boolean>(true);
  const [showCheckpoints, setShowCheckpoints] = useState<boolean>(true);
  const [showHeatSegments, setShowHeatSegments] = useState<boolean>(true);

  const activeRoute = routes.find((r) => r.id === selectedRouteId) || routes[0];

  if (!routes || routes.length === 0) {
    return (
      <div className="h-[480px] bg-slate-100 rounded-2xl flex items-center justify-center border border-slate-200 text-slate-400">
        <span>Awaiting route analysis data...</span>
      </div>
    );
  }

  const getCheckpointDynamicWeather = (cp: Checkpoint) => {
    if (forecastOffsetHours === 0 || !cp.hourly_timeline || cp.hourly_timeline.length === 0) {
      return {
        wind: cp.wind_speed_mph,
        rain: cp.rain_intensity_in_hr,
        snow: cp.snow_intensity_in_hr,
        risk: cp.final_risk,
      };
    }
    const offsetIdx = Math.min(forecastOffsetHours, cp.hourly_timeline.length - 1);
    const entry = cp.hourly_timeline[offsetIdx];
    return {
      wind: entry.wind_speed_mph,
      rain: entry.rain_intensity_in_hr,
      snow: entry.snow_intensity_in_hr,
      risk: cp.final_risk,
    };
  };

  return (
    <div className="relative w-full h-[520px] rounded-2xl overflow-hidden border border-slate-200/90 shadow-md">
      {/* Map Controls Floating Header */}
      <div className="absolute top-3 left-3 z-[1000] flex flex-wrap items-center gap-2 bg-white/95 backdrop-blur-md px-3 py-2 rounded-xl border border-slate-200 shadow-md text-xs">
        <div className="flex items-center gap-1.5 font-bold text-slate-800 pr-2 border-r border-slate-200">
          <Layers className="h-3.5 w-3.5 text-blue-600" />
          <span>Map Controls</span>
        </div>

        <button
          type="button"
          onClick={() => setShowAllRoutes(!showAllRoutes)}
          className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
            showAllRoutes
              ? 'bg-blue-50 text-blue-700 border border-blue-200'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          {showAllRoutes ? 'All 3 Routes Visible' : 'Focused Route Only'}
        </button>

        <button
          type="button"
          onClick={() => setShowCheckpoints(!showCheckpoints)}
          className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
            showCheckpoints
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          Checkpoints ({showCheckpoints ? 'ON' : 'OFF'})
        </button>

        <button
          type="button"
          onClick={() => setShowHeatSegments(!showHeatSegments)}
          className={`px-2.5 py-1 rounded-md font-semibold transition-all ${
            showHeatSegments
              ? 'bg-amber-50 text-amber-700 border border-amber-200'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          Risk Corridor Heatmap ({showHeatSegments ? 'ON' : 'OFF'})
        </button>
      </div>

      {/* Route Quick Switcher Pills Floating at Top Right */}
      <div className="absolute top-3 right-3 z-[1000] hidden sm:flex items-center gap-1.5 bg-white/95 backdrop-blur-md p-1.5 rounded-xl border border-slate-200 shadow-md text-xs">
        {routes.map((r, idx) => {
          const isSelected = r.id === (selectedRouteId || routes[0].id);
          const color = getRouteColor(r.id, idx);
          return (
            <button
              key={r.id}
              onClick={() => onSelectRoute(r.id)}
              className={`px-2.5 py-1 rounded-lg font-bold flex items-center gap-1.5 transition-all ${
                isSelected
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color.stroke }} />
              <span>Route {idx + 1}</span>
            </button>
          );
        })}
      </div>

      <MapContainer
        center={activeRoute.coordinates[0] || [39.8283, -98.5795]}
        zoom={6}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapBoundsAdjuster routes={routes} selectedRouteId={selectedRouteId} />

        {/* 1. Draw Route Polylines */}
        {routes.map((route, idx) => {
          const isSelected = route.id === (selectedRouteId || routes[0].id);
          if (!showAllRoutes && !isSelected) return null;

          const color = getRouteColor(route.id, idx);

          return (
            <React.Fragment key={route.id}>
              {isSelected && (
                <Polyline
                  positions={route.coordinates}
                  pathOptions={{
                    color: color.glow,
                    weight: 10,
                    opacity: 0.6,
                    lineCap: 'round',
                  }}
                />
              )}
              <Polyline
                positions={route.coordinates}
                pathOptions={{
                  color: color.stroke,
                  weight: isSelected ? 5 : 3.5,
                  opacity: isSelected ? 0.95 : 0.45,
                  dashArray: isSelected ? undefined : '5, 5',
                }}
                eventHandlers={{
                  click: () => onSelectRoute(route.id),
                }}
              />
            </React.Fragment>
          );
        })}

        {/* 2. Weather Heatmap / Risk Segments along active route */}
        {showHeatSegments &&
          activeRoute.metrics.segments &&
          activeRoute.metrics.segments.map((seg, sIdx) => {
            const riskConfig = RISK_COLORS[seg.risk_level] || RISK_COLORS.Low;
            return (
              <Polyline
                key={`heat_seg_${sIdx}`}
                positions={[
                  [seg.start_lat, seg.start_lon],
                  [seg.end_lat, seg.end_lon],
                ]}
                pathOptions={{
                  color: riskConfig.hex,
                  weight: 7,
                  opacity: 0.85,
                  lineCap: 'round',
                }}
              />
            );
          })}

        {/* 3. Terminal Markers (Origin & Destination) */}
        {activeRoute.coordinates.length > 0 && (
          <>
            <Marker
              position={activeRoute.coordinates[0]}
              icon={createTerminalIcon(true)}
            >
              <Popup>
                <div className="text-xs p-1">
                  <div className="font-bold text-emerald-800">Trip Origin</div>
                  <div className="text-slate-700 font-medium">{activeRoute.origin_name}</div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    Coords: {activeRoute.coordinates[0][0]}, {activeRoute.coordinates[0][1]}
                  </div>
                </div>
              </Popup>
            </Marker>

            <Marker
              position={activeRoute.coordinates[activeRoute.coordinates.length - 1]}
              icon={createTerminalIcon(false)}
            >
              <Popup>
                <div className="text-xs p-1">
                  <div className="font-bold text-red-800">Trip Destination</div>
                  <div className="text-slate-700 font-medium">{activeRoute.destination_name}</div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    Distance: {activeRoute.distance_miles} miles | Duration: {activeRoute.duration_formatted}
                  </div>
                </div>
              </Popup>
            </Marker>
          </>
        )}

        {/* 4. Checkpoints along Active Route */}
        {showCheckpoints &&
          activeRoute.checkpoints &&
          activeRoute.checkpoints.map((cp) => {
            const dynamic = getCheckpointDynamicWeather(cp);
            const riskConfig = RISK_COLORS[dynamic.risk] || RISK_COLORS.Low;
            const isHazard = dynamic.risk === 'Severe' || dynamic.risk === 'No Travel';

            return (
              <Marker
                key={cp.id}
                position={[cp.latitude, cp.longitude]}
                icon={createCustomIcon(riskConfig.hex, isHazard)}
              >
                <Popup>
                  <div className="p-1 max-w-[240px] text-xs space-y-2">
                    {/* Header */}
                    <div className="flex items-center justify-between pb-1.5 border-b border-slate-100">
                      <div>
                        <span className="font-bold text-slate-900">
                          {cp.is_origin ? 'Origin Point' : cp.is_destination ? 'Destination Point' : `Checkpoint ${cp.checkpoint_index}`}
                        </span>
                        <div className="text-[10px] text-slate-500">
                          {cp.distance_from_origin_miles} miles from origin
                        </div>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${riskConfig.badge}`}>
                        {dynamic.risk}
                      </span>
                    </div>

                    {/* ETA */}
                    <div className="bg-slate-50 p-1.5 rounded-lg border border-slate-100">
                      <span className="text-[10px] text-slate-400 font-medium block">ESTIMATED ARRIVAL (ETA)</span>
                      <span className="font-bold text-slate-800">{cp.arrival_time_formatted || cp.estimated_arrival_time}</span>
                    </div>

                    {/* Weather Measurements */}
                    <div className="grid grid-cols-3 gap-1.5 text-center">
                      <div className="bg-slate-50 p-1 rounded-md border border-slate-100">
                        <div className="text-[9px] text-slate-400 font-semibold flex items-center justify-center gap-0.5">
                          <Wind className="h-2.5 w-2.5" />
                          <span>WIND</span>
                        </div>
                        <div className="font-bold text-slate-800 mt-0.5">{dynamic.wind} mph</div>
                        <div className="text-[9px] text-slate-500">{cp.wind_risk}</div>
                      </div>

                      <div className="bg-slate-50 p-1 rounded-md border border-slate-100">
                        <div className="text-[9px] text-slate-400 font-semibold flex items-center justify-center gap-0.5">
                          <CloudRain className="h-2.5 w-2.5" />
                          <span>RAIN</span>
                        </div>
                        <div className="font-bold text-slate-800 mt-0.5">{dynamic.rain} in/h</div>
                        <div className="text-[9px] text-slate-500">{cp.rain_risk}</div>
                      </div>

                      <div className="bg-slate-50 p-1 rounded-md border border-slate-100">
                        <div className="text-[9px] text-slate-400 font-semibold flex items-center justify-center gap-0.5">
                          <Snowflake className="h-2.5 w-2.5" />
                          <span>SNOW</span>
                        </div>
                        <div className="font-bold text-slate-800 mt-0.5">{dynamic.snow} in/h</div>
                        <div className="text-[9px] text-slate-500">{cp.snow_risk}</div>
                      </div>
                    </div>

                    {/* Load Rule & Reason */}
                    {cp.load_adjusted_risk !== 'None' && (
                      <div className="text-[10px] p-1.5 rounded bg-amber-50 text-amber-900 border border-amber-200">
                        <span className="font-bold">Load Rule Active:</span> Elevated to {cp.load_adjusted_risk}
                      </div>
                    )}

                    {cp.risk_reason && (
                      <div className="text-[10px] text-slate-600 bg-slate-50 p-1.5 rounded border border-slate-100 italic">
                        {cp.risk_reason}
                      </div>
                    )}
                  </div>
                </Popup>
              </Marker>
            );
          })}
      </MapContainer>
    </div>
  );
};
