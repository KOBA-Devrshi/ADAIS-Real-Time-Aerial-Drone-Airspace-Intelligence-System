import React, { useEffect, useRef } from 'react';
import { Radar } from 'lucide-react';
import { DroneDetection, SessionInfo } from '../types/drone';

interface Props {
  session: SessionInfo | null;
  videoRef: React.RefObject<HTMLVideoElement>;
  detections: DroneDetection[];
  currentTime: number;
  processingFps: number;
  onTimeUpdate: (t: number) => void;
  onPlayStateChange: (playing: boolean) => void;
}

export const LiveDetection: React.FC<Props> = ({
  session,
  videoRef,
  detections,
  currentTime,
  processingFps,
  onTimeUpdate,
  onPlayStateChange,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    let rafId: number;
    const syncClock = () => {
      const vid = videoRef.current;
      if (vid && !vid.paused) {
        onTimeUpdate(vid.currentTime);
      }
      rafId = requestAnimationFrame(syncClock);
    };
    rafId = requestAnimationFrame(syncClock);
    return () => cancelAnimationFrame(rafId);
  }, [videoRef, onTimeUpdate]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const rect = video.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;
    canvas.width = rect.width;
    canvas.height = rect.height;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const srcW = session?.resolution.width || video.videoWidth || 1280;
    const srcH = session?.resolution.height || video.videoHeight || 720;

    const scale = Math.min(canvas.width / srcW, canvas.height / srcH);
    const offsetX = (canvas.width - srcW * scale) * 0.5;
    const offsetY = (canvas.height - srcH * scale) * 0.5;

    detections.forEach((det) => {
      const x1 = det.bbox.x1 * scale + offsetX;
      const y1 = det.bbox.y1 * scale + offsetY;
      const w = (det.bbox.x2 - det.bbox.x1) * scale;
      const h = (det.bbox.y2 - det.bbox.y1) * scale;
      const cx = det.center.x * scale + offsetX;
      const cy = det.center.y * scale + offsetY;

      const stroke =
        det.risk_level === 'CRITICAL' || det.risk_level === 'HIGH'
          ? '#ff3b5c'
          : det.risk_level === 'MEDIUM'
          ? '#facc15'
          : '#00e5ff';

      const bracket = Math.min(14, w * 0.25, h * 0.25);
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 2;
      ctx.strokeRect(x1, y1, w, h);

      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(x1, y1 + bracket);
      ctx.lineTo(x1, y1);
      ctx.lineTo(x1 + bracket, y1);
      ctx.moveTo(x1 + w - bracket, y1);
      ctx.lineTo(x1 + w, y1);
      ctx.lineTo(x1 + w, y1 + bracket);
      ctx.moveTo(x1, y1 + h - bracket);
      ctx.lineTo(x1, y1 + h);
      ctx.lineTo(x1 + bracket, y1 + h);
      ctx.moveTo(x1 + w - bracket, y1 + h);
      ctx.lineTo(x1 + w, y1 + h);
      ctx.lineTo(x1 + w, y1 + h - bracket);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(cx - 7, cy);
      ctx.lineTo(cx + 7, cy);
      ctx.moveTo(cx, cy - 7);
      ctx.lineTo(cx, cy + 7);
      ctx.stroke();

      const lines = [
        `DRONE ID: ${det.track_id}`,
        `CLASS: ${det.class}`,
        `CONFIDENCE: ${(det.confidence * 100).toFixed(1)}%`,
        `TRACK STATUS: ${det.track_status}`,
        `IMAGE POS: X:${Math.round(det.center.x)} Y:${Math.round(det.center.y)}`,
      ];

      ctx.font = '10px "JetBrains Mono", monospace';
      const boxW = 186;
      const boxH = lines.length * 13 + 8;
      const tagX = Math.min(canvas.width - boxW - 4, Math.max(4, x1));
      const tagY = y1 - boxH - 6 > 4 ? y1 - boxH - 6 : y1 + h + 6;

      ctx.fillStyle = 'rgba(4, 8, 17, 0.86)';
      ctx.fillRect(tagX, tagY, boxW, boxH);
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.strokeRect(tagX, tagY, boxW, boxH);

      ctx.fillStyle = stroke;
      lines.forEach((line, idx) => {
        ctx.fillText(line, tagX + 6, tagY + 13 + idx * 13);
      });
    });
  }, [detections, session, videoRef]);

  return (
    <div className="bg-panel border border-cyan-500/35 rounded-lg overflow-hidden flex flex-col h-[470px]">
      <div className="px-3 py-2 bg-navy border-b border-cyan-500/25 flex items-center justify-between font-mono text-xs">
        <div className="flex items-center gap-2">
          <Radar className="w-4 h-4 text-cyan-400 animate-pulse" />
          <span className="text-cyan-300 font-semibold tracking-wider">LIVE DRONE DETECTION</span>
          {session?.is_demo_mode && (
            <span className="bg-amber-500/20 border border-amber-400 text-amber-300 text-[10px] px-1.5 py-0.2 rounded">
              DEMO CALIBRATION MODE
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-[11px] text-slate-300">
          <span>T: {currentTime.toFixed(2)}s</span>
          <span>FPS: {processingFps.toFixed(1)}</span>
          <span className="text-cyan-300">TARGETS: {detections.length}</span>
        </div>
      </div>

      <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden">
        {session ? (
          <>
            <video
              ref={videoRef}
              src={session.video_url}
              className="w-full h-full object-contain"
              playsInline
              onTimeUpdate={(e) => onTimeUpdate(e.currentTarget.currentTime)}
              onPlay={() => onPlayStateChange(true)}
              onPause={() => onPlayStateChange(false)}
              onEnded={() => onPlayStateChange(false)}
            />
            <canvas ref={canvasRef} className="absolute inset-0 pointer-events-none" />
          </>
        ) : (
          <div className="text-center font-mono text-xs text-slate-500 space-y-1">
            <div>NO SENSOR VIDEO FEED LOADED</div>
            <div className="text-[10px] text-slate-600">
              Upload drone surveillance video above to initialize computer vision pipeline
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
