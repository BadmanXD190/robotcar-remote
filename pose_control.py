import streamlit as st

st.title("🕺 Pose Control")
st.caption("Run the official Teachable Machine pose model in browser and publish results.")

MODEL_ID = "rveXhwfWN"

html = f"""
<div>Teachable Machine Pose Model</div>
<button type="button" onclick="init()">Start</button>
<div><canvas id="canvas"></canvas></div>
<div id="label-container"></div>

<!-- Load TF + TM Pose -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@1.3.1/dist/tf.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@teachablemachine/pose@0.8/dist/teachablemachine-pose.min.js"></script>

<script type="text/javascript">
const URL = "https://teachablemachine.withgoogle.com/models/{MODEL_ID}/";
let model, webcam, ctx, labelContainer, maxPredictions;

async function init() {{
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
    canvas.width = size;
    canvas.height = size;
    ctx = canvas.getContext("2d");
    labelContainer = document.getElementById("label-container");
    for (let i = 0; i < maxPredictions; i++) {{
        labelContainer.appendChild(document.createElement("div"));
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

    for (let i = 0; i < maxPredictions; i++) {{
        const classPrediction =
            prediction[i].className + ": " + prediction[i].probability.toFixed(2);
        labelContainer.childNodes[i].innerHTML = classPrediction;
    }}
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
