import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.database import init_db
from detection.model_loader import DroneModelLoader
from detection.detector import DroneDetector
from perception.depth_estimator import MonocularDepthEstimator
from processing.video_processor import VideoAnalysisOrchestrator
from api.upload import router as upload_router
from api.tracking import router as tracking_router
from api.websocket import router as ws_router, ws_manager
from api.analysis import create_analysis_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ADAIS — Autonomous Drone Airspace Intelligence System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_loader = DroneModelLoader()
detector = DroneDetector(
    loader=model_loader,
    conf_threshold=float(os.getenv("YOLO_CONF_THRESHOLD", "0.45")),
    imgsz=int(os.getenv("YOLO_IMGSZ", "640")),
)
depth_estimator = MonocularDepthEstimator()
orchestrator = VideoAnalysisOrchestrator(
    detector=detector,
    depth_estimator=depth_estimator,
    ws_manager=ws_manager,
)

app.include_router(upload_router)
app.include_router(create_analysis_router(orchestrator, model_loader))
app.include_router(tracking_router)
app.include_router(ws_router)


@app.get("/api/health")
def health_check():
    return {
        "system": "ADAIS",
        "status": "ONLINE",
        "detector": model_loader.get_diagnostics(),
        "depth_engine": depth_estimator.model_status,
    }
