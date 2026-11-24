import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { AirspaceEvent } from '../types/drone';

interface Props {
  events: AirspaceEvent[];
}

export const AirspaceAlerts: React.FC<Props> = ({ events }) => {
  return (
    <div className="bg-panel border border-cyan-500/30 rounded-lg p-3 flex flex-col h-[260px]">
      <div className="flex items-center gap-2 font-mono text-xs text-cyan-300 font-semibold mb-2">
        <ShieldAlert className="w-4 h-4 text-amber-400" />
        <span>AIRSPACE INTELLIGENCE & EVENT LOG</span>
      </div>
      <div className="flex-1 overflow-y-auto space-y-1.5 font-mono text-[11px] pr-1">
        {events.length === 0 ? (
          <div className="text-slate-500 text-center py-8">No airspace events logged yet.</div>
        ) : (
          events.map((ev, idx) => {
            const badge =
              ev.risk_level === 'CRITICAL'
                ? 'border-red-500/60 bg-red-950/40 text-red-200'
                : ev.risk_level === 'HIGH'
                ? 'border-orange-500/60 bg-orange-950/30 text-orange-200'
                : ev.risk_level === 'MEDIUM'
                ? 'border-amber-500/50 bg-amber-950/30 text-amber-200'
                : 'border-cyan-500/30 bg-void/70 text-slate-300';

            return (
              <div key={idx} className={`border rounded px-2.5 py-1.5 ${badge}`}>
                <div className="flex justify-between text-[10px] opacity-80">
                  <span>
                    [{ev.risk_level}] {ev.event_type} {ev.track_id ? `• ${ev.track_id}` : ''}
                  </span>
                  <span>T+{ev.timestamp.toFixed(2)}s</span>
                </div>
                <div className="mt-0.5">{ev.reason}</div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
