import streamlit as st
from app.theme import render_header, get_theme

def render_settings_page():
    theme = get_theme()
    render_header("Settings")

    st.markdown(
        f"<div style='color:{theme['border_color']}; font-size:1.1rem; margin:1.5rem 0;'>Settings will be available here.</div>",
        unsafe_allow_html=True
    )
    # Room for future user and venue management UI
    st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True) 