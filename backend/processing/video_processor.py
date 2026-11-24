import asyncio
import math
import time
from pathlib import Path
from typing import Dict, Optional, List
import cv2
import numpy as np

from database.database import SessionLocal
from database.models import AnalysisSession, DetectionRecord, TrackRecord, AirspaceEvent
from detection.detector import DroneDetector, RawDetection
from tracking.bytetrack import ByteTracker
from tracking.trajectory import TrajectoryManager, TrajectoryNode
from perception.calibration import CameraCalibration
from perception.depth_estimator import MonocularDepthEstimator
from perception.coordinate_transform import CoordinateTransformer
from airspace.geofence import GeofenceMonitor
from airspace.prediction import TrajectoryPredictor
from airspace.risk_engine import AirspaceRiskEngine, RISK_ORDER
from processing.frame_manager import draw_hud_annotations


class SessionRuntimeController:
    def __init__(self):
        self.pause_event = asyncio.Event()
        self.pause_event.set()
        self.stop_requested = False


class VideoAnalysisOrchestrator:
    def __init__(self, detector: DroneDetector, depth_estimator: MonocularDepthEstimator, ws_manager):
        self.detector = detector
        self.depth_estimator = depth_estimator
        self.ws_manager = ws_manager
        self.controllers: Dict[str, SessionRuntimeController] = {}
        self.tasks: Dict[str, asyncio.Task] = {}

    def start_session(
        self,
        session_id: str,
        conf_threshold: float = 0.45,
        frame_stride: int = 1,
        demo_mode: bool = False,
        calibration_override: Optional[dict] = None,
    ) -> None:
        if session_id in self.tasks and not self.tasks[session_id].done():
            raise RuntimeError(f"Session {session_id} is already running.")

        ctrl = SessionRuntimeController()
        self.controllers[session_id] = ctrl
        task = asyncio.create_task(
            self._run_pipeline(
                session_id=session_id,
                ctrl=ctrl,
                conf_threshold=conf_threshold,
                frame_stride=max(1, frame_stride),
                demo_mode=demo_mode,
                calibration_override=calibration_override,
            )
        )
        self.tasks[session_id] = task

    def pause_session(self, session_id: str) -> bool:
        ctrl = self.controllers.get(session_id)
        if not ctrl:
            return False
        ctrl.pause_event.clear()
        self._update_status(session_id, "PAUSED")
        return True

    def resume_session(self, session_id: str) -> bool:
        ctrl = self.controllers.get(session_id)
        if not ctrl:
            return False
        ctrl.pause_event.set()
        self._update_status(session_id, "PROCESSING")
        return True

    def stop_session(self, session_id: str) -> bool:
        ctrl = self.controllers.get(session_id)
        if not ctrl:
            return False
        ctrl.stop_requested = True
        ctrl.pause_event.set()
        return True

    def _update_status(self, session_id: str, status: str, error: Optional[str] = None) -> None:
        db = SessionLocal()
        try:
            sess = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
            if sess:
                sess.status = status
                if error:
                    sess.error_message = error
                db.commit()
        finally:
            db.close()

    def _generate_demo_detections(self, frame_id: int, w: int, h: int) -> List[RawDetection]:
        t = frame_id * 0.04
        cx = w * (0.5 + 0.28 * math.sin(t))
        cy = h * (0.42 + 0.16 * math.cos(t * 0.7))
        scale = 1.0 + 0.25 * math.sin(t * 0.5)
        bw, bh = 74.0 * scale, 44.0 * scale
        return [
            RawDetection(
                x1=cx - bw * 0.5,
                y1=cy - bh * 0.5,
                x2=cx + bw * 0.5,
                y2=cy + bh * 0.5,
                confidence=0.94,
                class_id=0,
                class_name="QUADCOPTER [DEMO]",
            )
        ]

    async def _run_pipeline(
        self,
        session_id: str,
        ctrl: SessionRuntimeController,
        conf_threshold: float,
        frame_stride: int,
        demo_mode: bool,
        calibration_override: Optional[dict],
    ) -> None:
        db = SessionLocal()
        cap = None
        writer = None

        try:
            sess = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
            if not sess:
                return

            if not demo_mode and not self.detector.is_ready:
                sess.status = "ERROR"
                sess.error_message = self.detector.loader.error_detail
                db.commit()
                await self.ws_manager.broadcast(session_id, {
                    "type": "ERROR",
                    "session_id": session_id,
                    "message": sess.error_message,
                })
                return

            db.query(DetectionRecord).filter(DetectionRecord.session_id == session_id).delete()
            db.query(TrackRecord).filter(TrackRecord.session_id == session_id).delete()
            db.query(AirspaceEvent).filter(AirspaceEvent.session_id == session_id).delete()
            sess.status = "PROCESSING"
            sess.error_message = None
            sess.frames_processed = 0
            sess.is_demo_mode = demo_mode
            db.commit()

            cap = cv2.VideoCapture(sess.filepath)
            if not cap.isOpened():
                raise RuntimeError(f"Unable to decode video stream: {sess.filename}")

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            annotated_path = str(Path(sess.filepath).with_name(f"{session_id}_annotated.mp4"))
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(annotated_path, fourcc, fps, (width, height))

            cal_cfg = calibration_override or {}
            calibration = CameraCalibration(
                image_width=width,
                image_height=height,
                fx=cal_cfg.get("fx"),
                fy=cal_cfg.get("fy"),
                cx=cal_cfg.get("cx"),
                cy=cal_cfg.get("cy"),
                metric_scale_m=cal_cfg.get("metric_scale_m"),
                camera_pitch_deg=cal_cfg.get("camera_pitch_deg", 0.0),
                camera_altitude_m=cal_cfg.get("camera_altitude_m", 0.0),
            )

            tracker = ByteTracker()
            traj_manager = TrajectoryManager(max_history=300)
            coord_tx = CoordinateTransformer(calibration)
            geofence_mon = GeofenceMonitor()
            predictor = TrajectoryPredictor()
            risk_engine = AirspaceRiskEngine(geofence_mon)

            track_db_map: Dict[str, TrackRecord] = {}
            frame_id = 0
            processed_count = 0
            t_start = time.perf_counter()

            while True:
                await ctrl.pause_event.wait()
                if ctrl.stop_requested:
                    sess.status = "STOPPED"
                    db.commit()
                    await self.ws_manager.broadcast(session_id, {"type": "STOPPED", "session_id": session_id})
                    break

                ret, frame = cap.read()
                if not ret:
                    sess.status = "COMPLETED"
                    sess.annotated_filepath = annotated_path
                    db.commit()
                    await self.ws_manager.broadcast(session_id, {"type": "COMPLETED", "session_id": session_id})
                    break

                timestamp = round(frame_id / fps, 4)

                if frame_id % frame_stride == 0:
                    if demo_mode:
                        raw_dets = self._generate_demo_detections(frame_id, width, height)
                        depth_map = None
                    else:
                        raw_dets = await asyncio.to_thread(self.detector.detect, frame, conf_threshold)
                        depth_map = await asyncio.to_thread(self.depth_estimator.compute_depth_map, frame)

                    active_tracks, track_events = tracker.update(raw_dets, frame_id, timestamp)

                    frame_detections_payload = []
                    frame_events_payload = []
                    highest_risk = "LOW"

                    for ev in track_events:
                        ev_obj = AirspaceEvent(
                            session_id=session_id,
                            frame_id=frame_id,
                            timestamp=timestamp,
                            track_id=ev["track_id"],
                            event_type=ev["event_type"],
                            risk_level="LOW",
                            reason=ev["reason"],
                        )
                        db.add(ev_obj)
                        frame_events_payload.append({
                            "frame_id": frame_id,
                            "timestamp": timestamp,
                            "track_id": ev["track_id"],
                            "event_type": ev["event_type"],
                            "risk_level": "LOW",
                            "reason": ev["reason"],
                        })

                    for trk in active_tracks:
                        depth_est = self.depth_estimator.estimate_for_drone(
                            trk.track_id, trk.bbox, frame.shape, depth_map
                        )
                        pt3d = coord_tx.image_to_3d(trk.center[0], trk.center[1], depth_est)

                        node = TrajectoryNode(
                            frame_id=frame_id,
                            timestamp=timestamp,
                            track_id=trk.track_id,
                            image_x=round(trk.center[0], 1),
                            image_y=round(trk.center[1], 1),
                            relative_depth=round(depth_est.relative_depth, 4),
                            is_metric=pt3d.is_metric,
                            pos_x=pt3d.x,
                            pos_y=pt3d.y,
                            pos_z=pt3d.z,
                            vx=0.0,
                            vy=0.0,
                            vz=0.0,
                            speed=0.0,
                            heading_deg=trk.heading_deg,
                            confidence=round(trk.confidence, 4),
                        )
                        vx, vy, vz, speed, heading = traj_manager.record(node)

                        pred_path = predictor.predict(
                            pos=(pt3d.x, pt3d.y, pt3d.z),
                            vel=(vx, vy, vz),
                            is_metric=pt3d.is_metric,
                            base_confidence=trk.confidence,
                        )

                        risk = risk_engine.assess_drone(
                            track_id=trk.track_id,
                            timestamp=timestamp,
                            pos=(pt3d.x, pt3d.y, pt3d.z),
                            speed=speed,
                            predicted_path=pred_path,
                            confidence=trk.confidence,
                            is_metric=pt3d.is_metric,
                        )
                        if RISK_ORDER[risk.risk_level] > RISK_ORDER[highest_risk]:
                            highest_risk = risk.risk_level

                        if risk.risk_level in ("MEDIUM", "HIGH", "CRITICAL"):
                            alert_ev = AirspaceEvent(
                                session_id=session_id,
                                frame_id=frame_id,
                                timestamp=timestamp,
                                track_id=trk.track_id,
                                event_type="GEOFENCE_ALERT",
                                risk_level=risk.risk_level,
                                zone_name=risk.zone_name,
                                reason=risk.reason,
                                position=risk.position,
                                confidence=risk.confidence,
                            )
                            db.add(alert_ev)
                            frame_events_payload.append({
                                "frame_id": frame_id,
                                "timestamp": timestamp,
                                "track_id": trk.track_id,
                                "event_type": "GEOFENCE_ALERT",
                                "risk_level": risk.risk_level,
                                "zone_name": risk.zone_name,
                                "reason": risk.reason,
                            })

                        det_row = DetectionRecord(
                            session_id=session_id,
                            frame_id=frame_id,
                            timestamp=timestamp,
                            track_id=trk.track_id,
                            drone_class=trk.class_name,
                            confidence=round(trk.confidence, 4),
                            track_status=trk.state,
                            x1=round(trk.bbox[0], 2),
                            y1=round(trk.bbox[1], 2),
                            x2=round(trk.bbox[2], 2),
                            y2=round(trk.bbox[3], 2),
                            cx=round(trk.center[0], 2),
                            cy=round(trk.center[1], 2),
                            relative_depth=round(depth_est.relative_depth, 4),
                            depth_confidence=round(depth_est.depth_confidence, 3),
                            is_metric=pt3d.is_metric,
                            pos_x=pt3d.x,
                            pos_y=pt3d.y,
                            pos_z=pt3d.z,
                            vx=round(vx, 3),
                            vy=round(vy, 3),
                            vz=round(vz, 3),
                            speed=round(speed, 3),
                            heading_deg=round(heading, 1),
                        )
                        db.add(det_row)

                        if trk.track_id not in track_db_map:
                            tr_row = TrackRecord(
                                session_id=session_id,
                                track_id=trk.track_id,
                                drone_class=trk.class_name,
                                first_seen_frame=frame_id,
                                last_seen_frame=frame_id,
                                first_seen_ts=timestamp,
                                last_seen_ts=timestamp,
                                avg_confidence=round(trk.confidence, 4),
                                status=trk.state,
                                reid_count=trk.reid_count,
                            )
                            db.add(tr_row)
                            track_db_map[trk.track_id] = tr_row
                        else:
                            tr_row = track_db_map[trk.track_id]
                            tr_row.last_seen_frame = frame_id
                            tr_row.last_seen_ts = timestamp
                            tr_row.avg_confidence = round(float(np.mean(trk.confidence_history)), 4)
                            tr_row.status = trk.state
                            tr_row.reid_count = trk.reid_count

                        frame_detections_payload.append({
                            "frame_id": frame_id,
                            "timestamp": timestamp,
                            "track_id": trk.track_id,
                            "class": trk.class_name,
                            "confidence": round(trk.confidence, 4),
                            "track_status": trk.state,
                            "bbox": {
                                "x1": round(trk.bbox[0], 1),
                                "y1": round(trk.bbox[1], 1),
                                "x2": round(trk.bbox[2], 1),
                                "y2": round(trk.bbox[3], 1),
                            },
                            "center": {"x": round(trk.center[0], 1), "y": round(trk.center[1], 1)},
                            "spatial": {
                                "x": pt3d.x,
                                "y": pt3d.y,
                                "z": pt3d.z,
                                "relative_depth": round(depth_est.relative_depth, 4),
                                "depth_confidence": round(depth_est.depth_confidence, 3),
                                "is_metric": pt3d.is_metric,
                                "frame_label": pt3d.frame_label,
                                "depth_method": depth_est.method,
                            },
                            "motion": {
                                "vx": round(vx, 2),
                                "vy": round(vy, 2),
                                "vz": round(vz, 2),
                                "speed": round(speed, 2),
                                "heading_deg": round(heading, 1),
                            },
                            "predicted_trajectory": pred_path,
                            "risk_level": risk.risk_level,
                            "risk_reason": risk.reason,
                        })

                    processed_count += 1
                    elapsed = max(1e-3, time.perf_counter() - t_start)
                    proc_fps = round(processed_count / elapsed, 2)

                    sess.frames_processed = processed_count
                    sess.processing_fps = proc_fps
                    if processed_count % 15 == 0:
                        db.commit()

                    if writer is not None:
                        annotated = draw_hud_annotations(frame, frame_detections_payload, is_demo=demo_mode)
                        writer.write(annotated)

                    await self.ws_manager.broadcast(session_id, {
                        "type": "FRAME_UPDATE",
                        "session_id": session_id,
                        "frame_id": frame_id,
                        "total_frames": total_frames,
                        "timestamp": timestamp,
                        "processing_fps": proc_fps,
                        "is_demo_mode": demo_mode,
                        "airspace_risk": highest_risk,
                        "detections": frame_detections_payload,
                        "trajectories": traj_manager.get_all_paths(),
                        "events": frame_events_payload,
                    })

                frame_id += 1
                await asyncio.sleep(0)

        except Exception as exc:
            self._update_status(session_id, "ERROR", str(exc))
            await self.ws_manager.broadcast(session_id, {
                "type": "ERROR",
                "session_id": session_id,
                "message": str(exc),
            })
        finally:
            if cap is not None:
                cap.release()
            if writer is not None:
                writer.release()
            db.close()
