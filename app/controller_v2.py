import os, time, queue
import streamlit as st
import paho.mqtt.client as mqtt

# ---- Config (secrets first, then env, then hardcoded defaults) ----
BROKER   = st.secrets.get("BROKER",   os.environ.get("BROKER",   "broker.hivemq.com"))
PORT     = int(st.secrets.get("PORT", os.environ.get("PORT", "1883")))
DEVICE_ID= st.secrets.get("DEVICE_ID", os.environ.get("DEVICE_ID", "robotcar_umk1"))
TOPIC_CMD  = f"rc/{DEVICE_ID}/cmd"
TOPIC_TELE = f"rc/{DEVICE_ID}/tele"
TRANSPORT  = st.secrets.get("TRANSPORT", os.environ.get("TRANSPORT", "tcp")).lower()
KEEPALIVE  = int(st.secrets.get("KEEPALIVE", os.environ.get("KEEPALIVE", "30")))

st.set_page_config(page_title="Robot Car Controller", layout="centered")

# ---- App state ----
if "connected" not in st.session_state: st.session_state.connected = False
if "speed" not in st.session_state:     st.session_state.speed = 60
if "q" not in st.session_state:         st.session_state.q = queue.Queue()
if "client" not in st.session_state:
    st.session_state.client = None

def make_client():
    # paho-mqtt v2 uses a new Client API; we pass transport accordingly
    client = mqtt.Client(client_id=f"rc_panel_{int(time.time())}", transport=("websockets" if TRANSPORT=="ws" else "tcp"))

    def on_connect(c, u, f, rc, *args):
        st.session_state.connected = (rc == 0)
        if rc == 0:
            c.subscribe(TOPIC_TELE)
        st.session_state.q.put(("sys", f"on_connect rc={rc}"))

    def on_message(c, u, msg):
        st.session_state.q.put(("tele", msg.payload.decode("utf-8", errors="ignore")))

    client.on_connect = on_connect
    client.on_message = on_message

    # WebSocket path/port tips:
    # - HiveMQ public WS often uses port 8000 with path "/mqtt"
    #   Set secrets: TRANSPORT="ws", PORT=8000, WS_PATH="/mqtt"
    ws_path = st.secrets.get("WS_PATH", os.environ.get("WS_PATH", "/mqtt" if TRANSPORT=="ws" else ""))

    try:
        if TRANSPORT == "ws":
            client.ws_set_options(path=ws_path)
        client.connect(BROKER, PORT, keepalive=KEEPALIVE)
        client.loop_start()
    except Exception as e:
        st.session_state.q.put(("err", f"MQTT connect error: {e}"))
    return client

if st.session_state.client is None:
    st.session_state.client = make_client()

st.title("Robot Car Controller")
st.caption(f"Broker {BROKER} | Transport {TRANSPORT.upper()} | CMD {TOPIC_CMD} | TELE {TOPIC_TELE}")
st.success("MQTT Connected") if st.session_state.connected else st.warning("MQTT Connecting...")

# ---- Controls ----
col1, col2, col3 = st.columns(3)
with col2:
    if st.button("Forward"): st.session_state.client.publish(TOPIC_CMD, "F")
with col1:
    if st.button("Left"):    st.session_state.client.publish(TOPIC_CMD, "L")
with col3:
    if st.button("Right"):   st.session_state.client.publish(TOPIC_CMD, "R")
if st.button("Back"):        st.session_state.client.publish(TOPIC_CMD, "B")
if st.button("Stop"):        st.session_state.client.publish(TOPIC_CMD, "S")

st.session_state.speed = st.slider("Speed percent", 0, 100, st.session_state.speed, 5)
if st.button("Set speed"):
    st.session_state.client.publish(TOPIC_CMD, f"speed:{st.session_state.speed}")

# ---- Logs ----
st.subheader("Telemetry / Logs")
log_box = st.empty()
logs = getattr(st.session_state, "logs", [])
for _ in range(200):
    try:
        kind, msg = st.session_state.q.get_nowait()
        logs.append(f"{time.strftime('%H:%M:%S')} [{kind}] {msg}")
    except queue.Empty:
        break
st.session_state.logs = logs[-250:]
log_box.code("\n".join(st.session_state.logs) if logs else "No messages yet")

st.caption("Push to GitHub to auto-redeploy. If it hangs, use the top-right ‘Rerun’.")
