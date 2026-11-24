import cv2
import numpy as np
from typing import List


def draw_hud_annotations(frame: np.ndarray, tracks_payload: List[dict], is_demo: bool = False) -> np.ndarray:
    annotated = frame.copy()

    if is_demo:
        cv2.putText(
            annotated,
            "DEMO CALIBRATION MODE - SYNTHETIC CALIBRATION TARGETS (NO WEIGHTS LOADED)",
            (20, 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 215, 255),
            2,
            cv2.LINE_AA,
        )

    for item in tracks_payload:
        bbox = item["bbox"]
        x1, y1, x2, y2 = int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])
        cx, cy = int(item["center"]["x"]), int(item["center"]["y"])
        risk = item.get("risk_level", "LOW")

        color = (255, 220, 0)
        if risk == "MEDIUM":
            color = (0, 215, 255)
        elif risk in ("HIGH", "CRITICAL"):
            color = (60, 60, 255)

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        cv2.drawMarker(annotated, (cx, cy), color, cv2.MARKER_CROSS, 12, 1)

        label = f"{item['track_id']} | {item['class']} {item['confidence']*100:.1f}%"
        cv2.putText(
            annotated,
            label,
            (x1, max(18, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            color,
            2,
            cv2.LINE_AA,
        )
    return annotated
