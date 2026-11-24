import React, { useMemo } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine } from 'recharts';
import { DroneDetection } from '../types/drone';

interface Props {
  allDetections: DroneDetection[];
  currentTime: number;
}

export const FlightTimeline: React.FC<Props> = ({ allDetections, currentTime }) => {
  const chartData = useMemo(() => {
    const byTs = new Map<number, { timestamp: number; count: number; maxConf: number }>();
    allDetections.forEach((d) => {
      const key = Number(d.timestamp.toFixed(2));
      const existing = byTs.get(key) || { timestamp: key, count: 0, maxConf: 0 };
      existing.count += 1;
      existing.maxConf = Math.max(existing.maxConf, Math.round(d.confidence * 100));
      byTs.set(key, existing);
    });
    return Array.from(byTs.values()).sort((a, b) => a.timestamp - b.timestamp);
  }, [allDetections]);

  return (
    <div className="bg-panel border border-cyan-500/30 rounded-lg p-3 flex flex-col h-[260px]">
      <div className="font-mono text-xs text-cyan-300 font-semibold mb-2">
        FLIGHT-PATH & DETECTION TIMELINE
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <XAxis dataKey="timestamp" stroke="#64748b" fontSize={10} tickFormatter={(v) => `${v}s`} />
            <YAxis stroke="#64748b" fontSize={10} />
            <Tooltip
              contentStyle={{ backgroundColor: '#040811', borderColor: '#00e5ff', fontSize: '11px' }}
            />
            <ReferenceLine x={Number(currentTime.toFixed(2))} stroke="#00e5ff" strokeDasharray="3 3" />
            <Area
              type="monotone"
              dataKey="maxConf"
              name="Peak Confidence (%)"
              stroke="#00e5ff"
              fill="#00e5ff"
              fillOpacity={0.18}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
