import streamlit as st

st.title("🕺 Pose Control")
st.caption("Use Teachable Machine pose model to control your ESP32 robot car via MQTT.")

MODEL_ID = "rveXhwfWN"
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = "rc/robotcar_umk1/cmd"

html = f"""
<div style="font-family:system-ui,Segoe UI,Roboto,Arial">
  <h4>Teachable Machine Pose Model</h4>
  <button type="button" onclick="init()" style="padding:10px 16px;border-radius:10px;">Start</button>
  <div><canvas id="canvas"></canvas></div>
  <div id="label-container" style="margin-top:10px;"></div>
  <div style="margin-top:8px;font-size:12px;opacity:.7;">
    Publishing to <code>{TOPIC_CMD}</code> on <code>{BROKER_WS}</code>
  </div>
</div>

<!-- TensorFlow + Teachable Machine -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.3.1/dist/tf.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@teachablemachine/pose@0.8/dist/teachablemachine-pose.min.js"></script>

<!-- MQTT.js -->
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script type="text/javascript">
const URL = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
const MQTT_URL = "{BROKER_WS}";
const TOPIC_CMD = "{TOPIC_CMD}";
let model, webcam, ctx, labelContainer, maxPredictions;
let mqttClient = null;

// ===== MQTT Connection =====
function mqttConnect() {{
  mqttClient = mqtt.connect(MQTT_URL, {{
    clientId: "pose-" + Math.random().toString(16).slice(2,8),
    clean: true,
    reconnectPeriod: 2000
  }});
  mqttClient.on("connect", () => console.log("MQTT connected ✔️"));
  mqttClient.on("reconnect", () => console.log("Reconnecting MQTT..."));
  mqttClient.on("error", err => console.log("MQTT error:", err));
}}

function publishPose(label) {{
  if (mqttClient && mqttClient.connected) {{
    mqttClient.publish(TOPIC_CMD, label, {{ qos: 0, retain: false }});
    console.log("Published:", label);
  }}
}}

// ===== Teachable Machine Pose =====
async function init() {{
  mqttConnect(); // connect MQTT first
  const modelURL = URL + "model.json";
  const metadataURL = URL + "metadata.json";
  model = await tmPose.load(modelURL, metadataURL);
  maxPredictions = model.getTotalClasses();

  const size = 300;
  const flip = true;
  webcam = new tmPose.Webcam(size, size, flip);
  await webcam.setup();
  await webcam.play();
  window.requestAnimationFrame(loop);

  const canvas = document.getElementById("canvas");
  canvas.width = size; canvas.height = size;
  ctx = canvas.getContext("2d");
  labelContainer = document.getElementById("label-container");
  for (let i = 0; i < maxPredictions; i++) {{
    const div = document.createElement("div");
    div.style.fontSize = "16px";
    div.style.margin = "2px 0";
    labelContainer.appendChild(div);
  }}
}}

async function loop(timestamp) {{
  webcam.update();
  await predict();
  window.requestAnimationFrame(loop);
}}

async function predict() {{
  const {{ pose, posenetOutput }} = await model.estimatePose(webcam.canvas);
  const prediction = await model.predict(posenetOutput);

  // Find highest probability
  prediction.sort((a,b)=>b.probability - a.probability);
  const top = prediction[0];
  const label = top.className;
  const prob = top.probability.toFixed(2);

  // Update label display
  for (let i = 0; i < maxPredictions; i++) {{
    const p = prediction[i];
    const text = p.className + ": " + p.probability.toFixed(2);
    labelContainer.childNodes[i].innerHTML = text;
  }}

  publishPose(label); // send top prediction
  drawPose(pose);
}}

function drawPose(pose) {{
  if (webcam.canvas) {{
    ctx.drawImage(webcam.canvas, 0, 0);
    if (pose) {{
      const minPartConfidence = 0.5;
      tmPose.drawKeypoints(pose.keypoints, minPartConfidence, ctx);
      tmPose.drawSkeleton(pose.keypoints, minPartConfidence, ctx);
    }}
  }}
}}
</script>
"""

st.components.v1.html(html, height=520)
