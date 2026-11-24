from dataclasses import dataclass
from typing import List
import numpy as np
from detection.model_loader import DroneModelLoader


@dataclass
class RawDetection:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) * 0.5, (self.y1 + self.y2) * 0.5)


class DroneDetector:
    def __init__(self, loader: DroneModelLoader, conf_threshold: float = 0.45, imgsz: int = 640):
        self.loader = loader
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz

    @property
    def is_ready(self) -> bool:
        return self.loader.model is not None

    def detect(self, frame_bgr: np.ndarray, conf_threshold: float | None = None) -> List[RawDetection]:
        if not self.is_ready:
            raise RuntimeError(self.loader.error_detail or "Drone detector model is not loaded.")

        conf = conf_threshold if conf_threshold is not None else self.conf_threshold
        results = self.loader.model.predict(
            source=frame_bgr,
            conf=conf,
            imgsz=self.imgsz,
            device=self.loader.device,
            verbose=False,
        )

        detections: List[RawDetection] = []
        if not results:
            return detections

        res = results[0]
        if res.boxes is None:
            return detections

        boxes_xyxy = res.boxes.xyxy.cpu().numpy()
        confs = res.boxes.conf.cpu().numpy()
        clss = res.boxes.cls.cpu().numpy().astype(int)
        names = getattr(res, "names", {}) or {}

        for box, score, cid in zip(boxes_xyxy, confs, clss):
            raw_label = str(names.get(int(cid), "QUADCOPTER")).upper()
            label = "QUADCOPTER" if raw_label in ("DRONE", "UAV", "0") else raw_label
            detections.append(
                RawDetection(
                    x1=float(box[0]),
                    y1=float(box[1]),
                    x2=float(box[2]),
                    y2=float(box[3]),
                    confidence=float(score),
                    class_id=int(cid),
                    class_name=label,
                )
            )
        return detections
