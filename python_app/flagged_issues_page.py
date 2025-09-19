import streamlit as st
import pandas as pd
import sqlite3
import os
from app.theme import render_header, render_divider, get_theme

def get_db_connection():
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn

def load_flagged_items(conn):
    try:
        df = pd.read_sql_query("SELECT * FROM invoices_line_items WHERE flagged = 1", conn)
        return df
    except Exception as e:
        st.error(f"Error loading flagged issues: {e}")
        return pd.DataFrame()

def render_flagged_issues_page():
    theme = get_theme()
    render_header("Flagged Issues")
    conn = get_db_connection()
    df = load_flagged_items(conn)
    flagged_count = len(df)

    st.markdown(f"<div style='color:{theme['primary_color']}; font-size:1.1rem; margin-bottom:0.5rem;'><b>{flagged_count} flagged item{'s' if flagged_count != 1 else ''}</b></div>", unsafe_allow_html=True)
    render_divider()

    if flagged_count == 0:
        st.markdown(f"<div style='color:{theme['border_color']}; font-size:1.1rem; margin:2rem 0;'>No flagged issues found.</div>", unsafe_allow_html=True)
        return

    # Show flagged items in a styled table with action buttons
    for idx, row in df.iterrows():
        with st.container():
            bg = f"background:{theme['alert_color']}20; border-radius:0.5rem; padding:1rem; margin-bottom:1rem;"
            st.markdown(f"<div style='{bg}'>", unsafe_allow_html=True)
            st.markdown(f"<b>Item:</b> {row['item']}<br>"
                        f"<b>Qty:</b> {row['qty']}<br>"
                        f"<b>Price:</b> {row['price']}<br>"
                        f"<b>Source:</b> {row['source']}<br>"
                        f"<b>Uploaded:</b> {row['upload_timestamp']}", unsafe_allow_html=True)
            col1, col2 = st.columns([1,1])
            with col1:
                if st.button("Resolve", key=f"resolve_{row['id']}"):
                    st.markdown(f"<div style='background:{theme['secondary_color']}; color:white; padding:0.5rem 1rem; border-radius:0.5rem; margin:0.5rem 0;'>Marked as resolved (mock action).</div>", unsafe_allow_html=True)
            with col2:
                if st.button("Escalate", key=f"escalate_{row['id']}"):
                    st.markdown(f"<div style='background:{theme['critical_color']}; color:white; padding:0.5rem 1rem; border-radius:0.5rem; margin:0.5rem 0;'>Escalated for review (mock action).</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    render_divider() 