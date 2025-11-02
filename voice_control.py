import os, json
import streamlit as st
import streamlit.components.v1 as components

# Use same broker as keyboard page (defaults for Mosquitto WSS). Override via secrets if needed.
WSS_HOST = st.secrets.get("WSS_HOST", os.environ.get("WSS_HOST", "test.mosquitto.org"))
WSS_PORT = st.secrets.get("WSS_PORT", os.environ.get("WSS_PORT", "8081"))
WSS_PATH = st.secrets.get("WSS_PATH", os.environ.get("WSS_PATH", "/mqtt"))
DEVICE_ID = st.secrets.get("DEVICE_ID", os.environ.get("DEVICE_ID", "robotcar_umk1"))
KEEPALIVE = int(st.secrets.get("KEEPALIVE", os.environ.get("KEEPALIVE", "30")))
MQTT_USER = st.secrets.get("MQTT_USERNAME", os.environ.get("MQTT_USERNAME", ""))  # usually not needed
MQTT_PASS = st.secrets.get("MQTT_PASSWORD", os.environ.get("MQTT_PASSWORD", ""))

TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"

st.title("🎤 Voice Control")
st.caption("Say: **go**, **back**, **left**, **right**, **stop**")

cfg = {
    "host": WSS_HOST,
    "port": WSS_PORT,
    "path": WSS_PATH if WSS_PATH.startswith("/") else f"/{WSS_PATH}",
    "topicCmd": TOPIC_CMD,
    "keepalive": KEEPALIVE,
    "username": MQTT_USER,
    "password": MQTT_PASS,
}

components.html(f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'self' https: 'unsafe-inline' 'unsafe-eval' data: blob:; connect-src *;">
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
<style>
  :root {{ --bg:#0f172a; --fg:#e5e7eb; --muted:#94a3b8; --accent:#22c55e; --err:#ef4444; }}
  body {{ margin:0; background:var(--bg); color:var(--fg); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }}
  .wrap {{ max-width:800px; margin:10px auto 80px; padding:0 16px; }}
  .row {{ display:flex; gap:10px; align-items:center; margin:8px 0; }}
  button {{
    padding:10px 14px; border-radius:12px; border:1px solid rgba(255,255,255,.15);
    background:rgba(255,255,255,.06); color:var(--fg); font-weight:600; cursor:pointer;
  }}
  button:disabled {{ opacity:.5; cursor:not-allowed; }}
  .green {{ color:var(--accent) }}
  .red {{ color:var(--err) }}
  .box {{ margin-top:12px; padding:12px; border:1px solid rgba(255,255,255,.15); border-radius:12px; background:rgba(255,255,255,.04); }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  #partial {{ opacity:.85; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="row">
    <button id="btnStart">🎙️ Start Listening</button>
    <button id="btnStop" disabled>🛑 Stop</button>
    <span id="status" class="mono">Mic: idle  •  MQTT: connecting…</span>
  </div>

  <div class="box">
    <div><strong>Live transcript</strong></div>
    <div id="final"></div>
    <div id="partial" class="mono"></div>
  </div>

  <div class="box mono" style="margin-top:10px">
    MQTT WSS: wss://{cfg["host"]}:{cfg["port"]}{cfg["path"]} &nbsp;&nbsp; Topic: <code>{TOPIC_CMD}</code>
    <div id="err" class="red"></div>
  </div>
</div>

<script>
(() => {{
  const CFG = {json.dumps(cfg)};
  const btnStart = document.getElementById('btnStart');
  const btnStop  = document.getElementById('btnStop');
  const statusEl = document.getElementById('status');
  const finalEl  = document.getElementById('final');
  const partEl   = document.getElementById('partial');
  const errEl    = document.getElementById('err');

  // --- MQTT over WSS ---
  let client;
  try {{
    const url = "wss://" + CFG.host + ":" + CFG.port + CFG.path;
    const opts = {{
      keepalive: Number(CFG.keepalive || 30),
      reconnectPeriod: 1000,
      clean: true,
      clientId: "rc_voice_" + Math.random().toString(16).slice(2),
      protocolVersion: 4
    }};
    if (CFG.username) opts.username = CFG.username;
    if (CFG.password) opts.password = CFG.password;

    client = mqtt.connect(url, opts);
    client.on('connect', () => {{ statusEl.textContent = "Mic: idle  •  MQTT: connected"; errEl.textContent = ""; }});
    client.on('reconnect', () => {{ statusEl.textContent = "Mic: idle  •  MQTT: reconnecting…"; }});
    client.on('close', () => {{ statusEl.textContent = "Mic: idle  •  MQTT: disconnected"; }});
    client.on('error', (e) => {{ errEl.textContent = "MQTT error: " + (e.message||e); }});
  }} catch (e) {{
    errEl.textContent = "MQTT init error: " + (e.message||e);
  }}

  const publish = (msg) => {{
    try {{ if (client && client.connected) client.publish(CFG.topicCmd, msg); }}
    catch (e) {{ errEl.textContent = "publish error: " + (e.message||e); }}
  }};

  // --- Speech Recognition (Web Speech API) ---
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {{
    errEl.textContent = "Web Speech API not supported in this browser. Use Chrome/Edge.";
  }}

  let rec; let running = false; let lastCmd = ""; let lastCmdAt = 0;

  function startRec() {{
    if (!SpeechRecognition || running) return;
    rec = new SpeechRecognition();
    rec.lang = 'en-US';
    rec.interimResults = true;   // show partials
    rec.continuous = true;       // keep listening
    running = true;

    finalEl.innerHTML = "";
    partEl.textContent = "";
    statusEl.textContent = "Mic: listening…  •  MQTT: " + (client && client.connected ? "connected" : "connecting…");
    btnStart.disabled = true; btnStop.disabled = false;

    rec.onresult = (e) => {{
      let interim = "";
      let commit  = "";
      for (let i = e.resultIndex; i < e.results.length; ++i) {{
        const r = e.results[i];
        if (r.isFinal) commit += r[0].transcript;
        else interim += r[0].transcript;
      }}
      if (interim) partEl.textContent = interim;
      if (commit) {{
        partEl.textContent = "";
        const text = commit.trim();
        if (text) {{
          const p = document.createElement('p'); p.textContent = text;
          finalEl.appendChild(p);
          handleCommand(text);
        }}
      }}
    }};
    rec.onerror = (e) => {{ errEl.textContent = "speech error: " + (e.error||e.message||e); }};
    rec.onend = () => {{
      // Auto-restart to stay continuous if still running
      if (running) rec.start();
      else statusEl.textContent = "Mic: stopped  •  MQTT: " + (client && client.connected ? "connected" : "disconnected");
    }};
    rec.start();
  }}

  function stopRec() {{
    running = false;
    try {{ rec && rec.stop(); }} catch (e) {{}}
    btnStart.disabled = false; btnStop.disabled = true;
  }}

  // Map voice → command, avoid spamming same command rapidly
  function handleCommand(text) {{
    const s = text.toLowerCase();
    let cmd = "";
    if (/(^|\\b)(go|forward|start)(\\b|$)/.test(s)) cmd = "F";
    else if (/(^|\\b)(back|backward|reverse)(\\b|$)/.test(s)) cmd = "B";
    else if (/(^|\\b)(left|turn left)(\\b|$)/.test(s)) cmd = "L";
    else if (/(^|\\b)(right|turn right)(\\b|$)/.test(s)) cmd = "R";
    else if (/(^|\\b)(stop|halt|freeze)(\\b|$)/.test(s)) cmd = "S";

    const now = Date.now();
    if (cmd && (cmd !== lastCmd || now - lastCmdAt > 600)) {{
      publish(cmd);
      lastCmd = cmd; lastCmdAt = now;
    }}
  }}

  // Buttons
  btnStart.addEventListener('click', startRec);
  btnStop.addEventListener('click',  stopRec);
}})();
</script>
</body>
</html>
""", height=560, scrolling=False)
