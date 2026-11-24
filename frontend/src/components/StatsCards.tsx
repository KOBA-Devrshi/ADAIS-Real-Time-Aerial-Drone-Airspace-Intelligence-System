import React from 'react';
import { RiskLevel } from '../types/drone';

interface Props {
  totalUniqueDrones: number;
  activeTracks: number;
  framesProcessed: number;
  avgConfidence: number;
  processingFps: number;
  riskLevel: RiskLevel;
}

export const StatsCards: React.FC<Props> = ({
  totalUniqueDrones,
  activeTracks,
  framesProcessed,
  avgConfidence,
  processingFps,
  riskLevel,
}) => {
  const riskStyle =
    riskLevel === 'CRITICAL'
      ? 'text-red-400 border-red-500/60 bg-red-950/30'
      : riskLevel === 'HIGH'
      ? 'text-orange-400 border-orange-500/60 bg-orange-950/30'
      : riskLevel === 'MEDIUM'
      ? 'text-amber-300 border-amber-500/60 bg-amber-950/30'
      : 'text-emerald-400 border-emerald-500/40 bg-emerald-950/20';

  const cards = [
    { label: 'TOTAL DRONES DETECTED', value: totalUniqueDrones, accent: 'text-cyan-300' },
    { label: 'ACTIVE TRACKS', value: activeTracks, accent: 'text-emerald-400' },
    { label: 'FRAMES PROCESSED', value: framesProcessed.toLocaleString(), accent: 'text-slate-100' },
    { label: 'AVG CONFIDENCE', value: `${(avgConfidence * 100).toFixed(1)}%`, accent: 'text-cyan-300' },
    { label: 'PROCESSING FPS', value: processingFps.toFixed(1), accent: 'text-blue-400' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-3 font-mono">
      {cards.map((c) => (
        <div key={c.label} className="bg-panel border border-cyan-500/25 rounded-lg p-3">
          <div className="text-[10px] text-slate-400 tracking-wider">{c.label}</div>
          <div className={`text-xl font-bold mt-1 ${c.accent}`}>{c.value}</div>
        </div>
      ))}
      <div className={`border rounded-lg p-3 ${riskStyle}`}>
        <div className="text-[10px] opacity-80 tracking-wider">AIRSPACE RISK LEVEL</div>
        <div className="text-xl font-bold mt-1">{riskLevel}</div>
      </div>
    </div>
  );
};
