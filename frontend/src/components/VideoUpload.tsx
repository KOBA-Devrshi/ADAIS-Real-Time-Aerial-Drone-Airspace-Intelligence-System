import React, { useRef, useState } from 'react';
import { Upload, Play, Pause, Square, RotateCcw, AlertTriangle, CheckCircle2, Cpu } from 'lucide-react';
import { DetectorDiagnostics, SessionInfo } from '../types/drone';
import { configureDetectorWeights, getDetectorStatus } from '../services/api';

interface Props {
  session: SessionInfo | null;
  detectorDiag: DetectorDiagnostics | null;
  onDiagnosticsUpdated: (d: DetectorDiagnostics) => void;
  framesProcessed: number;
  activeCount: number;
  onUpload: (file: File) => Promise<void>;
  onStart: (opts: { conf_threshold: number; frame_stride: number; demo_mode: boolean }) => Promise<void>;
  onControl: (action: 'pause' | 'resume' | 'stop') => Promise<void>;
  error: string | null;
}

export const VideoUpload: React.FC<Props> = ({
  session,
  detectorDiag,
  onDiagnosticsUpdated,
  framesProcessed,
  activeCount,
  onUpload,
  onStart,
  onControl,
  error,
}) => {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [confThreshold, setConfThreshold] = useState(0.45);
  const [frameStride, setFrameStride] = useState(1);
  const [demoMode, setDemoMode] = useState(false);
  const [weightsInput, setWeightsInput] = useState('weights/drone_best.pt');
  const [showSetup, setShowSetup] = useState(false);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    try {
      await onUpload(files[0]);
    } finally {
      setUploading(false);
    }
  };

  const handleReloadWeights = async () => {
    const res = await configureDetectorWeights(weightsInput);
    if (res.diagnostics) onDiagnosticsUpdated(res.diagnostics);
    else onDiagnosticsUpdated(await getDetectorStatus());
  };

  const progressPct =
    session && session.total_frames > 0
      ? Math.min(100, Math.round(((framesProcessed || session.frames_processed || 0) / session.total_frames) * 100))
      : 0;

  return (
    <div className="bg-panel/90 border border-cyan-500/30 rounded-lg p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cyan-500/20 pb-2">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-mono uppercase tracking-wider text-cyan-300">
            Ingest & AI Inference Pipeline
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          {detectorDiag?.available ? (
            <span className="flex items-center gap-1 text-emerald-400 bg-emerald-950/60 border border-emerald-500/40 px-2 py-0.5 rounded">
              <CheckCircle2 className="w-3.5 h-3.5" /> YOLO DRONE MODEL READY ({detectorDiag.device})
            </span>
          ) : (
            <button
              onClick={() => setShowSetup((s) => !s)}
              className="flex items-center gap-1 text-amber-300 bg-amber-950/60 border border-amber-500/40 px-2 py-0.5 rounded hover:bg-amber-900/50"
            >
              <AlertTriangle className="w-3.5 h-3.5" /> DRONE WEIGHTS MISSING — SETUP GUIDE
            </button>
          )}
        </div>
      </div>

      {!detectorDiag?.available && (
        <div className="bg-amber-950/30 border border-amber-500/40 rounded p-3 text-xs font-mono text-amber-200 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-amber-300">
              DETECTOR UNAVAILABLE: {detectorDiag?.error || 'Custom drone weights not loaded.'}
            </span>
            <label className="flex items-center gap-2 cursor-pointer text-cyan-300">
              <input
                type="checkbox"
                checked={demoMode}
                onChange={(e) => setDemoMode(e.target.checked)}
                className="accent-cyan-400"
              />
              <span>Enable DEMO Calibration Mode</span>
            </label>
          </div>

          {showSetup && (
            <div className="space-y-2 pt-1 border-t border-amber-500/20 text-slate-300">
              {detectorDiag?.setup_instructions?.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
              <div className="flex items-center gap-2 pt-1">
                <input
                  value={weightsInput}
                  onChange={(e) => setWeightsInput(e.target.value)}
                  className="bg-void border border-cyan-500/30 px-2 py-1 rounded text-xs text-cyan-200 flex-1"
                  placeholder="weights/drone_best.pt"
                />
                <button
                  onClick={handleReloadWeights}
                  className="bg-cyan-600/30 hover:bg-cyan-600/50 border border-cyan-400/50 px-3 py-1 rounded text-cyan-200"
                >
                  LOAD WEIGHTS
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-center">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={`lg:col-span-4 border border-dashed rounded p-3 cursor-pointer transition text-center font-mono text-xs ${
            dragging
              ? 'border-cyan-400 bg-cyan-950/40'
              : 'border-cyan-500/30 bg-void/70 hover:border-cyan-400/70'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".mp4,.mov,.avi,.mkv"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <Upload className="w-4 h-4 mx-auto mb-1 text-cyan-400" />
          <div className="text-slate-200">
            {uploading ? 'VALIDATING STREAM...' : 'DROP DRONE FOOTAGE OR BROWSE'}
          </div>
          <div className="text-[10px] text-slate-400">MP4 · MOV · AVI · MKV (MAX 500MB)</div>
        </div>

        <div className="lg:col-span-4 bg-void/70 border border-cyan-500/20 rounded p-2.5 font-mono text-[11px] space-y-1">
          <div className="flex justify-between">
            <span className="text-slate-400">VIDEO UPLOADED:</span>
            <span className="text-cyan-300 truncate max-w-[180px]">{session?.filename || 'NONE'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">DURATION / FPS:</span>
            <span className="text-slate-200">
              {session ? `${session.duration_sec.toFixed(2)}s @ ${session.fps} FPS` : '--'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">STATUS:</span>
            <span className="text-emerald-400">{session?.status || 'IDLE'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">FRAMES ANALYSED:</span>
            <span className="text-slate-200">
              {framesProcessed} / {session?.total_frames || 0} ({progressPct}%)
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">ACTIVE OBJECTS:</span>
            <span className="text-cyan-300">{activeCount}</span>
          </div>
        </div>

        <div className="lg:col-span-4 space-y-2 font-mono text-xs">
          <div className="grid grid-cols-2 gap-2">
            <label className="bg-void/70 border border-cyan-500/20 rounded px-2 py-1 flex items-center justify-between">
              <span className="text-[10px] text-slate-400">CONF</span>
              <input
                type="number"
                step="0.05"
                min="0.1"
                max="0.95"
                value={confThreshold}
                onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
                className="w-14 bg-transparent text-right text-cyan-300 focus:outline-none"
              />
            </label>
            <label className="bg-void/70 border border-cyan-500/20 rounded px-2 py-1 flex items-center justify-between">
              <span className="text-[10px] text-slate-400">STRIDE</span>
              <select
                value={frameStride}
                onChange={(e) => setFrameStride(Number(e.target.value))}
                className="bg-void text-cyan-300 focus:outline-none"
              >
                <option value={1}>1x (All)</option>
                <option value={2}>2x Fast</option>
                <option value={4}>4x Turbo</option>
              </select>
            </label>
          </div>

          <div className="flex flex-wrap gap-1.5">
            <button
              disabled={!session || (!detectorDiag?.available && !demoMode)}
              onClick={() => onStart({ conf_threshold: confThreshold, frame_stride: frameStride, demo_mode: demoMode })}
              className="flex-1 flex items-center justify-center gap-1 bg-cyan-500/20 hover:bg-cyan-500/35 disabled:opacity-40 border border-cyan-400/60 text-cyan-200 py-1.5 px-2 rounded"
            >
              <Play className="w-3.5 h-3.5" /> START ANALYSIS
            </button>

            {session?.status === 'PROCESSING' && (
              <button
                onClick={() => onControl('pause')}
                className="flex items-center gap-1 bg-amber-500/20 hover:bg-amber-500/35 border border-amber-400/60 text-amber-200 py-1.5 px-2.5 rounded"
              >
                <Pause className="w-3.5 h-3.5" /> PAUSE
              </button>
            )}

            {session?.status === 'PAUSED' && (
              <button
                onClick={() => onControl('resume')}
                className="flex items-center gap-1 bg-emerald-500/20 hover:bg-emerald-500/35 border border-emerald-400/60 text-emerald-200 py-1.5 px-2.5 rounded"
              >
                <Play className="w-3.5 h-3.5" /> RESUME
              </button>
            )}

            {(session?.status === 'PROCESSING' || session?.status === 'PAUSED') && (
              <button
                onClick={() => onControl('stop')}
                className="flex items-center gap-1 bg-red-500/20 hover:bg-red-500/35 border border-red-400/60 text-red-200 py-1.5 px-2.5 rounded"
              >
                <Square className="w-3.5 h-3.5" /> STOP
              </button>
            )}

            {session && (
              <button
                disabled={!detectorDiag?.available && !demoMode}
                onClick={() => onStart({ conf_threshold: confThreshold, frame_stride: frameStride, demo_mode: demoMode })}
                title="Restart Analysis"
                className="flex items-center gap-1 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 border border-cyan-500/30 text-slate-200 py-1.5 px-2 rounded"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/60 border border-red-500/50 text-red-200 text-xs font-mono px-3 py-2 rounded">
          ERROR: {error}
        </div>
      )}
    </div>
  );
};
