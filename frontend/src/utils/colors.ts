import type { RiskLevel } from '../types';

export const RISK_COLORS: Record<RiskLevel, { bg: string; text: string; border: string; hex: string; badge: string }> = {
  'Low': {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    hex: '#10b981',
    badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  },
  'Moderate': {
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    hex: '#f59e0b',
    badge: 'bg-amber-100 text-amber-800 border-amber-300',
  },
  'High': {
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    border: 'border-orange-200',
    hex: '#f97316',
    badge: 'bg-orange-100 text-orange-800 border-orange-300',
  },
  'Severe': {
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-200',
    hex: '#ef4444',
    badge: 'bg-red-100 text-red-800 border-red-300',
  },
  'No Travel': {
    bg: 'bg-rose-100',
    text: 'text-rose-950',
    border: 'border-rose-400',
    hex: '#881337',
    badge: 'bg-rose-900 text-white border-rose-950 font-bold',
  },
  'Data Unavailable': {
    bg: 'bg-slate-100',
    text: 'text-slate-700',
    border: 'border-slate-300',
    hex: '#64748b',
    badge: 'bg-slate-200 text-slate-800 border-slate-400',
  },
};

export const ROUTE_PALETTE = [
  { id: 'route_1', name: 'Primary Route', stroke: '#2563eb', glow: '#93c5fd' },   // Royal Blue
  { id: 'route_2', name: 'Alternative 1', stroke: '#6366f1', glow: '#c7d2fe' },   // Indigo
  { id: 'route_3', name: 'Alternative 2', stroke: '#0891b2', glow: '#a5f3fc' },   // Cyan
];

export function getRouteColor(routeId: string, index: number = 0): { stroke: string; glow: string } {
  const match = ROUTE_PALETTE.find((r) => r.id === routeId);
  if (match) return match;
  return ROUTE_PALETTE[index % ROUTE_PALETTE.length];
}
