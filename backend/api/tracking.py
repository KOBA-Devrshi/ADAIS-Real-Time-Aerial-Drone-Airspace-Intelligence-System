from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import (
    AnalysisSession, DetectionRecord, TrackRecord, AirspaceEvent, ExternalTelemetry
)
from airspace.geofence import default_airspace_zones

router = APIRouter(prefix="/api", tags=["tracking"])


class ESP32TelemetryIn(BaseModel):
    session_id: Optional[str] = None
    device_id: str
    sensor_timestamp: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    baro_altitude_m: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    rssi_dbm: Optional[int] = None


@router.get("/detections/{session_id}")
def get_detections(session_id: str, frame_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(DetectionRecord).filter(DetectionRecord.session_id == session_id)
    if frame_id is not None:
        q = q.filter(DetectionRecord.frame_id == frame_id)
    rows = q.order_by(DetectionRecord.frame_id.asc()).all()
    return [
        {
            "frame_id": r.frame_id,
            "timestamp": r.timestamp,
            "track_id": r.track_id,
            "class": r.drone_class,
            "confidence": r.confidence,
            "track_status": r.track_status,
            "bbox": {"x1": r.x1, "y1": r.y1, "x2": r.x2, "y2": r.y2},
            "center": {"x": r.cx, "y": r.cy},
            "spatial": {
                "x": r.pos_x,
                "y": r.pos_y,
                "z": r.pos_z,
                "relative_depth": r.relative_depth,
                "depth_confidence": r.depth_confidence,
                "is_metric": r.is_metric,
            },
            "motion": {
                "vx": r.vx,
                "vy": r.vy,
                "vz": r.vz,
                "speed": r.speed,
                "heading_deg": r.heading_deg,
            },
        }
        for r in rows
    ]


@router.get("/tracks/{session_id}")
def get_tracks(session_id: str, db: Session = Depends(get_db)):
    rows = db.query(TrackRecord).filter(TrackRecord.session_id == session_id).all()
    return [
        {
            "track_id": r.track_id,
            "class": r.drone_class,
            "first_seen_frame": r.first_seen_frame,
            "last_seen_frame": r.last_seen_frame,
            "first_seen_ts": r.first_seen_ts,
            "last_seen_ts": r.last_seen_ts,
            "avg_confidence": r.avg_confidence,
            "status": r.status,
            "reid_count": r.reid_count,
        }
        for r in rows
    ]


@router.get("/trajectory/{session_id}")
def get_trajectory(session_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(DetectionRecord)
        .filter(DetectionRecord.session_id == session_id)
        .order_by(DetectionRecord.frame_id.asc())
        .all()
    )
    grouped = {}
    for r in rows:
        grouped.setdefault(r.track_id, []).append({
            "frame_id": r.frame_id,
            "timestamp": r.timestamp,
            "image_x": r.cx,
            "image_y": r.cy,
            "pos_x": r.pos_x,
            "pos_y": r.pos_y,
            "pos_z": r.pos_z,
            "relative_depth": r.relative_depth,
            "is_metric": r.is_metric,
            "speed": r.speed,
            "heading_deg": r.heading_deg,
            "confidence": r.confidence,
        })
    return grouped


@router.get("/airspace/{session_id}")
def get_airspace(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    events = (
        db.query(AirspaceEvent)
        .filter(AirspaceEvent.session_id == session_id)
        .order_by(AirspaceEvent.id.desc())
        .limit(200)
        .all()
    )
    zones = [z.to_dict() for z in default_airspace_zones()]
    highest = "LOW"
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    for e in events:
        if order.get(e.risk_level, 0) > order[highest]:
            highest = e.risk_level

    return {
        "session_id": session_id,
        "airspace_risk_level": highest,
        "zones": zones,
        "events": [
            {
                "id": e.id,
                "frame_id": e.frame_id,
                "timestamp": e.timestamp,
                "track_id": e.track_id,
                "event_type": e.event_type,
                "risk_level": e.risk_level,
                "zone_name": e.zone_name,
                "reason": e.reason,
                "position": e.position,
                "confidence": e.confidence,
            }
            for e in events
        ],
    }


@router.post("/telemetry/esp32")
def ingest_esp32_telemetry(payload: ESP32TelemetryIn, db: Session = Depends(get_db)):
    row = ExternalTelemetry(
        session_id=payload.session_id,
        device_id=payload.device_id,
        sensor_timestamp=payload.sensor_timestamp,
        latitude=payload.latitude,
        longitude=payload.longitude,
        baro_altitude_m=payload.baro_altitude_m,
        temperature_c=payload.temperature_c,
        humidity_pct=payload.humidity_pct,
        rssi_dbm=payload.rssi_dbm,
    )
    db.add(row)
    db.commit()
    return {"status": "RECORDED", "source": "ESP32_EXTERNAL_SENSOR", "id": row.id}
