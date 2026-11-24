from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey
from database.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id = Column(String(32), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    annotated_filepath = Column(String(512), nullable=True)
    file_size_bytes = Column(Integer, default=0)
    duration_sec = Column(Float, default=0.0)
    fps = Column(Float, default=30.0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    total_frames = Column(Integer, default=0)
    frames_processed = Column(Integer, default=0)
    processing_fps = Column(Float, default=0.0)
    status = Column(String(32), default="UPLOADED")
    is_demo_mode = Column(Boolean, default=False)
    error_message = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=utcnow)


class DetectionRecord(Base):
    __tablename__ = "detection_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), ForeignKey("analysis_sessions.id"), index=True, nullable=False)
    frame_id = Column(Integer, index=True, nullable=False)
    timestamp = Column(Float, index=True, nullable=False)
    track_id = Column(String(32), index=True, nullable=False)
    drone_class = Column(String(64), default="drone")
    confidence = Column(Float, nullable=False)
    track_status = Column(String(32), default="ACTIVE")

    x1 = Column(Float, nullable=False)
    y1 = Column(Float, nullable=False)
    x2 = Column(Float, nullable=False)
    y2 = Column(Float, nullable=False)
    cx = Column(Float, nullable=False)
    cy = Column(Float, nullable=False)

    relative_depth = Column(Float, default=0.5)
    depth_confidence = Column(Float, default=0.5)
    is_metric = Column(Boolean, default=False)
    pos_x = Column(Float, default=0.0)
    pos_y = Column(Float, default=0.0)
    pos_z = Column(Float, default=0.0)

    vx = Column(Float, default=0.0)
    vy = Column(Float, default=0.0)
    vz = Column(Float, default=0.0)
    speed = Column(Float, default=0.0)
    heading_deg = Column(Float, default=0.0)


class TrackRecord(Base):
    __tablename__ = "track_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), ForeignKey("analysis_sessions.id"), index=True, nullable=False)
    track_id = Column(String(32), index=True, nullable=False)
    drone_class = Column(String(64), default="drone")
    first_seen_frame = Column(Integer, default=0)
    last_seen_frame = Column(Integer, default=0)
    first_seen_ts = Column(Float, default=0.0)
    last_seen_ts = Column(Float, default=0.0)
    avg_confidence = Column(Float, default=0.0)
    status = Column(String(32), default="ACTIVE")
    reid_count = Column(Integer, default=0)


class AirspaceEvent(Base):
    __tablename__ = "airspace_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), ForeignKey("analysis_sessions.id"), index=True, nullable=False)
    frame_id = Column(Integer, default=0)
    timestamp = Column(Float, default=0.0)
    track_id = Column(String(32), nullable=True)
    event_type = Column(String(64), nullable=False)
    risk_level = Column(String(32), default="LOW")
    zone_name = Column(String(128), nullable=True)
    reason = Column(String(512), nullable=False)
    position = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)


class ExternalTelemetry(Base):
    __tablename__ = "external_telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), index=True, nullable=True)
    device_id = Column(String(64), nullable=False)
    sensor_timestamp = Column(Float, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    baro_altitude_m = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    rssi_dbm = Column(Integer, nullable=True)
    received_at = Column(DateTime, default=utcnow)
