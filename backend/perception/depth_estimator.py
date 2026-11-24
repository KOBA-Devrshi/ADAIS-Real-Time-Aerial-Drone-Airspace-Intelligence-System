import os
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import cv2
import numpy as np
import torch


@dataclass
class DepthEstimate:
    relative_depth: float          # Normalized [0.05, 1.0], higher = further from camera
    depth_confidence: float        # [0.0, 1.0] reliability indicator
    is_metric: bool                # False for monocular relative depth
    method: str                    # "MIDAS_MONOCULAR" or "APPARENT_SCALE_RELATIVE"


class MonocularDepthEstimator:
    """
    Monocular spatial depth estimation pipeline.
    Conventions:
    - Generates per-frame inverse depth map via MiDaS when enabled.
    - Extracts robust median depth inside inner 50% of the drone bounding box
      to reject background sky/ground bleed.
    - Applies exponential moving average (EMA) temporal smoothing per track_id.
    - Explicitly distinguishes relative monocular depth from physical metric depth.
    """

    def __init__(self, enable_neural_depth: Optional[bool] = None, ema_alpha: float = 0.35):
        env_flag = os.getenv("ENABLE_DEPTH_MODEL", "true").lower() == "true"
        self.enable_neural = env_flag if enable_neural_depth is None else enable_neural_depth
        self.ema_alpha = ema_alpha
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.transform = None
        self.model_status = "UNINITIALIZED"
        self._smoothed_depth: Dict[str, float] = {}
        self._load_model()

    def _load_model(self) -> None:
        if not self.enable_neural:
            self.model_status = "DISABLED_BY_CONFIG"
            return
        try:
            model_type = os.getenv("DEPTH_MODEL_TYPE", "MiDaS_small")
            self.model = torch.hub.load("intel-isl/MiDaS", model_type, trust_repo=True)
            self.model.to(self.device).eval()
            midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms", trust_repo=True)
            self.transform = (
                midas_transforms.small_transform
                if "small" in model_type.lower()
                else midas_transforms.dpt_transform
            )
            self.model_status = f"READY ({model_type})"
        except Exception as exc:
            self.model = None
            self.model_status = f"FALLBACK_ACTIVE ({exc})"

    def compute_depth_map(self, frame_bgr: np.ndarray) -> Optional[np.ndarray]:
        if self.model is None or self.transform is None:
            return None
        try:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            input_batch = self.transform(rgb).to(self.device)
            with torch.no_grad():
                prediction = self.model(input_batch)
                prediction = torch.nn.functional.interpolate(
                    prediction.unsqueeze(1),
                    size=rgb.shape[:2],
                    mode="bicubic",
                    align_corners=False,
                ).squeeze()
            inv_depth = prediction.cpu().numpy()
            d_min, d_max = float(np.min(inv_depth)), float(np.max(inv_depth))
            if d_max - d_min < 1e-6:
                return None
            norm_inv = (inv_depth - d_min) / (d_max - d_min)
            rel_distance = np.clip(1.0 - norm_inv * 0.90, 0.05, 1.0)
            return rel_distance.astype(np.float32)
        except Exception:
            return None

    def estimate_for_drone(
        self,
        track_id: str,
        bbox: Tuple[float, float, float, float],
        frame_shape: Tuple[int, ...],
        depth_map: Optional[np.ndarray] = None,
    ) -> DepthEstimate:
        h, w = frame_shape[:2]
        x1, y1, x2, y2 = bbox
        bw = max(2.0, x2 - x1)
        bh = max(2.0, y2 - y1)

        if depth_map is not None:
            ix1 = int(np.clip(x1 + bw * 0.25, 0, w - 1))
            iy1 = int(np.clip(y1 + bh * 0.25, 0, h - 1))
            ix2 = int(np.clip(x2 - bw * 0.25, ix1 + 1, w))
            iy2 = int(np.clip(y2 - bh * 0.25, iy1 + 1, h))
            patch = depth_map[iy1:iy2, ix1:ix2]
            if patch.size > 0:
                raw_depth = float(np.median(patch))
                spread = float(np.std(patch))
                conf = float(np.clip(1.0 - spread * 2.0, 0.35, 0.95))
                smoothed = self._smooth(track_id, raw_depth)
                return DepthEstimate(
                    relative_depth=smoothed,
                    depth_confidence=conf,
                    is_metric=False,
                    method="MIDAS_MONOCULAR",
                )

        diag_ratio = np.hypot(bw, bh) / max(1.0, np.hypot(w, h))
        raw_proxy = float(np.clip(0.08 / max(diag_ratio, 0.015), 0.08, 1.0))
        smoothed = self._smooth(track_id, raw_proxy)
        return DepthEstimate(
            relative_depth=smoothed,
            depth_confidence=0.40,
            is_metric=False,
            method="APPARENT_SCALE_RELATIVE",
        )

    def _smooth(self, track_id: str, value: float) -> float:
        prev = self._smoothed_depth.get(track_id)
        if prev is None:
            self._smoothed_depth[track_id] = value
            return value
        ema = self.ema_alpha * value + (1.0 - self.ema_alpha) * prev
        self._smoothed_depth[track_id] = ema
        return float(ema)
