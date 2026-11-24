import os
from pathlib import Path
from typing import Optional, Dict
import torch


class DroneModelLoader:
    """
    Loads custom drone-specific YOLO weights strictly without silently falling back
    to generic COCO weights (which fail to reliably detect small aerial UAVs).
    """

    def __init__(self, weights_path: Optional[str] = None):
        default_path = os.getenv("DRONE_MODEL_WEIGHTS", "weights/drone_best.pt")
        self.weights_path = weights_path or default_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.status = "UNINITIALIZED"
        self.error_detail: Optional[str] = None
        self.class_names: Dict[str, str] = {}
        self.load(self.weights_path)

    def load(self, weights_path: str) -> bool:
        self.weights_path = weights_path
        path_obj = Path(weights_path)
        if not path_obj.exists() or not path_obj.is_file():
            self.model = None
            self.status = "MISSING_WEIGHTS"
            self.error_detail = (
                f"Drone YOLO weights not found at '{weights_path}'. "
                "Generic COCO weights are intentionally disabled to prevent false airspace telemetry."
            )
            return False

        try:
            from ultralytics import YOLO
            loaded_model = YOLO(str(path_obj))
            loaded_model.to(self.device)
            self.model = loaded_model
            self.status = "READY"
            self.error_detail = None
            names = getattr(loaded_model, "names", {}) or {}
            self.class_names = {str(k): str(v).upper() for k, v in names.items()}
            return True
        except Exception as exc:
            self.model = None
            self.status = "LOAD_ERROR"
            self.error_detail = f"Failed to initialize YOLO model from '{weights_path}': {exc}"
            return False

    def get_diagnostics(self) -> dict:
        return {
            "status": self.status,
            "available": self.model is not None,
            "weights_path": self.weights_path,
            "device": self.device,
            "classes": self.class_names,
            "error": self.error_detail,
            "setup_instructions": [
                "1. Obtain or train a YOLOv8/YOLO11 drone detection model (e.g., Anti-UAV or VisDrone UAV weights).",
                f"2. Save the checkpoint file to backend/{self.weights_path} (or enter a valid path below).",
                "3. Click LOAD WEIGHTS, or enable DEMO Calibration Mode to test pipeline synchronization.",
            ],
        }
