from dataclasses import dataclass
from typing import Optional


@dataclass
class CameraCalibration:
    """
    Camera intrinsic and optional metric-scale calibration parameters.
    - When is_metric_calibrated=False: 3D outputs represent normalized camera-space
      coordinates derived from monocular relative depth (NOT physical altitude).
    - When is_metric_calibrated=True: Pinhole back-projection + metric scale factor
      (from stereo baseline, LiDAR, or known UAV wingspan reference) produces
      metric camera-frame (X, Y, Z) in meters.
    """
    image_width: int
    image_height: int
    fx: Optional[float] = None
    fy: Optional[float] = None
    cx: Optional[float] = None
    cy: Optional[float] = None
    metric_scale_m: Optional[float] = None
    camera_pitch_deg: float = 0.0
    camera_altitude_m: float = 0.0

    @property
    def is_metric_calibrated(self) -> bool:
        return (
            self.fx is not None
            and self.fy is not None
            and self.metric_scale_m is not None
            and self.metric_scale_m > 0
        )

    def effective_intrinsics(self) -> tuple[float, float, float, float]:
        fx = self.fx if self.fx is not None else float(self.image_width) * 0.85
        fy = self.fy if self.fy is not None else float(self.image_width) * 0.85
        cx = self.cx if self.cx is not None else float(self.image_width) * 0.5
        cy = self.cy if self.cy is not None else float(self.image_height) * 0.5
        return fx, fy, cx, cy
