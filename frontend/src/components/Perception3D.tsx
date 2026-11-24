import React, { useMemo, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Line, Html, Grid } from '@react-three/drei';
import * as THREE from 'three';
import { Box, RotateCcw } from 'lucide-react';
import { AirspaceZone, DroneDetection, TrajectoryPoint } from '../types/drone';

interface Props {
  activeDetections: DroneDetection[];
  trajectories: Record<string, TrajectoryPoint[]>;
  zones: AirspaceZone[];
}

const TRACK_COLORS = ['#00e5ff', '#34d399', '#facc15', '#fb7185', '#a78bfa'];

function getTrackColor(trackId: string): string {
  const num = parseInt(trackId.replace(/\D/g, ''), 10) || 1;
  return TRACK_COLORS[(num - 1) % TRACK_COLORS.length];
}

const ZoneVolume: React.FC<{ zone: AirspaceZone }> = ({ zone }) => {
  const [minX, minY, minZ] = zone.min_bounds;
  const [maxX, maxY, maxZ] = zone.max_bounds;
  const size: [number, number, number] = [maxX - minX, maxY - minY, maxZ - minZ];
  const center: [number, number, number] = [
    (minX + maxX) * 0.5,
    (minY + maxY) * 0.5,
    (minZ + maxZ) * 0.5,
  ];

  const color =
    zone.zone_type === 'RESTRICTED'
      ? '#ef4444'
      : zone.zone_type === 'WARNING'
      ? '#f59e0b'
      : '#10b981';

  return (
    <mesh position={center}>
      <boxGeometry args={size} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={zone.zone_type === 'SAFE' ? 0.04 : 0.12}
        wireframe={zone.zone_type === 'SAFE'}
        depthWrite={false}
      />
    </mesh>
  );
};

export const Perception3D: React.FC<Props> = ({ activeDetections, trajectories, zones }) => {
  const controlsRef = useRef<any>(null);
  const [showGrid, setShowGrid] = useState(true);
  const [showTrajectories, setShowTrajectories] = useState(true);
  const [showPredictions, setShowPredictions] = useState(true);
  const [showGeofences, setShowGeofences] = useState(true);

  const isMetric = useMemo(
    () => activeDetections.some((d) => d.spatial.is_metric),
    [activeDetections]
  );

  const resetCamera = () => {
    if (controlsRef.current) {
      controlsRef.current.object.position.set(65, 55, -35);
      controlsRef.current.target.set(0, 25, 50);
      controlsRef.current.update();
    }
  };

  return (
    <div className="bg-panel border border-cyan-500/35 rounded-lg overflow-hidden flex flex-col h-[470px]">
      <div className="px-3 py-2 bg-navy border-b border-cyan-500/25 flex flex-wrap items-center justify-between gap-2 font-mono text-xs">
        <div className="flex items-center gap-2">
          <Box className="w-4 h-4 text-cyan-400" />
          <span className="text-cyan-300 font-semibold tracking-wider">3D PERCEPTION</span>
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded border ${
              isMetric
                ? 'bg-emerald-950/70 border-emerald-500/50 text-emerald-300'
                : 'bg-blue-950/70 border-cyan-500/40 text-cyan-300'
            }`}
          >
            {isMetric ? 'CALIBRATED METRIC (m)' : 'MONOCULAR RELATIVE SPACE'}
          </span>
        </div>

        <div className="flex items-center gap-1.5 text-[10px]">
          <button
            onClick={() => setShowGrid((v) => !v)}
            className={`px-2 py-0.5 rounded border ${
              showGrid ? 'border-cyan-400 text-cyan-200 bg-cyan-500/20' : 'border-slate-700 text-slate-400'
            }`}
          >
            GRID
          </button>
          <button
            onClick={() => setShowTrajectories((v) => !v)}
            className={`px-2 py-0.5 rounded border ${
              showTrajectories ? 'border-cyan-400 text-cyan-200 bg-cyan-500/20' : 'border-slate-700 text-slate-400'
            }`}
          >
            TRAILS
          </button>
          <button
            onClick={() => setShowPredictions((v) => !v)}
            className={`px-2 py-0.5 rounded border ${
              showPredictions ? 'border-cyan-400 text-cyan-200 bg-cyan-500/20' : 'border-slate-700 text-slate-400'
            }`}
          >
            PREDICT
          </button>
          <button
            onClick={() => setShowGeofences((v) => !v)}
            className={`px-2 py-0.5 rounded border ${
              showGeofences ? 'border-cyan-400 text-cyan-200 bg-cyan-500/20' : 'border-slate-700 text-slate-400'
            }`}
          >
            ZONES
          </button>
          <button
            onClick={resetCamera}
            title="Reset 3D View"
            className="p-1 rounded border border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/20"
          >
            <RotateCcw className="w-3 h-3" />
          </button>
        </div>
      </div>

      <div className="relative flex-1 bg-[#030712]">
        <Canvas camera={{ position: [65, 55, -35], fov: 50 }}>
          <color attach="background" args={['#030712']} />
          <ambientLight intensity={0.7} />
          <pointLight position={[20, 80, 40]} intensity={1.2} color="#00e5ff" />

          {showGrid && (
            <>
              <Grid
                position={[0, 0, 50]}
                args={[140, 140]}
                cellSize={10}
                cellThickness={0.6}
                cellColor="#0e3a5c"
                sectionSize={50}
                sectionThickness={1.2}
                sectionColor="#00b4d8"
                fadeDistance={240}
              />
              <Grid
                position={[0, 50, 120]}
                rotation={[Math.PI / 2, 0, 0]}
                args={[140, 100]}
                cellSize={10}
                cellThickness={0.5}
                cellColor="#0b2942"
                sectionSize={50}
                sectionThickness={1}
                sectionColor="#0284c7"
              />
              <axesHelper args={[25]} />
            </>
          )}

          <mesh position={[0, 1, 0]}>
            <coneGeometry args={[2.2, 4.5, 4]} />
            <meshStandardMaterial color="#38bdf8" emissive="#0284c7" />
          </mesh>

          {showGeofences && zones.map((z) => <ZoneVolume key={z.zone_id} zone={z} />)}

          {showTrajectories &&
            Object.entries(trajectories).map(([trackId, pts]) => {
              if (pts.length < 2) return null;
              const color = getTrackColor(trackId);
              const linePts = pts.map((p) => new THREE.Vector3(p.pos_x, p.pos_y, p.pos_z));
              return (
                <group key={`traj-${trackId}`}>
                  <Line points={linePts} color={color} lineWidth={2.5} />
                  {pts.slice(-12).map((p, idx) => (
                    <mesh key={idx} position={[p.pos_x, p.pos_y, p.pos_z]}>
                      <sphereGeometry args={[0.45, 8, 8]} />
                      <meshBasicMaterial color={color} />
                    </mesh>
                  ))}
                </group>
              );
            })}

          {activeDetections.map((det) => {
            const color = getTrackColor(det.track_id);
            const { x, y, z } = det.spatial;

            return (
              <group key={`drone-${det.track_id}`}>
                <group position={[x, y, z]}>
                  <mesh>
                    <octahedronGeometry args={[2.0, 0]} />
                    <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
                  </mesh>
                  <Html distanceFactor={90} position={[0, 3.6, 0]}>
                    <div className="bg-void/90 border border-cyan-400/60 px-1.5 py-0.5 rounded font-mono text-[10px] text-cyan-200 whitespace-nowrap pointer-events-none">
                      {det.track_id} ({x.toFixed(1)}, {y.toFixed(1)}, {z.toFixed(1)})
                    </div>
                  </Html>
                </group>

                <Line
                  points={[new THREE.Vector3(x, 0, z), new THREE.Vector3(x, y, z)]}
                  color={color}
                  lineWidth={1}
                  dashed
                  dashSize={1.5}
                  gapSize={1.5}
                />

                {showPredictions && det.predicted_trajectory && det.predicted_trajectory.length > 0 && (
                  <Line
                    points={[
                      new THREE.Vector3(x, y, z),
                      ...det.predicted_trajectory.map((p) => new THREE.Vector3(p.x, p.y, p.z)),
                    ]}
                    color="#facc15"
                    lineWidth={1.8}
                    dashed
                    dashSize={2}
                    gapSize={1.5}
                  />
                )}
              </group>
            );
          })}

          <OrbitControls ref={controlsRef} target={[0, 25, 50]} makeDefault />
        </Canvas>
      </div>
    </div>
  );
};
