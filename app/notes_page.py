import streamlit as st
from app.theme import render_header, get_theme

def render_notes_page():
    theme = get_theme()
    render_header("Notes")

    st.markdown(
        f"<div style='color:{theme['border_color']}; font-size:1.1rem; margin:1.5rem 0;'>No notes available.</div>",
        unsafe_allow_html=True
    )
    # Room for future note input or logs
    st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True) 