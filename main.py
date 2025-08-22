import os
import json
import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from paho.mqtt import client as mqtt_client


MQTT_BROKER = os.getenv('MQTT_BROKER', 'broker.hivemq.com')
try:
    MQTT_PORT = int(os.getenv('MQTT_PORT', '1883'))
except Exception:
    print('Invalid MQTT_PORT env var; defaulting to 1883')
    MQTT_PORT = 1883
BACKEND_BASE = os.getenv('BACKEND_BASE', 'http://localhost:8000')
STATUS_TOPIC = 'hotel/devices/+/status'
WILL_TOPIC_TEMPLATE = 'hotel/devices/{device_id}/lwt'

app = FastAPI(title='SmartStay IoT Gateway')

mqtt = mqtt_client.Client()
event_loop = None


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(STATUS_TOPIC)
    else:
        print('MQTT connect failed:', rc)


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except Exception:
        payload = { 'raw': msg.payload.decode(errors='ignore') }
    # Derive device_id from topic if not present
    parts = msg.topic.split('/')
    if len(parts) >= 3 and parts[0] == 'hotel' and parts[1] == 'devices':
        payload.setdefault('device_id', parts[2])
    # Forward to backend
    if event_loop and event_loop.is_running():
        asyncio.run_coroutine_threadsafe(forward_status(payload), event_loop)
    else:
        try:
            asyncio.run(forward_status(payload))
        except RuntimeError:
            print('No event loop available to forward status, dropping message')


async def forward_status(payload):
    url = f"{BACKEND_BASE}/api/devices/webhook/status/"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(url, json=payload)
        except Exception as e:
            print('Failed to forward status:', e)


@app.on_event('startup')
async def startup():
    global event_loop
    event_loop = asyncio.get_running_loop()
    mqtt.on_connect = on_connect
    mqtt.on_message = on_message
    mqtt.connect_async(MQTT_BROKER, MQTT_PORT, 60)
    mqtt.loop_start()


@app.on_event('shutdown')
async def shutdown():
    mqtt.loop_stop()
    mqtt.disconnect()


@app.get('/health')
async def health():
    return { 'ok': True }


@app.post('/api/command')
async def command(body: dict):
    device_id = body.get('device_id')
    actuator = body.get('actuator')
    state = body.get('state')
    if not all([device_id, actuator, state]):
        raise HTTPException(status_code=400, detail='device_id, actuator, state are required')
    topic = f"hotel/devices/{device_id}/{actuator}/command"
    payload = json.dumps({ 'state': state })
    info = mqtt.publish(topic, payload)
    if info.rc != mqtt_client.MQTT_ERR_SUCCESS:
        raise HTTPException(status_code=500, detail='Failed to publish command')
    return { 'ok': True }



