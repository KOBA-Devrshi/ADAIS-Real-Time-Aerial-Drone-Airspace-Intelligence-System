from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import AnalysisSession

router = APIRouter(prefix="/api", tags=["analysis"])


class AnalyzeRequest(BaseModel):
    conf_threshold: float = 0.45
    frame_stride: int = 1
    demo_mode: bool = False
    calibration: Optional[dict] = None


class DetectorConfigRequest(BaseModel):
    weights_path: str


def create_analysis_router(orchestrator, model_loader):
    @router.post("/analyze/{session_id}")
    async def start_analysis(session_id: str, req: AnalyzeRequest, db: Session = Depends(get_db)):
        sess = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found.")
        if not req.demo_mode and model_loader.model is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Drone YOLO detector weights unavailable.",
                    "diagnostics": model_loader.get_diagnostics(),
                },
            )
        orchestrator.start_session(
            session_id=session_id,
            conf_threshold=req.conf_threshold,
            frame_stride=req.frame_stride,
            demo_mode=req.demo_mode,
            calibration_override=req.calibration,
        )
        return {"session_id": session_id, "status": "PROCESSING", "demo_mode": req.demo_mode}

    @router.post("/analyze/{session_id}/pause")
    def pause_analysis(session_id: str):
        if not orchestrator.pause_session(session_id):
            raise HTTPException(status_code=404, detail="Active session not found.")
        return {"session_id": session_id, "status": "PAUSED"}

    @router.post("/analyze/{session_id}/resume")
    def resume_analysis(session_id: str):
        if not orchestrator.resume_session(session_id):
            raise HTTPException(status_code=404, detail="Paused session not found.")
        return {"session_id": session_id, "status": "PROCESSING"}

    @router.post("/analyze/{session_id}/stop")
    def stop_analysis(session_id: str):
        if not orchestrator.stop_session(session_id):
            raise HTTPException(status_code=404, detail="Running session not found.")
        return {"session_id": session_id, "status": "STOPPED"}

    @router.get("/status/{session_id}")
    def get_status(session_id: str, db: Session = Depends(get_db)):
        sess = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found.")
        return {
            "session_id": sess.id,
            "filename": sess.filename,
            "status": sess.status,
            "error_message": sess.error_message,
            "frames_processed": sess.frames_processed,
            "total_frames": sess.total_frames,
            "duration_sec": sess.duration_sec,
            "fps": sess.fps,
            "processing_fps": sess.processing_fps,
            "is_demo_mode": sess.is_demo_mode,
        }

    @router.get("/detector/status")
    def detector_status():
        return model_loader.get_diagnostics()

    @router.post("/detector/configure")
    def configure_detector(req: DetectorConfigRequest):
        ok = model_loader.load(req.weights_path)
        return {"loaded": ok, "diagnostics": model_loader.get_diagnostics()}

    return router
