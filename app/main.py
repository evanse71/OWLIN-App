import streamlit as st
import sys
import os

# Add the parent directory to Python path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.sidebar import render_sidebar
from app.enhanced_invoices_page import main as render_enhanced_invoices_page
from app.flagged_issues_page import render_flagged_issues_page
from app.suppliers_page import render_suppliers_page
from app.forecast_page import render_forecast_page
from app.notes_page import render_notes_page
from app.settings_page import render_settings_page

# Set default session state values
if 'role' not in st.session_state:
    st.session_state['role'] = 'GM'

# Render sidebar and get selected page
selected_page = render_sidebar()

# Page title
st.title(f"Owlin - {selected_page}")

# Page routing
if selected_page == "Dashboard":
    st.write("Dashboard page coming soon.")
elif selected_page == "Invoices":
    render_enhanced_invoices_page()
elif selected_page == "Flagged Issues":
    render_flagged_issues_page()
elif selected_page == "Suppliers":
    render_suppliers_page()
elif selected_page == "Forecast":
    render_forecast_page()
elif selected_page == "Notes":
    render_notes_page()
elif selected_page == "Settings":
    render_settings_page()
else:
    st.write("Unknown page.") 