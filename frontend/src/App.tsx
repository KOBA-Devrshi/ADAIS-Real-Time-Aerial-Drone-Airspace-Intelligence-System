import React, { useMemo, useRef } from 'react';
import { Shield, Wifi, WifiOff } from 'lucide-react';
import { useAnalysis } from './hooks/useAnalysis';
import { VideoUpload } from './components/VideoUpload';
import { LiveDetection } from './components/LiveDetection';
import { Perception3D } from './components/Perception3D';
import { VideoControls } from './components/VideoControls';
import { StatsCards } from './components/StatsCards';
import { DroneTracker } from './components/DroneTracker';
import { FlightTimeline } from './components/FlightTimeline';
import { AirspaceAlerts } from './components/AirspaceAlerts';

export function App() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const {
    detectorDiag,
    setDetectorDiag,
    session,
    wsConnected,
    error,
    allDetections,
    activeDetections,
    synchronizedTrajectories,
    zones,
    events,
    processingFps,
    framesProcessed,
    currentTime,
    setCurrentTime,
    isPlaying,
    setIsPlaying,
    currentRiskLevel,
    avgConfidence,
    handleUpload,
    beginAnalysis,
    pauseOrResumeBackend,
  } = useAnalysis();

  const totalUniqueDrones = useMemo(
    () => new Set(allDetections.map((d) => d.track_id)).size,
    [allDetections]
  );

  return (
    <div className="min-h-screen bg-void text-slate-100 p-4 space-y-4">
      <header className="bg-navy border border-cyan-500/35 rounded-lg px-4 py-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-cyan-400" />
          <div>
            <h1 className="font-mono text-sm md:text-base font-bold tracking-widest text-cyan-300">
              ADAIS // AUTONOMOUS DRONE AIRSPACE INTELLIGENCE SYSTEM
            </h1>
            <p className="font-mono text-[11px] text-slate-400">
              REAL-TIME UAV DETECTION · BYTETRACK PERSISTENCE · 3D SPATIAL PERCEPTION & GEOFENCING
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <span className="px-2.5 py-1 rounded bg-void border border-cyan-500/30 text-slate-300">
            SESSION: {session?.session_id || 'STANDBY'}
          </span>
          <span
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded border ${
              wsConnected
                ? 'border-emerald-500/40 bg-emerald-950/40 text-emerald-300'
                : 'border-slate-700 bg-void text-slate-400'
            }`}
          >
            {wsConnected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {wsConnected ? 'TELEMETRY LINK ONLINE' : 'WS IDLE'}
          </span>
        </div>
      </header>

      <VideoUpload
        session={session}
        detectorDiag={detectorDiag}
        onDiagnosticsUpdated={setDetectorDiag}
        framesProcessed={framesProcessed}
        activeCount={activeDetections.length}
        onUpload={handleUpload}
        onStart={beginAnalysis}
        onControl={pauseOrResumeBackend}
        error={error}
      />

      <main className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <LiveDetection
          session={session}
          videoRef={videoRef}
          detections={activeDetections}
          currentTime={currentTime}
          processingFps={processingFps}
          onTimeUpdate={setCurrentTime}
          onPlayStateChange={setIsPlaying}
        />

        <Perception3D
          activeDetections={activeDetections}
          trajectories={synchronizedTrajectories}
          zones={zones}
        />
      </main>

      <VideoControls
        session={session}
        videoRef={videoRef}
        isPlaying={isPlaying}
        currentTime={currentTime}
        onSeek={setCurrentTime}
      />

      <StatsCards
        totalUniqueDrones={totalUniqueDrones}
        activeTracks={activeDetections.length}
        framesProcessed={framesProcessed}
        avgConfidence={avgConfidence}
        processingFps={processingFps}
        riskLevel={currentRiskLevel}
      />

      <DroneTracker detections={activeDetections} />

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <FlightTimeline allDetections={allDetections} currentTime={currentTime} />
        <AirspaceAlerts events={events} />
      </section>
    </div>
  );
}

export default App;
