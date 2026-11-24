import math
from dataclasses import dataclass
from perception.calibration import CameraCalibration
from perception.depth_estimator import DepthEstimate


@dataclass
class SpatialPoint3D:
    x: float
    y: float
    z: float
    is_metric: bool
    frame_label: str


class CoordinateTransformer:
    """
    Converts 2D pixel coordinates + depth estimate into 3D airspace coordinates.
    Three.js / Airspace convention:
      - X: lateral horizontal axis (-left / +right)
      - Y: vertical elevation axis (+up above ground plane)
      - Z: forward depth axis (+away from sensor)
    """

    def __init__(self, calibration: CameraCalibration, virtual_range_units: float = 100.0):
        self.calibration = calibration
        self.virtual_range_units = virtual_range_units

    def image_to_3d(self, cx: float, cy: float, depth_est: DepthEstimate) -> SpatialPoint3D:
        fx, fy, u0, v0 = self.calibration.effective_intrinsics()

        if self.calibration.is_metric_calibrated and self.calibration.metric_scale_m is not None:
            z_cam = depth_est.relative_depth * self.calibration.metric_scale_m
            x_cam = ((cx - u0) / fx) * z_cam
            y_cam = -((cy - v0) / fy) * z_cam

            pitch = math.radians(self.calibration.camera_pitch_deg)
            y_world = (
                y_cam * math.cos(pitch)
                + z_cam * math.sin(pitch)
                + self.calibration.camera_altitude_m
            )
            z_world = -y_cam * math.sin(pitch) + z_cam * math.cos(pitch)
            return SpatialPoint3D(
                x=round(x_cam, 3),
                y=round(max(0.0, y_world), 3),
                z=round(z_world, 3),
                is_metric=True,
                frame_label="CALIBRATED_METRIC_WORLD",
            )

        z_rel = depth_est.relative_depth * self.virtual_range_units
        x_rel = ((cx - u0) / fx) * z_rel
        y_rel = max(1.0, (-((cy - v0) / fy) * z_rel) + (self.virtual_range_units * 0.35))

        return SpatialPoint3D(
            x=round(x_rel, 3),
            y=round(y_rel, 3),
            z=round(z_rel, 3),
            is_metric=False,
            frame_label="RELATIVE_CAMERA_SPACE",
        )
