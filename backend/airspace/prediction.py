from typing import List, Tuple


class TrajectoryPredictor:
    """Short-term kinematic trajectory extrapolation with explicit uncertainty growth."""

    def __init__(self, horizon_sec: float = 2.0, steps: int = 5):
        self.horizon_sec = horizon_sec
        self.steps = steps

    def predict(
        self,
        pos: Tuple[float, float, float],
        vel: Tuple[float, float, float],
        is_metric: bool,
        base_confidence: float,
    ) -> List[dict]:
        px, py, pz = pos
        vx, vy, vz = vel
        points = []
        dt_step = self.horizon_sec / max(1, self.steps)

        for i in range(1, self.steps + 1):
            t = i * dt_step
            scale_factor = 1.0 if is_metric else 2.2
            uncertainty = round((1.0 - base_confidence * 0.5) * t * 3.5 * scale_factor, 2)
            points.append({
                "dt": round(t, 2),
                "x": round(px + vx * t, 3),
                "y": round(max(0.0, py + vy * t), 3),
                "z": round(pz + vz * t, 3),
                "uncertainty_radius": uncertainty,
                "is_metric": is_metric,
            })
        return points
