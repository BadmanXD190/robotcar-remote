import os, json
import streamlit as st
import streamlit.components.v1 as components

# --- Config (defaults to test.mosquitto.org WSS). You can override via Streamlit Secrets. ---
WSS_HOST = st.secrets.get("WSS_HOST", os.environ.get("WSS_HOST", "test.mosquitto.org"))
WSS_PORT = st.secrets.get("WSS_PORT", os.environ.get("WSS_PORT", "8081"))
WSS_PATH = st.secrets.get("WSS_PATH", os.environ.get("WSS_PATH", "/mqtt"))  # keep "/mqtt"
DEVICE_ID = st.secrets.get("DEVICE_ID", os.environ.get("DEVICE_ID", "robotcar_umk1"))
KEEPALIVE = int(st.secrets.get("KEEPALIVE", os.environ.get("KEEPALIVE", "30")))
MQTT_USER = st.secrets.get("MQTT_USERNAME", os.environ.get("MQTT_USERNAME", ""))  # usually not needed
MQTT_PASS = st.secrets.get("MQTT_PASSWORD", os.environ.get("MQTT_PASSWORD", ""))

TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"

cfg = {
    "host": WSS_HOST,
    "port": WSS_PORT,
    "path": WSS_PATH if WSS_PATH.startswith("/") else f"/{WSS_PATH}",
    "topicCmd": TOPIC_CMD,
    "keepalive": KEEPALIVE,
    "username": MQTT_USER,
    "password": MQTT_PASS,
    "title": "Traditional Controls",
    "instructions": "Use arrow keys to drive and Space to stop. You can also click the on-screen keys below. If keys don’t respond, click once on the page to give it focus."
}

components.html(f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'self' https: 'unsafe-inline' 'unsafe-eval' data: blob:; connect-src *;">
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Traditional Controls</title>
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
<style>
  :root {{ --bg:#0f172a; --fg:#e5e7eb; --muted:#94a3b8; --accent:rgba(0,180,255,.35); --accentRing:rgba(0,180,255,.6); }}
  html,body {{ margin:0; background:var(--bg); color:var(--fg); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }}
  .wrap {{ max-width:760px; margin:28px auto 80px; padding:0 16px; }}
  h1 {{ font-size:1.6rem; margin:0 0 6px; }}
  .muted {{ color:var(--muted); font-size:.95rem; }}
  .status {{ font-size:.9rem; margin:6px 0 2px; color:var(--muted); }}
  .ok::before {{ content:"● "; color:#22c55e; }}
  .no::before {{ content:"● "; color:#ef4444; }}
  .url {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:.85rem; color:#a3e635; }}
  .err {{ color:#fda4af; font-size:.85rem; white-space:pre-wrap; }}
  .panel {{ margin-top:18px; padding:14px; border:1px solid rgba(255,255,255,.1); border-radius:14px; background:rgba(255,255,255,.04); }}
  .sliderRow {{ display:flex; align-items:center; gap:12px; }}
  .sliderRow input[type=range] {{ width:100%; }}
  .val {{ min-width:48px; text-align:right; font-variant-numeric:tabular-nums; }}
  .pad {{ display:grid; grid-template-columns:96px 96px 96px; gap:12px; justify-content:center; margin-top:16px; }}
  .key {{
    user-select:none; text-align:center; padding:18px 0; border-radius:14px;
    border:1px solid rgba(255,255,255,.14); background:rgba(255,255,255,.06);
    font-weight:700; letter-spacing:.4px; cursor:pointer; transition:transform .02s ease, background .08s ease, box-shadow .08s ease;
    box-shadow:0 2px 8px rgba(0,0,0,.25);
  }}
  .key.active {{ background: var(--accent); box-shadow:0 0 0 2px var(--accentRing) inset, 0 2px 12px rgba(0, 180, 255, .45); }}
  .key:active {{ transform: scale(.98); }}
  .cell1 {{ grid-column:2; grid-row:1; }}
  .cell2 {{ grid-column:1; grid-row:2; }}
  .cell3 {{ grid-column:2; grid-row:2; }}
  .cell4 {{ grid-column:3; grid-row:2; }}
  .space {{ grid-column:1 / span 3; grid-row:3; padding:16px 0; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{cfg["title"]}</h1>
  <div class="muted">{cfg["instructions"]}</div>
  <div id="status" class="status no">Connecting…</div>
  <div class="url">WSS: wss://{cfg["host"]}:{cfg["port"]}{cfg["path"]} &nbsp;&nbsp; Topic: <code>{cfg["topicCmd"]}</code></div>
  <div id="errmsg" class="err"></div>

  <div class="panel">
    <div class="sliderRow">
      <div style="min-width:60px">Speed</div>
      <input id="speed" type="range" min="0" max="100" step="5" value="60"/>
      <div class="val"><span id="speedVal">60</span>%</div>
    </div>

    <div class="pad" style="margin-top:18px">
      <div class="key cell1" id="KeyUp"    data-cmd="F">▲</div>
      <div class="key cell2" id="KeyLeft"  data-cmd="L">◄</div>
      <div class="key cell3" id="KeyDown"  data-cmd="B">▼</div>
      <div class="key cell4" id="KeyRight" data-cmd="R">►</div>
      <div class="key space" id="KeySpace" data-cmd="S">Space (Stop)</div>
    </div>
  </div>
</div>

<script>
(() => {{
  const CFG = {json.dumps(cfg)};
  const statusEl = document.getElementById('status');
  const errEl = document.getElementById('errmsg');
  const speed = document.getElementById('speed');
  const speedVal = document.getElementById('speedVal');

  // --- MQTT over WSS to test.mosquitto.org ---
  let client;
  try {{
    const url = "wss://" + CFG.host + ":" + CFG.port + CFG.path;
    const options = {{
      keepalive: Number(CFG.keepalive || 30),
      reconnectPeriod: 1000,
      clean: true,
      clientId: "rc_web_" + Math.random().toString(16).slice(2),
      protocolVersion: 4  // MQTT 3.1.1
    }};
    if (CFG.username) options.username = CFG.username;
    if (CFG.password) options.password = CFG.password;

    client = mqtt.connect(url, options);

    client.on('connect', () => {{
      statusEl.textContent = 'Connected';
      statusEl.className = 'status ok';
      errEl.textContent = '';
      client.publish(CFG.topicCmd, 'speed:' + speed.value);
    }});

    client.on('reconnect', () => {{
      statusEl.textContent = 'Reconnecting…';
      statusEl.className = 'status no';
    }});

    client.on('close', () => {{
      statusEl.textContent = 'Disconnected';
      statusEl.className = 'status no';
    }});

    client.on('error', (err) => {{
      statusEl.textContent = 'MQTT error';
      statusEl.className = 'status no';
      errEl.textContent = (err && (err.message || err.toString())) || 'Unknown error';
      console.error('MQTT error', err);
    }});
  }} catch (e) {{
    statusEl.textContent = 'MQTT init error';
    statusEl.className = 'status no';
    errEl.textContent = e.message || e.toString();
    console.error(e);
  }}

  const publish = (msg) => {{
    try {{ if (client && client.connected) client.publish(CFG.topicCmd, msg); }}
    catch (e) {{ errEl.textContent = 'Publish error: ' + (e.message || e); }}
  }};

  // Speed
  speed.addEventListener('input', () => {{
    speedVal.textContent = speed.value;
    publish('speed:' + speed.value);
  }});

  // On-screen keys
  const ids = ['KeyUp','KeyDown','KeyLeft','KeyRight','KeySpace'];
  ids.forEach(id => {{
    const el = document.getElementById(id);
    const cmd = el.dataset.cmd;
    const setActive = (on) => el.classList.toggle('active', !!on);

    el.addEventListener('mousedown', (ev) => {{ ev.preventDefault(); setActive(true); publish(cmd); }});
    el.addEventListener('mouseup',   () => {{ setActive(false); publish('S'); }});
    el.addEventListener('mouseleave',() => {{ setActive(false); publish('S'); }});
    el.addEventListener('touchstart',(ev) => {{ ev.preventDefault(); setActive(true); publish(cmd); }}, {{passive:false}});
    el.addEventListener('touchend',  () => {{ setActive(false); publish('S'); }});
  }});

  // Keyboard
  window.focus(); document.body.tabIndex = -1; document.body.focus();
  const pressed = {{ArrowUp:false, ArrowDown:false, ArrowLeft:false, ArrowRight:false, Space:false}};
  let lastCmd = '';

  function computeCmd() {{
    if (pressed.Space) return 'S';
    if (pressed.ArrowUp) return 'F';
    if (pressed.ArrowDown) return 'B';
    if (pressed.ArrowLeft) return 'L';
    if (pressed.ArrowRight) return 'R';
    return '';
  }}
  function syncButtons() {{
    document.getElementById('KeyUp').classList.toggle('active', pressed.ArrowUp);
    document.getElementById('KeyDown').classList.toggle('active', pressed.ArrowDown);
    document.getElementById('KeyLeft').classList.toggle('active', pressed.ArrowLeft);
    document.getElementById('KeyRight').classList.toggle('active', pressed.ArrowRight);
    document.getElementById('KeySpace').classList.toggle('active', pressed.Space);
  }}
  function sendIfChanged() {{
    const cmd = computeCmd();
    if (cmd && cmd !== lastCmd) {{ publish(cmd); lastCmd = cmd; }}
    if (!cmd && lastCmd && lastCmd !== 'S') {{ publish('S'); lastCmd = 'S'; }}
    syncButtons();
  }}

  const allow = ['ArrowUp','ArrowDown','ArrowLeft','ArrowRight',' '];
  window.addEventListener('keydown', e => {{
    if (allow.includes(e.key)) {{
      e.preventDefault();
      if (e.key === ' ') pressed.Space = true; else pressed[e.key] = true;
      sendIfChanged();
    }}
  }}, {{passive:false}});
  window.addEventListener('keyup', e => {{
    if (allow.includes(e.key)) {{
      if (e.key === ' ') pressed.Space = false; else pressed[e.key] = false;
      sendIfChanged();
    }}
  }});
  window.addEventListener('blur', () => {{
    Object.keys(pressed).forEach(k => pressed[k] = false);
    syncButtons();
    publish('S'); lastCmd = 'S';
  }});
}})();
</script>
</body>
</html>
""", height=650, scrolling=False)
