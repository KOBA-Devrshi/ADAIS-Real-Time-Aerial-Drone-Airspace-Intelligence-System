from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional


@dataclass
class AirspaceZone:
    zone_id: str
    name: str
    zone_type: str  # SAFE, WARNING, RESTRICTED
    min_bounds: Tuple[float, float, float]
    max_bounds: Tuple[float, float, float]
    warning_margin: float = 8.0

    def contains(self, pos: Tuple[float, float, float]) -> bool:
        x, y, z = pos
        return (
            self.min_bounds[0] <= x <= self.max_bounds[0]
            and self.min_bounds[1] <= y <= self.max_bounds[1]
            and self.min_bounds[2] <= z <= self.max_bounds[2]
        )

    def distance_to_box(self, pos: Tuple[float, float, float]) -> float:
        x, y, z = pos
        dx = max(self.min_bounds[0] - x, 0.0, x - self.max_bounds[0])
        dy = max(self.min_bounds[1] - y, 0.0, y - self.max_bounds[1])
        dz = max(self.min_bounds[2] - z, 0.0, z - self.max_bounds[2])
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    def to_dict(self) -> dict:
        return asdict(self)


def default_airspace_zones() -> List[AirspaceZone]:
    return [
        AirspaceZone(
            zone_id="ZONE-SAFE-01",
            name="Authorized Flight Corridor",
            zone_type="SAFE",
            min_bounds=(-60.0, 0.0, 5.0),
            max_bounds=(60.0, 75.0, 110.0),
            warning_margin=5.0,
        ),
        AirspaceZone(
            zone_id="ZONE-WARN-01",
            name="Perimeter Buffer Sector",
            zone_type="WARNING",
            min_bounds=(-35.0, 10.0, 35.0),
            max_bounds=(35.0, 55.0, 75.0),
            warning_margin=6.0,
        ),
        AirspaceZone(
            zone_id="ZONE-REST-01",
            name="Restricted No-Fly Core",
            zone_type="RESTRICTED",
            min_bounds=(-15.0, 15.0, 45.0),
            max_bounds=(15.0, 45.0, 65.0),
            warning_margin=8.0,
        ),
    ]


class GeofenceMonitor:
    def __init__(self, zones: Optional[List[AirspaceZone]] = None):
        self.zones = zones if zones is not None else default_airspace_zones()

    def evaluate(self, pos: Tuple[float, float, float]) -> List[dict]:
        findings = []
        for zone in self.zones:
            inside = zone.contains(pos)
            dist = zone.distance_to_box(pos)

            if zone.zone_type == "RESTRICTED":
                if inside:
                    findings.append({
                        "status": "BREACH_RESTRICTED",
                        "zone": zone,
                        "distance": 0.0,
                    })
                elif dist <= zone.warning_margin:
                    findings.append({
                        "status": "APPROACHING_RESTRICTED",
                        "zone": zone,
                        "distance": round(dist, 2),
                    })
            elif zone.zone_type == "WARNING" and inside:
                findings.append({
                    "status": "INSIDE_WARNING",
                    "zone": zone,
                    "distance": 0.0,
                })
            elif zone.zone_type == "SAFE" and not inside:
                findings.append({
                    "status": "EXITED_SAFE_CORRIDOR",
                    "zone": zone,
                    "distance": round(dist, 2),
                })
        return findings
