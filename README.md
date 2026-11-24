# ADAIS — Autonomous Drone Airspace Intelligence System

Complete, operational AI-powered drone surveillance, ByteTrack multi-object tracking, monocular 3D depth perception, and virtual airspace risk analysis platform.

## 1. Prerequisites
- **Python 3.11+**
- **Node.js 20+** and **npm**
- Optional: NVIDIA GPU with CUDA for accelerated YOLO + MiDaS inference (CPU fallback is automatic).

## 2. Drone YOLO Model Setup (`backend/weights/drone_best.pt`)
ADAIS uses a drone-specific YOLO checkpoint (`yolov8n.pt` / `yolo11n.pt` fine-tuned on UAV datasets such as Anti-UAV, VisDrone, or Drone-vs-Bird).
1. Place your trained weights at `backend/weights/drone_best.pt`.
2. If weights are not yet present, ADAIS will honestly display `DRONE WEIGHTS MISSING` in the UI and allow you to either:
   - Load weights dynamically via the **Setup Guide** panel (`POST /api/detector/configure`), or
   - Enable **`DEMO Calibration Mode`** to verify video-to-3D synchronization before installing weights.

## 3. Running in VS Code
1. Extract this archive and open the `ADAIS` folder in **Visual Studio Code**.
2. Open two integrated terminals (or run **Terminal -> Run Task -> Start ADAIS Full Stack**):

### Terminal 1 — Backend (FastAPI + Computer Vision Pipeline)
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 — Frontend (React + TypeScript + Three.js)
```bash
cd frontend
npm install
npm run dev
```

3. Open **`http://localhost:5173`** in your browser.

## 4. Running Automated Verification Tests
```bash
cd backend
pytest -v tests/test_adais_pipeline.py
```

## 5. ESP32 Wi-Fi Sensor Telemetry (Optional Hardware Interface)
External ESP32 nodes can post GPS, barometric altitude, and environmental readings to `POST /api/telemetry/esp32`. External sensor data is stored separately from computer-vision depth estimates.
