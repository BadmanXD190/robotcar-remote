import streamlit as st

# ========= CONFIG =========
MODEL_ID  = "2ccGPl2N_"                 # your Teachable Machine pose model id
DEVICE_ID = "robotcar_umk1"             # must match ESP32 code
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"
SEND_INTERVAL_MS = 500                  # throttle publishes
VIDEO_W, VIDEO_H = 640, 480             # bigger webcam view
# ==========================

st.title("🕺 Pose Control")
st.caption("Use a Teachable Machine pose model to control the robot via MQTT")

# Small f-string block: only defines JS constants (no braces trouble)
config_js = f"""
<script>
  const MODEL_URL   = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
  const MQTT_URL    = "{BROKER_WS}";
  const TOPIC       = "{TOPIC_CMD}";
  const INTERVAL_MS = {SEND_INTERVAL_MS};
  const CAM_W       = {VIDEO_W};
  const CAM_H       = {VIDEO_H};
</script>
"""

# Everything below is a plain string (not f-string), so JS braces don't need escaping
html = """
<div style="font-family:system-ui,Segoe UI,Roboto,Arial; color:#e5e7eb;">
  <button id="start" style="padding:10px 16px;border-radius:10px;">Start Webcam</button>
  <div id="status" style="margin:10px 0;font-weight:600;">Idle</div>

  <div style="display:flex; gap:24px; align-items:flex-start; flex-wrap:wrap;">
    <!-- Video panel -->
    <div>
      <video id="webcam" autoplay playsinline width="CAM_W" height="CAM_H" style="border-radius:12px; background:#000;"></video>
    </div>

    <!-- Prediction panel -->
    <div style="min-width:220px;">
      <div style="font-size:14px; opacity:.8; margin-bottom:8px;">Sent:</div>
      <div id="label" style="font-size:72px; font-weight:800; line-height:1; color:#ffffff;">–</div>
      <div id="prob"  style="font-size:18px; opacity:.8; margin-top:6px;">0.0%</div>
      <div style="margin-top:16px; font-size:12px; opacity:.7;">
        Publishing raw class to <code style="color:#a3e635;" id="showTopic"></code> on <code style="color:#a3e635;" id="showBroker"></code>
      </div>
    </div>
  </div>
</div>

<!-- Use official TM Pose stack to avoid freezes -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.3.1/dist/tf.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@teachablemachine/pose@0.8/dist/teachablemachine-pose.min.js"></script>

<!-- MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script>
let model, webcam;
let mqttClient = null;
let lastLabel = "";
let lastSent  = 0;

function setStatus(s) {
  const el = document.getElementById("status");
  if (el) el.innerText = s;
}

function initLabels() {
  // fill the info footer
  const t = document.getElementById("showTopic");
  const b = document.getElementById("showBroker");
  if (t) t.textContent = TOPIC;
  if (b) b.textContent = MQTT_URL;
}

function mqttConnect() {
  mqttClient = mqtt.connect(MQTT_URL, {
    clientId: "tm-pose-" + Math.random().toString(16).slice(2,10),
    clean: true,
    reconnectPeriod: 2000,
    protocolVersion: 4
  });
  mqttClient.on("connect",   () => setStatus("MQTT connected ✔️"));
  mqttClient.on("reconnect", () => setStatus("Reconnecting MQTT..."));
  mqttClient.on("error",     (e) => setStatus("MQTT error: " + (e && e.message ? e.message : e)));
}

function publishIfNeeded(label) {
  if (!mqttClient || !mqttClient.connected) return;
  const now = Date.now();
  if (label && (label !== lastLabel || (now - lastSent) > INTERVAL_MS)) {
    mqttClient.publish(TOPIC, label, { qos: 0, retain: false });
    lastLabel = label;
    lastSent  = now;
    setStatus("Sent: " + label);
  }
}

async function init() {
  try {
    initLabels();
    setStatus("Loading pose model...");
    const modelURL = MODEL_URL + "model.json";
    const metadataURL = MODEL_URL + "metadata.json";
    model = await tmPose.load(modelURL, metadataURL);

    setStatus("Starting webcam...");
    const flip = true; // mirror front cam
    webcam = new tmPose.Webcam(CAM_W, CAM_H, flip);
    await webcam.setup(); // ask for permission
    await webcam.play();

    // Replace <video> with TM's canvas
    const vid = document.getElementById("webcam");
    vid.replaceWith(webcam.canvas);
    webcam.canvas.style.borderRadius = "12px";
    webcam.canvas.style.background   = "#000";

    mqttConnect();
    setStatus("Running pose predictions...");
    window.requestAnimationFrame(loop);
  } catch (err) {
    setStatus("Init error: " + (err && err.message ? err.message : err));
    console.error(err);
  }
}

async function loop() {
  // Keep the stream alive
  webcam.update();
  await predict();
  // Small yield helps some browsers keep the camera flowing
  await new Promise(r=>setTimeout(r,0));
  window.requestAnimationFrame(loop);
}

async function predict() {
  // Estimate pose and classify
  const result = await model.estimatePose(webcam.canvas);
  const pose = result.pose;
  const posenetOutput = result.posenetOutput;
  const preds = await model.predict(posenetOutput);
  preds.sort((a,b)=>b.probability - a.probability);

  // Top class
  let label = (preds[0].className || "").trim().toUpperCase();  // e.g., "F","B","L","R","S"
  const p = preds[0].probability || 0;

  // Update UI
  const labelEl = document.getElementById("label");
  const probEl  = document.getElementById("prob");
  if (labelEl) labelEl.textContent = label || "–";
  if (probEl)  probEl.textContent  = (p*100).toFixed(1) + "%";

  // Publish MQTT (throttled)
  publishIfNeeded(label);
}

document.getElementById("start").addEventListener("click", init);
</script>
"""

# Inject constants first, then the main HTML/JS (so the big block can use them)
st.components.v1.html(config_js + html, height=VIDEO_H + 240, scrolling=False)
