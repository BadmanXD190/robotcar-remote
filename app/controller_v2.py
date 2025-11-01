# app/keyboard_mqtt.py
import os, time, json, queue
import streamlit as st
from streamlit_javascript import st_javascript
from streamlit_autorefresh import st_autorefresh
import paho.mqtt.client as mqtt

BROKER    = st.secrets.get("BROKER", os.environ.get("BROKER", "broker.hivemq.com"))
PORT      = int(st.secrets.get("PORT", os.environ.get("PORT", "1883")))
DEVICE_ID = st.secrets.get("DEVICE_ID", os.environ.get("DEVICE_ID", "robotcar_umk1"))
KEEPALIVE = int(st.secrets.get("KEEPALIVE", os.environ.get("KEEPALIVE", "30")))
TRANSPORT = (st.secrets.get("TRANSPORT", os.environ.get("TRANSPORT", "tcp")) or "tcp").lower()
WS_PATH   = st.secrets.get("WS_PATH", os.environ.get("WS_PATH", "/mqtt" if TRANSPORT=="ws" else ""))

TOPIC_CMD  = f"rc/{DEVICE_ID}/cmd"
TOPIC_TELE = f"rc/{DEVICE_ID}/tele"

st.set_page_config(page_title="Robot Car – Keyboard", layout="centered")

# --- state ---
if "client" not in st.session_state:    st.session_state.client = None
if "connected" not in st.session_state: st.session_state.connected = False
if "q" not in st.session_state:         st.session_state.q = queue.Queue()
if "prev_keys" not in st.session_state: st.session_state.prev_keys = {"ArrowUp":False,"ArrowDown":False,"ArrowLeft":False,"ArrowRight":False,"Space":False}
if "last_cmd" not in st.session_state:  st.session_state.last_cmd = ""
if "logs" not in st.session_state:      st.session_state.logs = []

def _is_success(rc_or_reason):
    try:
        if hasattr(rc_or_reason, "is_success") and rc_or_reason.is_success: return True
        if hasattr(rc_or_reason, "value"): return int(rc_or_reason.value) == 0
        return int(rc_or_reason) == 0
    except Exception:
        return False

def ensure_client():
    if st.session_state.client: return st.session_state.client
    client = mqtt.Client(
        client_id=f"rc_keys_{int(time.time())}",
        transport=("websockets" if TRANSPORT=="ws" else "tcp"),
        protocol=mqtt.MQTTv311,
    )
    if TRANSPORT == "ws":
        client.ws_set_options(path=WS_PATH)

    def on_connect(c,u,flags,rc_or_reason,*_):
        ok = _is_success(rc_or_reason)
        st.session_state.connected = ok
        st.session_state.q.put(("sys", f"on_connect ok={ok} rc={getattr(rc_or_reason,'value',rc_or_reason)}"))
        if ok: c.subscribe(TOPIC_TELE)

    def on_message(c,u,msg):
        st.session_state.q.put(("tele", msg.payload.decode("utf-8","ignore")))

    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT, keepalive=KEEPALIVE)
        client.loop_start()
    except Exception as e:
        st.session_state.q.put(("err", f"MQTT connect error: {e}"))
    st.session_state.client = client
    return client

client = ensure_client()

# header (no banner)
st.markdown(f"**Broker** {BROKER}  |  **CMD** `{TOPIC_CMD}`  |  **TELE** `{TOPIC_TELE}`  |  "
            + ("✅ Connected" if st.session_state.connected else "⏳ Connecting"))

# rerun every 100 ms
st_autorefresh(interval=100, key="poll100ms")

# global key listeners + auto focus
state = st_javascript("""
(() => {
  try { window.focus(); document.body.tabIndex = -1; document.body.focus(); } catch(e) {}
  const allow = ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' '];
  if (!window.keyState) {
    window.keyState = {ArrowUp:false, ArrowDown:false, ArrowLeft:false, ArrowRight:false, Space:false};
    addEventListener('keydown', e => { if (allow.includes(e.key)) { e.preventDefault(); (e.key===' ' ? window.keyState.Space=true : window.keyState[e.key]=true); }}, {passive:false});
    addEventListener('keyup',   e => { if (allow.includes(e.key)) { (e.key===' ' ? window.keyState.Space=false : window.keyState[e.key]=false); }});
    addEventListener('blur',    () => { for (const k in window.keyState) window.keyState[k]=false; });
  }
  return window.keyState;
})()
""")

if isinstance(state, str):
    try: state = json.loads(state)
    except Exception: state = st.session_state.prev_keys

# decide command
cmd = None
if state.get("Space"):       cmd = "S"
elif state.get("ArrowUp"):   cmd = "F"
elif state.get("ArrowDown"): cmd = "B"
elif state.get("ArrowLeft"): cmd = "L"
elif state.get("ArrowRight"):cmd = "R"
else:
    if any(st.session_state.prev_keys.values()):
        cmd = "S"

# publish on change
if cmd and cmd != st.session_state.last_cmd and st.session_state.client:
    st.session_state.client.publish(TOPIC_CMD, cmd)
    st.session_state.last_cmd = cmd

# pressed HUD
pressed = [k.replace("Arrow","") for k,v in state.items() if v]
st.write("Pressed:", ", ".join(pressed) if pressed else "(none)")

st.session_state.prev_keys = state

# telemetry log (updates every 100 ms due to st_autorefresh)
st.subheader("Telemetry / Logs")
for _ in range(500):
    try:
        kind, msg = st.session_state.q.get_nowait()
        st.session_state.logs.append(f"{time.strftime('%H:%M:%S')} [{kind}] {msg}")
    except queue.Empty:
        break
st.session_state.logs = st.session_state.logs[-250:]
st.code("\n".join(st.session_state.logs) if st.session_state.logs else "No messages yet")
