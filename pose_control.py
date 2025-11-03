import streamlit as st

# ========== CONFIG ==========
MODEL_ID  = "rveXhwfWN"                 # your Teachable Machine pose model id
DEVICE_ID = "robotcar_umk1"             # must match ESP32 code
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"
SEND_INTERVAL_MS = 500                  # throttle publishes
VIDEO_W, VIDEO_H = 320, 240            # smaller webcam view
# ============================

st.title("🕺 Pose-Based Control")
st.caption("Use a Teachable Machine Pose model to control the robot via MQTT")

html = f"""
<div style="font-family:system-ui,Segoe UI,Roboto,Arial; color:#e5e7eb;">
  <button id="start" style="padding:10px 16px;border-radius:10px;">Start Webcam</button>
  <div id="status" style="margin:10px 0;font-weight:600;">Idle</div>

  <div style="display:flex; gap:24px; align-items:flex-start; flex-wrap:wrap;">
    <!-- Video panel -->
    <div>
      <video id="webcam" autoplay playsinline width="{VIDEO_W}" height="{VIDEO_H}" style="border-radius:12px; background:#000;"></video>
    </div>

    <!-- Prediction panel -->
    <div style="min-width:220px;">
      <div style="font-size:14px; opacity:.8; margin-bottom:8px;">Sent:</div>
      <div id="label" style="font-size:72px; font-weight:800; line-height:1; color:#ffffff;">–</div>
      <div id="prob"  style="font-size:18px; opacity:.8; margin-top:6px;">0.0%</div>
      <div style="margin-top:16px; font-size:12px; opacity:.7;">
        Publishing raw class to <code style="color:#a3e635;">{TOPIC_CMD}</code> on <code style="color:#a3e635;">{BROKER_WS}</code>
      </div>
    </div>
  </div>
</div>

<!-- TF.js + Teachable Machine Pose -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.3.1/dist/tf.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@teachablemachine/pose@0.8/dist/teachablemachine-pose.min.js"></script>

<!-- MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script>
const MODEL_URL   = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
const MQTT_URL    = "{BROKER_WS}";
const TOPIC       = "{TOPIC_CMD}";
const INTERVAL_MS = {SEND_INTERVAL_MS};
const CAM_W       = {VIDEO_W};
const CAM_H       = {VIDEO_H};

let model, webcam;
let mqttClient = null;
let lastLabel = "";
let lastSent  = 0;

function setStatus(s) {{
  const el = document.getElementById("status");
  if (el) el.innerText = s;
}}

function mqttConnect() {{
  mqttClient = mqtt.connect(MQTT_URL, {{
    clientId: "pose-" + Math.random().toString(16).slice(2,10),
    clean: true,
    reconnectPeriod: 2000,
    protocolVersion: 4
  }});
  mqttClient.on("connect",   () => setStatus("MQTT connected ✔️"));
  mqttClient.on("reconnect", () => setStatus("Reconnecting MQTT..."));
  mqttClient.on("error",     (e) => setStatus("MQTT error: " + (e?.message || e)));
}}

async function init() {{
  try {{
    setStatus("Loading pose model...");
    const modelURL = MODEL_URL + "model.json";
    const metadataURL = MODEL_URL + "metadata.json";
    model = await tmPose.load(modelURL, metadataURL);

    setStatus("Starting webcam...");
    const flip = true;
    webcam = new tmPose.Webcam(CAM_W, CAM_H, flip);
    await webcam.setup();
    await webcam.play();

    const vid = document.getElementById("webcam");
    vid.replaceWith(webcam.canvas);
    webcam.canvas.style.borderRadius = "12px";
    webcam.canvas.style.background   = "#000";

    mqttConnect();
    setStatus("Running pose predictions...");
    window.requestAnimationFrame(loop);
  }} catch (err) {{
    setStatus("Init error: " + (err?.message || err));
    console.error(err);
  }}
}}

async function loop() {{
  webcam.update();
  await predict();
  await new Promise(r=>setTimeout(r,0)); // yield
  window.requestAnimationFrame(loop);
}}

async function predict() {{
  const {{ pose, posenetOutput }} = await model.estimatePose(webcam.canvas);
  const preds = await model.predict(posenetOutput);
  preds.sort((a,b)=>b.probability-a.probability);

  const label = (preds[0].className || "").trim().toUpperCase();
  const p = preds[0].probability || 0;

  const labelEl = document.getElementById("label");
  const probEl  = document.getElementById("prob");
  if (labelEl) labelEl.textContent = label || "–";
  if (probEl)  probEl.textContent  = (p*100).toFixed(1) + "%";

  publishIfNeeded(label);
}}

function publishIfNeeded(label) {{
  if (!mqttClient || !mqttClient.connected) return;
  const now = Date.now();
  if (label && (label !== lastLabel || (now - lastSent) > INTERVAL_MS)) {{
    mqttClient.publish(TOPIC, label, {{ qos: 0, retain: false }});
    lastLabel = label;
    lastSent  = now;
    setStatus("Sent: " + label);
  }}
}}

document.getElementById("start").addEventListener("click", init);
</script>
"""

st.components.v1.html(html, height=VIDEO_H + 220, scrolling=False)
