# app/main.py
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Robot Car Control Panel", page_icon="🤖")

APP_DIR = Path(__file__).parent.resolve()

keyboard_page = st.Page(
    str((APP_DIR / "keyboard_controls.py").resolve()),
    title="Keyboard Controls",
    icon=":material/keyboard:",
    default=True,
)

voice_page = st.Page(
    str((APP_DIR / "voice_control.py").resolve()),
    title="Voice Control",
    icon=":material/record_voice_over:",
)

image_page = st.Page(
    str((APP_DIR / "image_control.py").resolve()),
    title="Image Control",
    icon=":material/image:",
)

pose_page = st.Page(
    str((APP_DIR / "pose_control.py").resolve()),
    title="Pose Control",
    icon=":material/accessibility_new:",
)

pg = st.navigation({"Control Modes": [keyboard_page, voice_page, image_page, pose_page]})
pg.run()
