import streamlit as st
import sounddevice as sd
import numpy as np
import threading
import queue
import paho.mqtt.client as mqtt
from faster_whisper import WhisperModel

# ---------------------------
# MQTT CONFIG
# ---------------------------
BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC_CMD = "rc/robotcar_umk1/cmd"

# ---------------------------
# INIT
# ---------------------------
st.title("🎤 Voice Control")
st.write("Click **Start Listening** and speak commands like 'go', 'back', 'left', 'right', or 'stop'.")

if "listening" not in st.session_state:
    st.session_state.listening = False
if "transcript" not in st.session_state:
    st.session_state.transcript = ""

# ---------------------------
# MQTT CLIENT
# ---------------------------
client = mqtt.Client()
client.connect(BROKER, PORT, 60)
client.loop_start()

# ---------------------------
# LOAD WHISPER MODEL
# ---------------------------
@st.cache_resource
def load_model():
    return WhisperModel("base", device="cpu", compute_type="int8")
model = load_model()

# ---------------------------
# AUDIO + TRANSCRIPTION THREAD
# ---------------------------
audio_q = queue.Queue()
def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    audio_q.put(indata.copy())

def listen_and_transcribe():
    with sd.InputStream(samplerate=16000, channels=1, callback=audio_callback):
        st.session_state.transcript = ""
        st.session_state.listening = True
        st.experimental_rerun()

        audio_buffer = np.zeros(0, dtype=np.float32)

        while st.session_state.listening:
            while not audio_q.empty():
                data = audio_q.get()
                audio_buffer = np.concatenate((audio_buffer, data.flatten()))

                # process every ~2 seconds of audio
                if len(audio_buffer) >= 32000:
                    segment = np.copy(audio_buffer)
                    audio_buffer = np.zeros(0, dtype=np.float32)
                    segments, _ = model.transcribe(segment, language="en")

                    text_chunk = " ".join([s.text for s in segments]).strip()
                    if text_chunk:
                        st.session_state.transcript += " " + text_chunk
                        st.experimental_rerun()

                        # --- COMMAND MAPPING ---
                        lower = text_chunk.lower()
                        if "go" in lower:
                            client.publish(TOPIC_CMD, "F")
                        elif "back" in lower or "backward" in lower:
                            client.publish(TOPIC_CMD, "B")
                        elif "left" in lower:
                            client.publish(TOPIC_CMD, "L")
                        elif "right" in lower:
                            client.publish(TOPIC_CMD, "R")
                        elif "stop" in lower or "halt" in lower:
                            client.publish(TOPIC_CMD, "S")

# ---------------------------
# STREAMLIT UI
# ---------------------------
col1, col2 = st.columns(2)
if col1.button("🎙️ Start Listening", disabled=st.session_state.listening):
    thread = threading.Thread(target=listen_and_transcribe, daemon=True)
    thread.start()

if col2.button("🛑 Stop Listening", disabled=not st.session_state.listening):
    st.session_state.listening = False
    st.experimental_rerun()

st.subheader("Live Transcript:")
st.write(st.session_state.transcript if st.session_state.transcript else "🎧 Waiting for speech...")

