import streamlit as st
import os
import sys
from datetime import datetime
from app.theme import get_theme

def render_sidebar():
    theme = get_theme()
    st.sidebar.markdown(f"""
        <div style='font-family: {theme['font']}; color: {theme['primary_color']}; font-size: 1.5rem; margin-bottom: 1.5rem;'>
            <b>Owlin</b>
        </div>
    """, unsafe_allow_html=True)

    # Page selection
    page = st.sidebar.radio(
        'Go to',
        [
            'Dashboard',
            'Invoices',
            'Flagged Issues',
            'Suppliers',
            'Forecast',
            'Notes',
            'Settings',
        ],
        label_visibility='collapsed',
    )

    # Venue selection for GMs
    venue = None
    if st.session_state.get('role') == 'GM':
        venues = ['Waterloo Hotel', 'Royal Oak Hotel', 'Stables Lodge']
        venue = st.sidebar.selectbox('Venue', venues)
        st.session_state['venue'] = venue

    st.sidebar.markdown("""<div style='margin-top:2rem; color:#B0B8C1; font-size:0.9rem;'>Owlin App &copy; 2024</div>""", unsafe_allow_html=True)

    return page 