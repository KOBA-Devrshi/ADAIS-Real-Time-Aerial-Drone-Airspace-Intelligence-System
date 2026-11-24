import os
import shutil
import uuid
from pathlib import Path
import cv2
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import AnalysisSession

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = int(os.getenv("MAX_UPLOAD_MB", "500")) * 1024 * 1024


@router.post("/upload")
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed formats: MP4, MOV, AVI, MKV.",
        )

    session_id = uuid.uuid4().hex[:12]
    session_folder = UPLOAD_DIR / session_id
    session_folder.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    dest_path = session_folder / safe_name

    size_bytes = 0
    with dest_path.open("wb") as buffer:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            if size_bytes > MAX_BYTES:
                buffer.close()
                shutil.rmtree(session_folder, ignore_errors=True)
                raise HTTPException(status_code=413, detail="Video exceeds maximum allowed upload size.")
            buffer.write(chunk)

    cap = cv2.VideoCapture(str(dest_path))
    if not cap.isOpened():
        shutil.rmtree(session_folder, ignore_errors=True)
        raise HTTPException(status_code=422, detail="File could not be decoded as a valid video stream.")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = round(total_frames / fps, 2) if fps > 0 else 0.0
    cap.release()

    if total_frames <= 0 or width <= 0 or height <= 0:
        shutil.rmtree(session_folder, ignore_errors=True)
        raise HTTPException(status_code=422, detail="Corrupted or empty video stream metadata.")

    session_row = AnalysisSession(
        id=session_id,
        filename=safe_name,
        filepath=str(dest_path),
        file_size_bytes=size_bytes,
        duration_sec=duration,
        fps=round(fps, 2),
        width=width,
        height=height,
        total_frames=total_frames,
        status="UPLOADED",
    )
    db.add(session_row)
    db.commit()

    return {
        "session_id": session_id,
        "filename": safe_name,
        "file_size_bytes": size_bytes,
        "duration_sec": duration,
        "fps": round(fps, 2),
        "resolution": {"width": width, "height": height},
        "total_frames": total_frames,
        "video_url": f"/api/video/{session_id}",
        "status": "UPLOADED",
    }


@router.get("/video/{session_id}")
def stream_uploaded_video(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not sess or not Path(sess.filepath).exists():
        raise HTTPException(status_code=404, detail="Session video not found.")
    return FileResponse(sess.filepath, filename=sess.filename)
