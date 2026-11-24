from dataclasses import dataclass, asdict
from typing import List, Tuple
from airspace.geofence import GeofenceMonitor


RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


@dataclass
class RiskAssessment:
    risk_level: str
    track_id: str
    timestamp: float
    zone_name: str
    reason: str
    position: dict
    confidence: float
    is_metric: bool

    def to_dict(self) -> dict:
        return asdict(self)


class AirspaceRiskEngine:
    def __init__(self, geofence_monitor: GeofenceMonitor, high_speed_threshold: float = 25.0):
        self.geofence = geofence_monitor
        self.high_speed_threshold = high_speed_threshold

    def assess_drone(
        self,
        track_id: str,
        timestamp: float,
        pos: Tuple[float, float, float],
        speed: float,
        predicted_path: List[dict],
        confidence: float,
        is_metric: bool,
    ) -> RiskAssessment:
        findings = self.geofence.evaluate(pos)
        pos_dict = {"x": pos[0], "y": pos[1], "z": pos[2], "is_metric": is_metric}

        level = "LOW"
        zone_name = "Authorized Airspace"
        reason = "No airspace boundary violation detected."

        for f in findings:
            status = f["status"]
            z = f["zone"]
            if status == "BREACH_RESTRICTED":
                if speed >= self.high_speed_threshold or confidence >= 0.80:
                    level = "CRITICAL"
                    zone_name = z.name
                    reason = (
                        f"CRITICAL intrusion: {track_id} inside {z.name} "
                        f"(speed={speed:.1f}, conf={confidence*100:.1f}%)."
                    )
                elif RISK_ORDER["HIGH"] > RISK_ORDER[level]:
                    level = "HIGH"
                    zone_name = z.name
                    reason = f"{track_id} entered restricted volume '{z.name}'."
            elif status == "APPROACHING_RESTRICTED" and RISK_ORDER["MEDIUM"] > RISK_ORDER[level]:
                level = "MEDIUM"
                zone_name = z.name
                reason = f"{track_id} within {f['distance']} units of restricted zone '{z.name}'."
            elif status == "INSIDE_WARNING" and RISK_ORDER["MEDIUM"] > RISK_ORDER[level]:
                level = "MEDIUM"
                zone_name = z.name
                reason = f"{track_id} operating inside warning sector '{z.name}'."
            elif status == "EXITED_SAFE_CORRIDOR" and RISK_ORDER["MEDIUM"] > RISK_ORDER[level]:
                level = "MEDIUM"
                zone_name = z.name
                reason = f"{track_id} exited safe flight corridor '{z.name}'."

        if level in ("LOW", "MEDIUM") and predicted_path:
            for pt in predicted_path:
                pred_findings = self.geofence.evaluate((pt["x"], pt["y"], pt["z"]))
                if any(pf["status"] == "BREACH_RESTRICTED" for pf in pred_findings):
                    if RISK_ORDER["HIGH"] > RISK_ORDER[level]:
                        level = "HIGH"
                        zone_name = pred_findings[0]["zone"].name
                        reason = (
                            f"Projected trajectory of {track_id} intersects restricted zone "
                            f"'{zone_name}' in ~{pt['dt']}s (±{pt['uncertainty_radius']} uncertainty)."
                        )
                    break

        return RiskAssessment(
            risk_level=level,
            track_id=track_id,
            timestamp=timestamp,
            zone_name=zone_name,
            reason=reason,
            position=pos_dict,
            confidence=round(confidence, 3),
            is_metric=is_metric,
        )
