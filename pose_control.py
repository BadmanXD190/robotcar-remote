import streamlit as st

MODEL_ID  = "2ccGPl2N_"
DEVICE_ID = "robotcar_umk1"
BROKER_WS = "wss://test.mosquitto.org:8081/mqtt"
TOPIC_CMD = f"rc/{DEVICE_ID}/cmd"
SEND_INTERVAL_MS = 500
VIDEO_W, VIDEO_H = 640, 480

st.title("🕺 Pose Control")
st.caption("Use a Teachable Machine Pose model to control the robot via MQTT")

html = """
<script>
const MODEL_URL   = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
const MQTT_URL    = "{BROKER_WS}";
const TOPIC       = "{TOPIC_CMD}";
const INTERVAL_MS = {SEND_INTERVAL_MS};
const CAM_W       = {VIDEO_W};
const CAM_H       = {VIDEO_H};

let model, webcam;
async function init() {{
  const modelURL = MODEL_URL + "model.json";
  const metadataURL = MODEL_URL + "metadata.json";
  model = await tmPose.load(modelURL, metadataURL);
  webcam = new tmPose.Webcam(CAM_W, CAM_H, true);
  await webcam.setup();
  await webcam.play();
  document.getElementById("webcam").replaceWith(webcam.canvas);
  window.requestAnimationFrame(loop);
}}
async function loop() {{
  webcam.update();
  await predict();
  await new Promise(r=>setTimeout(r,0));
  window.requestAnimationFrame(loop);
}}
async function predict() {{
  const {{ pose, posenetOutput }} = await model.estimatePose(webcam.canvas);
  const prediction = await model.predict(posenetOutput);
  prediction.sort((a,b)=>b.probability-a.probability);
  const top = prediction[0];
  document.getElementById("label").innerText = top.className;
  document.getElementById("prob").innerText = (top.probability*100).toFixed(1)+"%";
}}
document.getElementById("start").addEventListener("click", init);
</script>

<div style="font-family:system-ui;color:#e5e7eb;">
  <button id="start">Start Webcam</button>
  <video id="webcam" autoplay playsinline width="{VIDEO_W}" height="{VIDEO_H}" style="border-radius:12px;background:#000;"></video>
  <div id="label" style="font-size:72px;font-weight:800;color:white;">–</div>
  <div id="prob" style="font-size:18px;opacity:.8;">0%</div>
</div>
""".format(
    MODEL_ID=MODEL_ID,
    BROKER_WS=BROKER_WS,
    TOPIC_CMD=TOPIC_CMD,
    SEND_INTERVAL_MS=SEND_INTERVAL_MS,
    VIDEO_W=VIDEO_W,
    VIDEO_H=VIDEO_H,
)

st.components.v1.html(html, height=VIDEO_H + 240, scrolling=False)
