import os, time, json
import streamlit as st
from streamlit_javascript import st_javascript
import paho.mqtt.client as mqtt

# ---------- Config (secrets > env > defaults) ----------
BROKER    = st.secrets.get("BROKER", os.environ.get("BROKER", "broker.hivemq.com"))
PORT      = int(st.secrets.get("PORT", os.environ.get("PORT", "1883")))
DEVICE_ID = st.secrets.get("DEVICE_ID", os.environ.get("DEVICE_ID", "robotcar_umk1"))
KEEPALIVE = int(st.secrets.get("KEEPALIVE", os.environ.get("KEEPALIVE", "30")))
TRANSPORT = (st.secrets.get("TRANSPORT", os.environ.get("TRANSPORT", "tcp")) or "tcp").lower()
WS_PATH   = st.secrets.get("WS_PATH", os.environ.get("WS_PATH", "/mqtt" if TRANSPORT=="ws" else ""))

TOPIC_CMD  = f"rc/{DEVICE_ID}/cmd"
TOPIC_TELE = f"rc/{DEVICE_ID}/tele"   # not used here, but kept for consistency

st.set_page_config(page_title="Traditional Controls", layout="centered")

# ---------- State ----------
if "client" not in st.session_state:
    st.session_state.client = None
if "connected" not in st.session_state:
    st.session_state.connected = False
if "speed" not in st.session_state:
    st.session_state.speed = 60
if "last_cmd" not in st.session_state:
    st.session_state.last_cmd = ""
if "ui_active" not in st.session_state:
    st.session_state.ui_active = {"Up": False, "Down": False, "Left": False, "Right": False, "Space": False}

# ---------- MQTT ----------
def _is_success(rc_or_reason):
    try:
        if hasattr(rc_or_reason, "is_success") and rc_or_reason.is_success:
            return True
        if hasattr(rc_or_reason, "value"):
            return int(rc_or_reason.value) == 0
        return int(rc_or_reason) == 0
    except Exception:
        return False

def ensure_client():
    if st.session_state.client is not None:
        return st.session_state.client
    client = mqtt.Client(
        client_id=f"rc_trad_{int(time.time())}",
        transport=("websockets" if TRANSPORT == "ws" else "tcp"),
        protocol=mqtt.MQTTv311,
    )
    if TRANSPORT == "ws":
        client.ws_set_options(path=WS_PATH)

    def on_connect(c, u, flags, rc_or_reason, *args):
        st.session_state.connected = _is_success(rc_or_reason)

    client.on_connect = on_connect

    try:
        client.connect(BROKER, PORT, keepalive=KEEPALIVE)
        client.loop_start()
    except Exception:
        pass

    st.session_state.client = client
    return client

client = ensure_client()

# ---------- Title + Instructions ----------
st.markdown("# Traditional Controls")
st.write(
    "Use keyboard **arrow keys** to drive, and **Space** to stop. "
    "You can also **click** the on-screen keys below. "
    "If keys do not respond, click once anywhere on the page to give it focus."
)

# ---------- Speed Control ----------
new_speed = st.slider("Speed", 0, 100, st.session_state.speed, 5)
if new_speed != st.session_state.speed:
    st.session_state.speed = new_speed
    if st.session_state.client:
        st.session_state.client.publish(TOPIC_CMD, f"speed:{new_speed}")

# We’ll rerun the script every 100ms to poll keyboard and animate active keys
st.autorefresh(interval=100, key="poll100ms")

# ---------- Keypad UI (HTML + CSS) ----------
# We render custom HTML keys so we can color them when active.
st.markdown(
    """
    <style>
    .pad { display: grid; grid-template-columns: 80px 80px 80px; gap: 10px; justify-content: center; margin-top: 14px; }
    .key {
        user-select: none;
        text-align: center;
        padding: 16px 0;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.2);
        background: rgba(255,255,255,0.06);
        font-weight: 600;
        letter-spacing: .4px;
        cursor: pointer;
        transition: transform .02s ease, background .08s ease, box-shadow .08s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,.25);
    }
    .key.active {
        background: rgba(0, 180, 255, 0.35);
        box-shadow: 0 0 0 2px rgba(0, 180, 255, 0.6) inset, 0 2px 12px rgba(0, 180, 255, .45);
    }
    .key:active { transform: scale(.98); }

    /* layout cells */
    .cell1 { grid-column: 2; grid-row: 1; }           /* Up */
    .cell2 { grid-column: 1; grid-row: 2; }           /* Left */
    .cell3 { grid-column: 2; grid-row: 2; }           /* Down */
    .cell4 { grid-column: 3; grid-row: 2; }           /* Right */
    .space { grid-column: 1 / span 3; grid-row: 3; padding: 14px 0; }
    </style>

    <div class="pad">
      <div class="key cell1" id="KeyUp">▲</div>
      <div class="key cell2" id="KeyLeft">◄</div>
      <div class="key cell3" id="KeyDown">▼</div>
      <div class="key cell4" id="KeyRight">►</div>
      <div class="key space" id="KeySpace">Space</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- JavaScript: keyboard + click, return which keys are pressed ----------
js_state = st_javascript("""
(() => {
  try { window.focus(); document.body.tabIndex = -1; document.body.focus(); } catch(e) {}

  const allow = ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' '];
  if (!window.keyState) {
    window.keyState = {ArrowUp:false, ArrowDown:false, ArrowLeft:false, ArrowRight:false, Space:false};

    // Keyboard handlers
    window.addEventListener('keydown', (e) => {
      if (allow.includes(e.key)) { e.preventDefault(); if (e.key===' ') window.keyState.Space = true; else window.keyState[e.key] = true; }
    }, {passive:false});
    window.addEventListener('keyup', (e) => {
      if (allow.includes(e.key)) { if (e.key===' ') window.keyState.Space = false; else window.keyState[e.key] = false; }
    });

    // Click handlers for the on-screen keys (flash active briefly)
    const id2key = {KeyUp:'ArrowUp', KeyDown:'ArrowDown', KeyLeft:'ArrowLeft', KeyRight:'ArrowRight', KeySpace:' '};
    for (const id in id2key) {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('mousedown', (ev) => {
          const k = id2key[id];
          if (k===' ') window.keyState.Space = true; else window.keyState[k] = true;
          el.classList.add('active');
        });
        el.addEventListener('mouseup', (ev) => {
          const k = id2key[id];
          if (k===' ') window.keyState.Space = false; else window.keyState[k] = false;
          el.classList.remove('active');
        });
        el.addEventListener('mouseleave', (ev) => {
          const k = id2key[id];
          if (k===' ') window.keyState.Space = false; else window.keyState[k] = false;
          el.classList.remove('active');
        });
      }
    }
  }

  // Update visual active class from keyboard state too
  const mapEl = {ArrowUp:'KeyUp', ArrowDown:'KeyDown', ArrowLeft:'KeyLeft', ArrowRight:'KeyRight', Space:'KeySpace'};
  for (const k in mapEl) {
    const pressed = (k==='Space') ? window.keyState.Space : window.keyState[k];
    const el = document.getElementById(mapEl[k]);
    if (el) { if (pressed) el.classList.add('active'); else el.classList.remove('active'); }
  }
  return window.keyState;
})()
""")

# Normalize possible string return
if isinstance(js_state, str):
    try:
        js_state = json.loads(js_state)
    except Exception:
        js_state = {}

# ---------- Decide command from keys (priority) ----------
cmd = None
if js_state.get("Space"):
    cmd = "S"
elif js_state.get("ArrowUp"):
    cmd = "F"
elif js_state.get("ArrowDown"):
    cmd = "B"
elif js_state.get("ArrowLeft"):
    cmd = "L"
elif js_state.get("ArrowRight"):
    cmd = "R"
else:
    # If previously any key was active, send one Stop when all released
    if st.session_state.last_cmd in ("F","B","L","R"):
        cmd = "S"

# ---------- Publish only on change ----------
if cmd and cmd != st.session_state.last_cmd and st.session_state.client:
    st.session_state.client.publish(TOPIC_CMD, cmd)
    st.session_state.last_cmd = cmd
