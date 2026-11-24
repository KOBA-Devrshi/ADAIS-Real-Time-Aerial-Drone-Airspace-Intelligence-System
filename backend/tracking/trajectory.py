import math
from collections import deque
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple


@dataclass
class TrajectoryNode:
    frame_id: int
    timestamp: float
    track_id: str
    image_x: float
    image_y: float
    relative_depth: float
    is_metric: bool
    pos_x: float
    pos_y: float
    pos_z: float
    vx: float
    vy: float
    vz: float
    speed: float
    heading_deg: float
    confidence: float


class TrajectoryManager:
    """Maintains bounded per-track 2D + 3D trajectory history and computes kinematic velocity."""

    def __init__(self, max_history: int = 300):
        self.max_history = max_history
        self.histories: Dict[str, deque[TrajectoryNode]] = {}

    def record(self, node: TrajectoryNode) -> Tuple[float, float, float, float, float]:
        buf = self.histories.setdefault(node.track_id, deque(maxlen=self.max_history))
        if buf:
            prev = buf[-1]
            dt = max(1e-3, node.timestamp - prev.timestamp)
            vx = (node.pos_x - prev.pos_x) / dt
            vy = (node.pos_y - prev.pos_y) / dt
            vz = (node.pos_z - prev.pos_z) / dt
            # Exponential smoothing on velocity vector to suppress monocular depth jitter
            alpha = 0.45
            node.vx = alpha * vx + (1.0 - alpha) * prev.vx
            node.vy = alpha * vy + (1.0 - alpha) * prev.vy
            node.vz = alpha * vz + (1.0 - alpha) * prev.vz
            node.speed = math.sqrt(node.vx ** 2 + node.vy ** 2 + node.vz ** 2)
            if math.hypot(node.vx, node.vz) > 0.05:
                node.heading_deg = (math.degrees(math.atan2(node.vx, node.vz)) + 360.0) % 360.0

        buf.append(node)
        return node.vx, node.vy, node.vz, node.speed, node.heading_deg

    def get_path(self, track_id: str, up_to_timestamp: float | None = None) -> List[dict]:
        buf = self.histories.get(track_id, deque())
        if up_to_timestamp is None:
            return [asdict(n) for n in buf]
        return [asdict(n) for n in buf if n.timestamp <= up_to_timestamp]

    def get_all_paths(self, up_to_timestamp: float | None = None) -> Dict[str, List[dict]]:
        return {
            tid: self.get_path(tid, up_to_timestamp=up_to_timestamp)
            for tid in self.histories
        }
