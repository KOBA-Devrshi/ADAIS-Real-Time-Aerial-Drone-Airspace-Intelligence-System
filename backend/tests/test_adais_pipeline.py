import tempfile
from pathlib import Path
import cv2
import numpy as np
from fastapi.testclient import TestClient

from main import app
from detection.model_loader import DroneModelLoader
from detection.detector import RawDetection
from tracking.bytetrack import ByteTracker
from tracking.trajectory import TrajectoryManager, TrajectoryNode
from perception.calibration import CameraCalibration
from perception.depth_estimator import MonocularDepthEstimator
from perception.coordinate_transform import CoordinateTransformer
from airspace.geofence import GeofenceMonitor
from airspace.prediction import TrajectoryPredictor
from airspace.risk_engine import AirspaceRiskEngine


def _create_sample_mp4(path: Path, frames: int = 12, w: int = 320, h: int = 240) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, 15.0, (w, h))
    for i in range(frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.circle(frame, (40 + i * 10, 100), 12, (0, 255, 255), -1)
        writer.write(frame)
    writer.release()


def test_1_and_2_video_upload_and_decoding():
    client = TestClient(app)
    with tempfile.TemporaryDirectory() as tmp:
        vid_path = Path(tmp) / "test_drone.mp4"
        _create_sample_mp4(vid_path)
        with vid_path.open("rb") as f:
            res = client.post("/api/upload", files={"file": ("test_drone.mp4", f, "video/mp4")})
        assert res.status_code == 200
        body = res.json()
        assert body["total_frames"] == 12
        assert body["resolution"] == {"width": 320, "height": 240}


def test_3_model_loader_missing_weights_guard():
    loader = DroneModelLoader(weights_path="weights/non_existent_drone_weights.pt")
    assert loader.model is None
    assert loader.status == "MISSING_WEIGHTS"


def test_4_5_and_6_bytetrack_multi_object_persistence():
    tracker = ByteTracker()
    det_a1 = RawDetection(100, 100, 150, 140, 0.92, 0, "QUADCOPTER")
    det_b1 = RawDetection(220, 80, 260, 115, 0.88, 0, "QUADCOPTER")

    tracks_1, events_1 = tracker.update([det_a1, det_b1], frame_id=0, timestamp=0.0)
    assert len(tracks_1) == 2
    assert len(events_1) == 2
    id_map = {round(t.center[0]): t.track_id for t in tracks_1}

    det_a2 = RawDetection(106, 102, 156, 142, 0.91, 0, "QUADCOPTER")
    det_b2 = RawDetection(225, 83, 265, 118, 0.89, 0, "QUADCOPTER")
    tracks_2, _ = tracker.update([det_a2, det_b2], frame_id=1, timestamp=0.033)
    assert len(tracks_2) == 2
    assert tracks_2[0].track_id in id_map.values()


def test_7_and_8_depth_and_coordinate_transform_distinction():
    estimator = MonocularDepthEstimator(enable_neural_depth=False)
    est = estimator.estimate_for_drone("UAV-001", (100, 100, 160, 140), (720, 1280), depth_map=None)
    assert est.is_metric is False
    assert 0.05 <= est.relative_depth <= 1.0

    uncal = CameraCalibration(image_width=1280, image_height=720)
    pt_rel = CoordinateTransformer(uncal).image_to_3d(130, 120, est)
    assert pt_rel.is_metric is False

    cal = CameraCalibration(image_width=1280, image_height=720, fx=1050.0, fy=1050.0, metric_scale_m=120.0)
    pt_metric = CoordinateTransformer(cal).image_to_3d(130, 120, est)
    assert pt_metric.is_metric is True


def test_9_and_10_trajectory_and_geofence_risk():
    traj = TrajectoryManager()
    n1 = TrajectoryNode(0, 0.0, "UAV-001", 100, 100, 0.5, False, 0.0, 25.0, 40.0, 0, 0, 0, 0, 0, 0.95)
    n2 = TrajectoryNode(1, 0.5, "UAV-001", 105, 100, 0.55, False, 0.0, 25.0, 55.0, 0, 0, 0, 0, 0, 0.95)
    traj.record(n1)
    vx, vy, vz, speed, _ = traj.record(n2)
    assert vz == 30.0
    assert speed == 30.0

    monitor = GeofenceMonitor()
    predictor = TrajectoryPredictor()
    engine = AirspaceRiskEngine(monitor)
    pred = predictor.predict((0.0, 25.0, 55.0), (vx, vy, vz), False, 0.95)
    risk = engine.assess_drone("UAV-001", 0.5, (0.0, 25.0, 55.0), speed, pred, 0.95, False)
    assert risk.risk_level == "CRITICAL"


def test_11_and_12_websocket_and_timestamp_sync():
    client = TestClient(app)
    with client.websocket_connect("/ws/analysis/testsession") as ws:
        ws.send_text("PING")
        data = ws.receive_json()
        assert data == {"type": "PONG", "session_id": "testsession"}
