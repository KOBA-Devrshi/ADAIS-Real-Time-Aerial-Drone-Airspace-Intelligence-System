import React from 'react';
import { DroneDetection } from '../types/drone';

interface Props {
  detections: DroneDetection[];
}

export const DroneTracker: React.FC<Props> = ({ detections }) => {
  return (
    <div className="bg-panel border border-cyan-500/30 rounded-lg overflow-hidden">
      <div className="px-3 py-2 bg-navy border-b border-cyan-500/25 font-mono text-xs text-cyan-300 font-semibold">
        ACTIVE UAV TELEMETRY MATRIX
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left font-mono text-xs">
          <thead className="bg-void/80 text-slate-400 text-[11px] border-b border-cyan-500/20">
            <tr>
              <th className="py-2 px-3">DRONE ID</th>
              <th className="py-2 px-3">CLASS</th>
              <th className="py-2 px-3">CONFIDENCE</th>
              <th className="py-2 px-3">CURRENT X</th>
              <th className="py-2 px-3">CURRENT Y</th>
              <th className="py-2 px-3">EST. DEPTH</th>
              <th className="py-2 px-3">EST. SPEED</th>
              <th className="py-2 px-3">DIRECTION</th>
              <th className="py-2 px-3">STATUS</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-cyan-500/10 text-slate-200">
            {detections.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-6 text-center text-slate-500">
                  No active drone tracks at current playback timestamp.
                </td>
              </tr>
            ) : (
              detections.map((d) => (
                <tr key={d.track_id} className="hover:bg-cyan-950/20">
                  <td className="py-2 px-3 text-cyan-300 font-semibold">{d.track_id}</td>
                  <td className="py-2 px-3">{d.class}</td>
                  <td className="py-2 px-3">{(d.confidence * 100).toFixed(1)}%</td>
                  <td className="py-2 px-3">{Math.round(d.center.x)} px</td>
                  <td className="py-2 px-3">{Math.round(d.center.y)} px</td>
                  <td className="py-2 px-3">
                    {d.spatial.is_metric
                      ? `${d.spatial.z.toFixed(1)} m`
                      : `${(d.spatial.relative_depth * 100).toFixed(1)}% rel`}
                  </td>
                  <td className="py-2 px-3">
                    {d.motion.speed.toFixed(1)} {d.spatial.is_metric ? 'm/s' : 'u/s'}
                  </td>
                  <td className="py-2 px-3">{d.motion.heading_deg.toFixed(0)}°</td>
                  <td className="py-2 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] ${
                        d.track_status === 'ACTIVE'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                          : 'bg-amber-950 text-amber-300 border border-amber-500/40'
                      }`}
                    >
                      {d.track_status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
