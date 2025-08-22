IoT Gateway (FastAPI + MQTT)

Overview
- Subscribes to MQTT topic `hotel/devices/+/status`.
- Forwards payloads to backend `/api/devices/webhook/status/`.
- Accepts HTTP command requests and publishes to device command topics.

Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn paho-mqtt httpx python-dotenv
export MQTT_BROKER=broker.hivemq.com
export MQTT_PORT=1883
export BACKEND_BASE=http://localhost:8000
uvicorn main:app --reload --port 9000
```

HTTP API
- POST /api/command
  - Body: `{ "device_id": "AABBCCDDEEFF", "actuator": "ac|light|tv|refrigerator", "state": "ON|OFF" }`
- GET /health → `{ ok: true }`

Deploy to Render
- Prereqs: GitHub repo with this project at the root, `requirements.txt`, and `render.yaml`.
- Steps:
  1. Push this repo to GitHub.
  2. In Render, click New → Blueprint and select the repo.
  3. Render reads `render.yaml` and creates a Web Service named `iot-gateway`.
  4. Set environment variables:
     - `MQTT_BROKER` (e.g. `broker.hivemq.com`)
     - `MQTT_PORT` (e.g. `1883`)
     - `BACKEND_BASE` (e.g. `https://your-backend.example.com`)
  5. Deploy. Health check path is `/health`.

Notes
- The service listens on `$PORT` provided by Render and binds to `0.0.0.0` via Uvicorn.
- Update CORS or networking on your backend to accept calls from the Render domain if needed.


