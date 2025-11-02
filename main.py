import streamlit as st

st.set_page_config(page_title="Robot Car Control Panel", page_icon="🤖")

keyboard_page = st.Page('keyboard_control.py', title='Keyboard Controls', icon=":material/keyboard:", default=True)
voice_page    = st.Page('voice_control.py',   title='Voice Control',     icon=":material/record_voice_over:")
image_page    = st.Page('image_control.py',   title='Image Control',     icon=":material/image:")
pose_page     = st.Page('pose_control.py',    title='Pose Control',      icon=":material/accessibility_new:")

pg = st.navigation({"Control Modes": [keyboard_page, voice_page, image_page, pose_page]})
pg.run()
