import streamlit as st

st.set_page_config(page_title="Robot Car Control Panel", page_icon="🤖")

keyboard_page = st.Page(
    "app/keyboard_controls.py",   # <- path from repo root
    title="Keyboard Controls",
    icon=":material/keyboard:",
    default=True,
)
voice_page = st.Page(
    "app/voice_control.py",
    title="Voice Control",
    icon=":material/record_voice_over:",
)
image_page = st.Page(
    "app/image_control.py",
    title="Image Control",
    icon=":material/image:",
)
pose_page = st.Page(
    "app/pose_control.py",
    title="Pose Control",
    icon=":material/accessibility_new:",
)

pg = st.navigation(
    {"Control Modes": [keyboard_page, voice_page, image_page, pose_page]}
)
pg.run()
