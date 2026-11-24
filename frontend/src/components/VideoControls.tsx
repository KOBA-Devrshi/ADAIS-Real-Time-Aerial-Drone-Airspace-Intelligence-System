import React from 'react';
import { Play, Pause, Square, RotateCcw, StepBack, StepForward } from 'lucide-react';
import { SessionInfo } from '../types/drone';

interface Props {
  session: SessionInfo | null;
  videoRef: React.RefObject<HTMLVideoElement>;
  isPlaying: boolean;
  currentTime: number;
  onSeek: (t: number) => void;
}

export const VideoControls: React.FC<Props> = ({
  session,
  videoRef,
  isPlaying,
  currentTime,
  onSeek,
}) => {
  const duration = session?.duration_sec || 0;
  const stepSec = 1 / (session?.fps || 30);

  const togglePlay = () => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) v.play();
    else v.pause();
  };

  const stopVideo = () => {
    const v = videoRef.current;
    if (!v) return;
    v.pause();
    v.currentTime = 0;
    onSeek(0);
  };

  const stepFrame = (dir: -1 | 1) => {
    const v = videoRef.current;
    if (!v) return;
    v.pause();
    const next = Math.max(0, Math.min(duration, v.currentTime + dir * stepSec));
    v.currentTime = next;
    onSeek(next);
  };

  const setRate = (rate: number) => {
    if (videoRef.current) videoRef.current.playbackRate = rate;
  };

  return (
    <div className="bg-panel border border-cyan-500/30 rounded-lg px-4 py-2.5 flex flex-wrap items-center gap-4 font-mono text-xs">
      <div className="flex items-center gap-1.5">
        <button
          disabled={!session}
          onClick={togglePlay}
          className="p-1.5 rounded bg-cyan-500/20 hover:bg-cyan-500/35 disabled:opacity-40 border border-cyan-400/50 text-cyan-200"
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
        </button>
        <button
          disabled={!session}
          onClick={stopVideo}
          className="p-1.5 rounded bg-void hover:bg-slate-800 disabled:opacity-40 border border-cyan-500/30 text-slate-200"
        >
          <Square className="w-4 h-4" />
        </button>
        <button
          disabled={!session}
          onClick={() => {
            if (videoRef.current) {
              videoRef.current.currentTime = 0;
              onSeek(0);
            }
          }}
          className="p-1.5 rounded bg-void hover:bg-slate-800 disabled:opacity-40 border border-cyan-500/30 text-slate-200"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
        <button
          disabled={!session}
          onClick={() => stepFrame(-1)}
          title="Previous Frame"
          className="p-1.5 rounded bg-void hover:bg-slate-800 disabled:opacity-40 border border-cyan-500/30 text-slate-200"
        >
          <StepBack className="w-4 h-4" />
        </button>
        <button
          disabled={!session}
          onClick={() => stepFrame(1)}
          title="Next Frame"
          className="p-1.5 rounded bg-void hover:bg-slate-800 disabled:opacity-40 border border-cyan-500/30 text-slate-200"
        >
          <StepForward className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 flex items-center gap-3 min-w-[200px]">
        <span className="text-cyan-300">{currentTime.toFixed(2)}s</span>
        <input
          type="range"
          min={0}
          max={duration || 1}
          step={0.01}
          value={currentTime}
          disabled={!session}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            if (videoRef.current) videoRef.current.currentTime = val;
            onSeek(val);
          }}
          className="flex-1 accent-cyan-400 cursor-pointer"
        />
        <span className="text-slate-400">{duration.toFixed(2)}s</span>
      </div>

      <div className="flex items-center gap-1.5">
        <span className="text-slate-400 text-[10px]">SPEED</span>
        {[0.25, 0.5, 1, 2].map((r) => (
          <button
            key={r}
            disabled={!session}
            onClick={() => setRate(r)}
            className="px-2 py-0.5 rounded bg-void hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-200 text-[11px]"
          >
            {r}x
          </button>
        ))}
      </div>
    </div>
  );
};
