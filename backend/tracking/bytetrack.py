import math
from collections import deque
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import numpy as np
from scipy.optimize import linear_sum_assignment
from detection.detector import RawDetection


def compute_iou(box_a: Tuple[float, float, float, float], box_b: Tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    area_a = max(1e-5, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1e-5, (bx2 - bx1) * (by2 - by1))
    return inter / (area_a + area_b - inter)


class ConstantVelocityKalman2D:
    """8-state [cx, cy, w, h, vx, vy, vw, vh] linear Kalman filter for bounding-box motion."""

    def __init__(self, bbox: Tuple[float, float, float, float]):
        x1, y1, x2, y2 = bbox
        cx, cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
        w, h = max(2.0, x2 - x1), max(2.0, y2 - y1)
        self.x = np.array([cx, cy, w, h, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        self.P = np.eye(8, dtype=np.float32) * 10.0
        self.F = np.eye(8, dtype=np.float32)
        for i in range(4):
            self.F[i, i + 4] = 1.0
        self.H = np.eye(4, 8, dtype=np.float32)
        self.Q = np.eye(8, dtype=np.float32) * 0.5
        self.R = np.eye(4, dtype=np.float32) * 2.0

    def predict(self) -> Tuple[float, float, float, float]:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.current_bbox()

    def update(self, bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        x1, y1, x2, y2 = bbox
        z = np.array([(x1 + x2) * 0.5, (y1 + y2) * 0.5, max(2.0, x2 - x1), max(2.0, y2 - y1)], dtype=np.float32)
        y = z - (self.H @ self.x)
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + (K @ y)
        self.P = (np.eye(8, dtype=np.float32) - K @ self.H) @ self.P
        return self.current_bbox()

    def current_bbox(self) -> Tuple[float, float, float, float]:
        cx, cy, w, h = self.x[:4]
        w = max(2.0, float(w))
        h = max(2.0, float(h))
        return (float(cx - w * 0.5), float(cy - h * 0.5), float(cx + w * 0.5), float(cy + h * 0.5))


@dataclass
class DroneTrack:
    track_id: str
    numeric_id: int
    class_name: str
    bbox: Tuple[float, float, float, float]
    confidence: float
    kf: ConstantVelocityKalman2D
    last_frame: int
    last_timestamp: float
    state: str = "ACTIVE"  # ACTIVE, UNCERTAIN, LOST
    lost_frames: int = 0
    hits: int = 1
    reid_count: int = 0
    confidence_history: deque = field(default_factory=lambda: deque(maxlen=120))
    heading_deg: float = 0.0

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) * 0.5, (self.bbox[1] + self.bbox[3]) * 0.5)


class ByteTracker:
    """
    Two-stage ByteTrack association engine:
      - Stage 1: Associates high-confidence detections (>= high_thresh) with active/uncertain tracks via IoU + Hungarian matching.
      - Stage 2: Associates low-confidence detections (>= low_thresh) with remaining unmatched tracks to survive motion blur/occlusion.
      - Explicit uncertainty tracking: Tracks missing detections transition to UNCERTAIN before LOST, logging re-identification events.
    """

    def __init__(
        self,
        high_thresh: float = 0.50,
        low_thresh: float = 0.15,
        iou_thresh: float = 0.20,
        max_lost_frames: int = 25,
    ):
        self.high_thresh = high_thresh
        self.low_thresh = low_thresh
        self.iou_thresh = iou_thresh
        self.max_lost_frames = max_lost_frames
        self.next_id = 1
        self.tracks: Dict[str, DroneTrack] = {}

    def _new_track_id(self) -> Tuple[str, int]:
        nid = self.next_id
        self.next_id += 1
        return f"UAV-{nid:03d}", nid

    def _associate(
        self,
        track_list: List[DroneTrack],
        dets: List[RawDetection],
        iou_threshold: float,
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        if not track_list or not dets:
            return [], list(range(len(track_list))), list(range(len(dets)))

        cost_matrix = np.ones((len(track_list), len(dets)), dtype=np.float32)
        for ti, trk in enumerate(track_list):
            t_box = trk.bbox
            tcx, tcy = trk.center
            diag = max(20.0, math.hypot(t_box[2] - t_box[0], t_box[3] - t_box[1]))
            for di, det in enumerate(dets):
                d_box = (det.x1, det.y1, det.x2, det.y2)
                iou = compute_iou(t_box, d_box)
                dcx, dcy = det.center
                center_dist = math.hypot(tcx - dcx, tcy - dcy)
                norm_dist = min(1.0, center_dist / (diag * 2.5))
                score = 0.7 * iou + 0.3 * (1.0 - norm_dist)
                cost_matrix[ti, di] = 1.0 - score

        row_ind, col_ind = linear_sum_assignment(cost_matrix)
        matches = []
        unmatched_tracks = set(range(len(track_list)))
        unmatched_dets = set(range(len(dets)))

        for r, c in zip(row_ind, col_ind):
            if (1.0 - cost_matrix[r, c]) >= iou_threshold:
                matches.append((r, c))
                unmatched_tracks.discard(r)
                unmatched_dets.discard(c)

        return matches, sorted(unmatched_tracks), sorted(unmatched_dets)

    def update(
        self,
        detections: List[RawDetection],
        frame_id: int,
        timestamp: float,
    ) -> Tuple[List[DroneTrack], List[dict]]:
        events: List[dict] = []

        # Predict prior state for all live tracks
        live_tracks = [t for t in self.tracks.values() if t.state != "LOST"]
        for trk in live_tracks:
            trk.bbox = trk.kf.predict()

        high_dets = [d for d in detections if d.confidence >= self.high_thresh]
        low_dets = [d for d in detections if self.low_thresh <= d.confidence < self.high_thresh]

        # Stage 1: High-confidence association
        matches_1, unm_trk_idx_1, unm_high_idx = self._associate(live_tracks, high_dets, self.iou_thresh)

        matched_track_ids = set()
        for ti, di in matches_1:
            trk = live_tracks[ti]
            det = high_dets[di]
            self._apply_match(trk, det, frame_id, timestamp, events)
            matched_track_ids.add(trk.track_id)

        # Stage 2: Low-confidence recovery association on remaining tracks
        rem_tracks = [live_tracks[i] for i in unm_trk_idx_1]
        matches_2, unm_trk_idx_2, _ = self._associate(rem_tracks, low_dets, self.iou_thresh * 0.8)

        for ti, di in matches_2:
            trk = rem_tracks[ti]
            det = low_dets[di]
            self._apply_match(trk, det, frame_id, timestamp, events)
            matched_track_ids.add(trk.track_id)

        # Handle unmatched tracks -> mark UNCERTAIN or LOST
        for ti in unm_trk_idx_2:
            trk = rem_tracks[ti]
            trk.lost_frames += 1
            if trk.lost_frames > self.max_lost_frames:
                if trk.state != "LOST":
                    trk.state = "LOST"
                    events.append({
                        "track_id": trk.track_id,
                        "event_type": "TRACK_LOST",
                        "reason": f"Track {trk.track_id} lost after {trk.lost_frames} missed frames.",
                    })
            else:
                trk.state = "UNCERTAIN"

        # Spawn new tracks from unmatched high-confidence detections
        for di in unm_high_idx:
            det = high_dets[di]
            tid, nid = self._new_track_id()
            bbox = (det.x1, det.y1, det.x2, det.y2)
            kf = ConstantVelocityKalman2D(bbox)
            new_trk = DroneTrack(
                track_id=tid,
                numeric_id=nid,
                class_name=det.class_name,
                bbox=bbox,
                confidence=det.confidence,
                kf=kf,
                last_frame=frame_id,
                last_timestamp=timestamp,
                state="ACTIVE",
            )
            new_trk.confidence_history.append(det.confidence)
            self.tracks[tid] = new_trk
            events.append({
                "track_id": tid,
                "event_type": "TRACK_CREATED",
                "reason": f"New UAV track {tid} ({det.class_name}) acquired at conf={det.confidence*100:.1f}%.",
            })

        visible = [t for t in self.tracks.values() if t.state in ("ACTIVE", "UNCERTAIN")]
        return visible, events

    def _apply_match(
        self,
        trk: DroneTrack,
        det: RawDetection,
        frame_id: int,
        timestamp: float,
        events: List[dict],
    ) -> None:
        prev_cx, prev_cy = trk.center
        was_uncertain = trk.state == "UNCERTAIN"
        bbox = (det.x1, det.y1, det.x2, det.y2)
        trk.bbox = trk.kf.update(bbox)
        trk.confidence = det.confidence
        trk.confidence_history.append(det.confidence)
        trk.last_frame = frame_id
        trk.last_timestamp = timestamp
        trk.hits += 1

        new_cx, new_cy = trk.center
        dx, dy = new_cx - prev_cx, new_cy - prev_cy
        if math.hypot(dx, dy) > 0.5:
            trk.heading_deg = (math.degrees(math.atan2(dx, -dy)) + 360.0) % 360.0

        if was_uncertain:
            trk.reid_count += 1
            events.append({
                "track_id": trk.track_id,
                "event_type": "TRACK_REACQUIRED",
                "reason": f"Track {trk.track_id} re-acquired after {trk.lost_frames} occluded frames.",
            })
        trk.lost_frames = 0
        trk.state = "ACTIVE"
