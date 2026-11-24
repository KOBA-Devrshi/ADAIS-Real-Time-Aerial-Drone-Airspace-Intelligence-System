import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AirspaceEvent,
  AirspaceZone,
  DetectorDiagnostics,
  DroneDetection,
  RiskLevel,
  SessionInfo,
  TrajectoryPoint,
} from '../types/drone';
import {
  controlAnalysis,
  fetchAirspace,
  fetchDetections,
  fetchSessionStatus,
  fetchTrajectories,
  getDetectorStatus,
  startAnalysis,
  uploadVideoFile,
} from '../services/api';
import { AnalysisSocketClient } from '../services/websocket';

export function useAnalysis() {
  const [detectorDiag, setDetectorDiag] = useState<DetectorDiagnostics | null>(null);
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [allDetections, setAllDetections] = useState<DroneDetection[]>([]);
  const [trajectories, setTrajectories] = useState<Record<string, TrajectoryPoint[]>>({});
  const [zones, setZones] = useState<AirspaceZone[]>([]);
  const [events, setEvents] = useState<AirspaceEvent[]>([]);
  const [processingFps, setProcessingFps] = useState<number>(0);
  const [framesProcessed, setFramesProcessed] = useState<number>(0);

  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const socketRef = useRef<AnalysisSocketClient>(new AnalysisSocketClient());

  useEffect(() => {
    getDetectorStatus().then(setDetectorDiag).catch(() => {});
    return () => socketRef.current.disconnect();
  }, []);

  const refreshStoredData = useCallback(async (sessionId: string) => {
    const [dets, trajs, airspace, status] = await Promise.all([
      fetchDetections(sessionId),
      fetchTrajectories(sessionId),
      fetchAirspace(sessionId),
      fetchSessionStatus(sessionId),
    ]);
    setAllDetections(dets);
    setTrajectories(trajs);
    setZones(airspace.zones);
    setEvents(airspace.events);
    setSession((prev) => (prev ? { ...prev, ...status } : status));
  }, []);

  const handleUpload = useCallback(async (file: File) => {
    setError(null);
    const info = await uploadVideoFile(file);
    setSession(info);
    setAllDetections([]);
    setTrajectories({});
    setEvents([]);
    setFramesProcessed(0);
    setProcessingFps(0);
    setCurrentTime(0);

    const airspace = await fetchAirspace(info.session_id);
    setZones(airspace.zones);

    socketRef.current.connect(
      info.session_id,
      (msg) => {
        if (msg.type === 'FRAME_UPDATE') {
          setFramesProcessed((p) => p + 1);
          setProcessingFps(msg.processing_fps || 0);
          if (Array.isArray(msg.detections) && msg.detections.length > 0) {
            setAllDetections((prev) => [...prev, ...msg.detections]);
          }
          if (msg.trajectories) {
            setTrajectories(msg.trajectories);
          }
          if (Array.isArray(msg.events) && msg.events.length > 0) {
            setEvents((prev) => [...msg.events.reverse(), ...prev].slice(0, 250));
          }
        } else if (msg.type === 'COMPLETED' || msg.type === 'STOPPED') {
          refreshStoredData(info.session_id);
        } else if (msg.type === 'ERROR') {
          setError(msg.message);
          setSession((prev) => (prev ? { ...prev, status: 'ERROR', error_message: msg.message } : null));
        }
      },
      setWsConnected
    );
  }, [refreshStoredData]);

  const beginAnalysis = useCallback(
    async (opts: { conf_threshold: number; frame_stride: number; demo_mode: boolean }) => {
      if (!session) return;
      setError(null);
      setAllDetections([]);
      setTrajectories({});
      setEvents([]);
      setFramesProcessed(0);
      await startAnalysis(session.session_id, opts);
      setSession((prev) => (prev ? { ...prev, status: 'PROCESSING', is_demo_mode: opts.demo_mode } : null));
    },
    [session]
  );

  const pauseOrResumeBackend = useCallback(
    async (action: 'pause' | 'resume' | 'stop') => {
      if (!session) return;
      await controlAnalysis(session.session_id, action);
      setSession((prev) =>
        prev
          ? {
              ...prev,
              status: action === 'pause' ? 'PAUSED' : action === 'resume' ? 'PROCESSING' : 'STOPPED',
            }
          : null
      );
    },
    [session]
  );

  const activeDetections = useMemo(() => {
    if (allDetections.length === 0) return [];
    const fps = session?.fps || 30;
    const windowSec = Math.max(0.08, 2.0 / fps);

    let bestTs = -1;
    for (let i = allDetections.length - 1; i >= 0; i--) {
      const ts = allDetections[i].timestamp;
      if (ts <= currentTime + 0.02) {
        bestTs = ts;
        break;
      }
    }
    if (bestTs < 0 || currentTime - bestTs > windowSec * 3) return [];
    return allDetections.filter((d) => Math.abs(d.timestamp - bestTs) < 1e-3);
  }, [allDetections, currentTime, session?.fps]);

  const synchronizedTrajectories = useMemo(() => {
    const out: Record<string, TrajectoryPoint[]> = {};
    for (const [tid, pts] of Object.entries(trajectories)) {
      out[tid] = pts.filter((p) => p.timestamp <= currentTime + 0.02);
    }
    return out;
  }, [trajectories, currentTime]);

  const currentRiskLevel: RiskLevel = useMemo(() => {
    const order: Record<RiskLevel, number> = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 };
    let maxR: RiskLevel = 'LOW';
    for (const d of activeDetections) {
      const r = d.risk_level || 'LOW';
      if (order[r] > order[maxR]) maxR = r;
    }
    return maxR;
  }, [activeDetections]);

  const avgConfidence = useMemo(() => {
    if (allDetections.length === 0) return 0;
    const sum = allDetections.reduce((acc, d) => acc + d.confidence, 0);
    return sum / allDetections.length;
  }, [allDetections]);

  return {
    detectorDiag,
    setDetectorDiag,
    session,
    wsConnected,
    error,
    setError,
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
  };
}
