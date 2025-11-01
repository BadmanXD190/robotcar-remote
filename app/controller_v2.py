import os, time, json
import streamlit as st
from streamlit_javascript import st_javascript
import paho.mqtt.client as mqtt

# ---- Config (secrets > env > defaults) ----
BROKER    = st.secrets.get("BROKER", os.environ.get("BROKER", "broker.hivemq.com"))
PORT      = int(st.secrets.get("PORT", os.environ.get("PORT", "1883")))
DEVICE_ID = st.secrets.get("DEVICE_ID", os.environ.get("DEVICE_ID", "robotcar_umk1"))
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"
KEEPALIVE = int(st.secrets.get("KEEPALIVE", os.environ.get("KEEPALIVE", "30")))
TRANSPORT = os.environ.get("TRANSPORT", st.secrets.get("TRANSPORT", "tcp")).lower()  # tcp or ws
WS_PATH   = os.environ.get("WS_PATH", st.secrets.get("WS_PATH", "/mqtt"))

st.set_page_config(page_title="Robot Car Keyboard", layout="centered")

# ---- MQTT client (one per session) ----
if "client" not in st.session_state:
    client = mqtt.Client(
        client_id=f"rc_keys_{int(time.time())}",
        transport=("websockets" if TRANSPORT == "ws" else "tcp"),
    )
    if TRANSPORT == "ws":
        client.ws_set_options(path=WS_PATH)

    def on_connect(c, u, f, rc, *args):
        st.session_state.connected = (rc == 0)

    client.on_connect = on_connect
    client.connect(BROKER, PORT, keepalive=KEEPALIVE)
    client.loop_start()
    st.session_state.client = client
    st.session_state.connected = False
    st.session_state.prev = {"ArrowUp": False, "ArrowDown": False,
                             "ArrowLeft": False, "ArrowRight": False, "Space": False}
    st.session_state.last_sent = ""  # last command we published

client = st.session_state.client

st.title("Robot Car – Keyboard Controller")
st.caption(f"Broker {BROKER}  |  Topic {TOPIC_CMD}")
st.success("MQTT Connected") if st.session_state.connected else st.warning("MQTT Connecting…")

st.write("Click once on this page to give it focus, then use ⬆️ ⬇️ ⬅️ ➡️. Spacebar = Stop.")

# Poll the browser ~10 times/sec for key state
st.autorefresh(interval=100, key="poll")

# JavaScript: maintain key state and return it each rerun
state = st_javascript("""
(() => {
  const allow = ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' '];
  if (!window.keyState) {
    window.keyState = {ArrowUp:false, ArrowDown:false, ArrowLeft:false, ArrowRight:false, Space:false};
    window.addEventListener('keydown', (e) => {
      if (allow.includes(e.key)) {
        e.preventDefault();
        if (e.key === ' ') window.keyState.Space = true;
        else window.keyState[e.key] = true;
      }
    }, {passive:false});
    window.addEventListener('keyup', (e) => {
      if (allow.includes(e.key)) {
        if (e.key === ' ') window.keyState.Space = false;
        else window.keyState[e.key] = false;
      }
    });
  }
  return window.keyState;
})()
""")

# Convert JS return (could be string) to dict
if isinstance(state, str):
    try:
        state = json.loads(state)
    except Exception:
        state = st.session_state.prev

# Decide command based on key state (priority order)
cmd = None
if state.get("Space"):             cmd = "S"
elif state.get("ArrowUp"):         cmd = "F"
elif state.get("ArrowDown"):       cmd = "B"
elif state.get("ArrowLeft"):       cmd = "L"
elif state.get("ArrowRight"):      cmd = "R"
else:
    # no key pressed now
    if any(st.session_state.prev.values()):
        cmd = "S"  # send stop once when keys released

# Publish when command changes
if cmd and cmd != st.session_state.last_sent:
    client.publish(TOPIC_CMD, cmd)
    st.session_state.last_sent = cmd

# Keep a tiny HUD
pressed = [k.replace("Arrow","") for k,v in state.items() if v]
st.write("Pressed:", ", ".join(pressed) if pressed else "(none)")

# Remember previous state
st.session_state.prev = state
