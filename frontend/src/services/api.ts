import {
  AirspaceEvent,
  AirspaceZone,
  DetectorDiagnostics,
  DroneDetection,
  SessionInfo,
  TrajectoryPoint,
} from '../types/drone';

export async function getDetectorStatus(): Promise<DetectorDiagnostics> {
  const res = await fetch('/api/detector/status');
  if (!res.ok) throw new Error('Failed to fetch detector status');
  return res.json();
}

export async function configureDetectorWeights(weightsPath: string) {
  const res = await fetch('/api/detector/configure', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ weights_path: weightsPath }),
  });
  return res.json();
}

export async function uploadVideoFile(file: File): Promise<SessionInfo> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('/api/upload', { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail));
  }
  return res.json();
}

export async function startAnalysis(
  sessionId: string,
  options: { conf_threshold: number; frame_stride: number; demo_mode: boolean }
) {
  const res = await fetch(`/api/analyze/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to start analysis' }));
    throw new Error(err.detail?.message || err.detail || 'Failed to start analysis');
  }
  return res.json();
}

export async function controlAnalysis(sessionId: string, action: 'pause' | 'resume' | 'stop') {
  const res = await fetch(`/api/analyze/${sessionId}/${action}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Failed to ${action} session`);
  return res.json();
}

export async function fetchSessionStatus(sessionId: string): Promise<SessionInfo> {
  const res = await fetch(`/api/status/${sessionId}`);
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export async function fetchDetections(sessionId: string): Promise<DroneDetection[]> {
  const res = await fetch(`/api/detections/${sessionId}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchTrajectories(sessionId: string): Promise<Record<string, TrajectoryPoint[]>> {
  const res = await fetch(`/api/trajectory/${sessionId}`);
  if (!res.ok) return {};
  return res.json();
}

export async function fetchAirspace(sessionId: string): Promise<{
  airspace_risk_level: string;
  zones: AirspaceZone[];
  events: AirspaceEvent[];
}> {
  const res = await fetch(`/api/airspace/${sessionId}`);
  if (!res.ok) return { airspace_risk_level: 'LOW', zones: [], events: [] };
  return res.json();
}
