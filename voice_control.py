import streamlit as st

# ========= CONFIG =========
MODEL_ID  = "6_YbLoW0i"                 # your Teachable Machine Audio model ID
DEVICE_ID = "robotcar_umk1"             # must match your ESP32 device ID
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"
PROB_THRESHOLD = 0.75                   # minimum confidence to send
INTERVAL_MS = 1000                      # throttle publishes
# ==========================

st.title("🎤 Voice Control")
st.caption("Use your Teachable Machine Audio model to control the robot car via MQTT.")

html = f"""
<div style="font-family:system-ui,Segoe UI,Roboto,Arial; color:#e5e7eb;">
  <button id="toggle" style="padding:10px 16px;border-radius:10px;">Start Listening</button>
  <div id="status" style="margin:10px 0;font-weight:600;">Idle</div>

  <div style="min-width:220px;">
    <div style="font-size:14px; opacity:.8; margin-bottom:8px;">Detected:</div>
    <div id="label" style="font-size:64px; font-weight:900; line-height:1; color:#ffffff;">–</div>
    <div id="prob"  style="font-size:18px; opacity:.8; margin-top:6px;">0.0%</div>
    <div style="margin-top:16px; font-size:12px; opacity:.7;">
      Publishing raw label to <code style="color:#a3e635;">{TOPIC_CMD}</code> on <code style="color:#a3e635;">{BROKER_WS}</code>
    </div>
  </div>
</div>

<!-- TensorFlow.js + Speech Commands -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.3.1/dist/tf.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/speech-commands@0.4.0/dist/speech-commands.min.js"></script>

<!-- MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script>
const MODEL_URL  = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
const MQTT_URL   = "{BROKER_WS}";
const TOPIC      = "{TOPIC_CMD}";
const PROB_THRESHOLD = {PROB_THRESHOLD};
const INTERVAL_MS = {INTERVAL_MS};

let recognizer = null;
let listening  = false;
let mqttClient = null;
let lastLabel  = "";
let lastSent   = 0;

function setStatus(msg) {{
  const el = document.getElementById("status");
  if (el) el.innerText = msg;
}}

function mqttConnect() {{
  if (mqttClient && mqttClient.connected) return;
  mqttClient = mqtt.connect(MQTT_URL, {{
    clientId: "tm-voice-" + Math.random().toString(16).slice(2,10),
    clean: true,
    reconnectPeriod: 2000
  }});
  mqttClient.on("connect",   () => setStatus("MQTT connected ✔️"));
  mqttClient.on("reconnect", () => setStatus("Reconnecting MQTT..."));
  mqttClient.on("error",     (e) => setStatus("MQTT error: " + (e?.message || e)));
}}

function mqttPublish(label) {{
  if (!mqttClient || !mqttClient.connected) return;
  mqttClient.publish(TOPIC, label, {{ qos: 0, retain: false }});
  console.log("Published:", label);
}}

function maybePublish(label, prob) {{
  const now = Date.now();
  if (prob < PROB_THRESHOLD) return;
  if (label && (label !== lastLabel || now - lastSent > INTERVAL_MS)) {{
    mqttPublish(label);
    setStatus("Sent: " + label);
    lastLabel = label;
    lastSent  = now;
  }}
}}

function setButton() {{
  const btn = document.getElementById("toggle");
  btn.textContent = listening ? "Stop Listening" : "Start Listening";
  btn.style.background = listening ? "#c62828" : "#2e7d32";
  btn.style.color = "white";
}}

async function createModel() {{
  const checkpointURL = MODEL_URL + "model.json";
  const metadataURL   = MODEL_URL + "metadata.json";
  recognizer = speechCommands.create("BROWSER_FFT", undefined, checkpointURL, metadataURL);
  await recognizer.ensureModelLoaded();
  setStatus("Model loaded ✔️");
}}

async function startListening() {{
  mqttConnect();
  if (!recognizer) await createModel();

  const labels = recognizer.wordLabels();
  setStatus("Listening… (allow microphone)");
  listening = true;
  setButton();

  recognizer.listen(result => {{
    const scores = result.scores;
    let topIndex = 0;
    for (let i = 1; i < scores.length; i++) {{
      if (scores[i] > scores[topIndex]) topIndex = i;
    }}
    const label = labels[topIndex].trim().toUpperCase();
    const prob  = scores[topIndex];
    document.getElementById("label").innerText = label;
    document.getElementById("prob").innerText  = (prob*100).toFixed(1) + "%";
    maybePublish(label, prob);
  }}, {{
    includeSpectrogram: false,
    probabilityThreshold: 0,
    overlapFactor: 0.5
  }});
}}

function stopListening() {{
  if (!listening) return;
  recognizer.stopListening();
  listening = false;
  setButton();
  setStatus("Stopped (MQTT still connected)");
}}

document.getElementById("toggle").addEventListener("click", () => {{
  if (listening) stopListening();
  else startListening();
}});
</script>
"""

st.components.v1.html(html, height=420, scrolling=False)
