import streamlit as st

# ========== CONFIG ==========
MODEL_ID  = "DgfbqBv53"                 # your Teachable Machine model id
DEVICE_ID = "robotcar_umk1"             # must match ESP32 code
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"
SEND_INTERVAL_MS = 500                  # throttle publishes
# ============================

st.title("📷 Image-Based Control")
st.caption("Use a Teachable Machine model to control the robot via MQTT")

html = f"""
<div style="font-family:system-ui,Segoe UI,Roboto,Arial">
  <button id="start" style="padding:10px 16px;border-radius:10px;">Start Webcam</button>
  <div id="status" style="margin:10px 0;font-weight:600;">Idle</div>
  <video id="webcam" autoplay playsinline width="320" height="240" style="border-radius:12px"></video>
  <div id="label" style="margin-top:12px;font-size:18px;font-weight:600;"></div>
  <div style="margin-top:8px;font-size:12px;opacity:.7;">
    Publishing raw class to <code>{TOPIC_CMD}</code> on <code>{BROKER_WS}</code>
  </div>
</div>

<!-- Load TF.js + Teachable Machine -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4"></script>
<script src="https://cdn.jsdelivr.net/npm/@teachablemachine/image@0.8/dist/teachablemachine-image.min.js"></script>

<!-- Load MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script>
const MODEL_URL = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
const MQTT_URL  = "{BROKER_WS}";
const TOPIC     = "{TOPIC_CMD}";
const INTERVAL_MS = {SEND_INTERVAL_MS};

let model, webcam;
let mqttClient = null;
let lastLabel = "";
let lastSent = 0;

function setStatus(s) {{
  const el = document.getElementById("status");
  if (el) el.innerText = s;
}}

function mqttConnect() {{
  mqttClient = mqtt.connect(MQTT_URL, {{
    clientId: "tm-" + Math.random().toString(16).slice(2,10),
    clean: true,
    reconnectPeriod: 2000
  }});
  mqttClient.on("connect", () => setStatus("MQTT connected ✔️"));
  mqttClient.on("reconnect", () => setStatus("Reconnecting MQTT..."));
  mqttClient.on("error", (e) => setStatus("MQTT error: " + e.message));
}}

async function init() {{
  setStatus("Loading model...");
  const modelURL = MODEL_URL + "model.json";
  const metadataURL = MODEL_URL + "metadata.json";
  model = await tmImage.load(modelURL, metadataURL);

  setStatus("Starting webcam...");
  webcam = new tmImage.Webcam(320, 240, true);
  await webcam.setup();
  await webcam.play();
  document.getElementById("webcam").replaceWith(webcam.canvas);

  mqttConnect();
  setStatus("Running predictions...");
  window.requestAnimationFrame(loop);
}}

async function loop() {{
  webcam.update();
  await predict();
  window.requestAnimationFrame(loop);
}}

async function predict() {{
  const preds = await model.predict(webcam.canvas);
  preds.sort((a,b)=>b.probability-a.probability);
  let label = preds[0].className || "";
  label = label.trim().toUpperCase();  // "F","B","L","R","S"
  document.getElementById("label").innerText = label;
  publishIfNeeded(label);
}}

function publishIfNeeded(label) {{
  if (!mqttClient || !mqttClient.connected) return;
  const now = Date.now();
  if (label !== lastLabel || (now - lastSent) > INTERVAL_MS) {{
    mqttClient.publish(TOPIC, label, {{ qos: 0, retain: false }});
    setStatus("Sent: " + label);
    lastLabel = label;
    lastSent = now;
    console.log("Published", label, "to", TOPIC);
  }}
}}

document.getElementById("start").addEventListener("click", init);
</script>
"""

st.components.v1.html(html, height=520)
