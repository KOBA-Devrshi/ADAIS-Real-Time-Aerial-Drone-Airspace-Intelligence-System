export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface BBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface SpatialInfo {
  x: number;
  y: number;
  z: number;
  relative_depth: number;
  depth_confidence: number;
  is_metric: boolean;
  frame_label?: string;
  depth_method?: string;
}

export interface MotionInfo {
  vx: number;
  vy: number;
  vz: number;
  speed: number;
  heading_deg: number;
}

export interface PredictedPoint {
  dt: number;
  x: number;
  y: number;
  z: number;
  uncertainty_radius: number;
  is_metric: boolean;
}

export interface DroneDetection {
  frame_id: number;
  timestamp: number;
  track_id: string;
  class: string;
  confidence: number;
  track_status: 'ACTIVE' | 'UNCERTAIN' | 'LOST';
  bbox: BBox;
  center: { x: number; y: number };
  spatial: SpatialInfo;
  motion: MotionInfo;
  predicted_trajectory?: PredictedPoint[];
  risk_level?: RiskLevel;
  risk_reason?: string;
}

export interface TrajectoryPoint {
  frame_id: number;
  timestamp: number;
  image_x: number;
  image_y: number;
  pos_x: number;
  pos_y: number;
  pos_z: number;
  relative_depth: number;
  is_metric: boolean;
  speed: number;
  heading_deg: number;
  confidence: number;
}

export interface AirspaceZone {
  zone_id: string;
  name: string;
  zone_type: 'SAFE' | 'WARNING' | 'RESTRICTED';
  min_bounds: [number, number, number];
  max_bounds: [number, number, number];
  warning_margin: number;
}

export interface AirspaceEvent {
  id?: number;
  frame_id: number;
  timestamp: number;
  track_id: string | null;
  event_type: string;
  risk_level: RiskLevel;
  zone_name?: string;
  reason: string;
  confidence?: number;
}

export interface SessionInfo {
  session_id: string;
  filename: string;
  file_size_bytes: number;
  duration_sec: number;
  fps: number;
  resolution: { width: number; height: number };
  total_frames: number;
  video_url: string;
  status: 'UPLOADED' | 'PROCESSING' | 'PAUSED' | 'COMPLETED' | 'STOPPED' | 'ERROR';
  frames_processed?: number;
  processing_fps?: number;
  is_demo_mode?: boolean;
  error_message?: string | null;
}

export interface DetectorDiagnostics {
  status: string;
  available: boolean;
  weights_path: string;
  device: string;
  classes: Record<string, string>;
  error: string | null;
  setup_instructions: string[];
}
