import streamlit as st
import sqlite3
from datetime import datetime, timedelta
from components.supplier_scorecard import render_supplier_scorecard

DB_PATH = 'data/owlin.db'

# --- Helper: Get all suppliers alphabetically ---
def get_suppliers():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM suppliers ORDER BY name ASC")
        suppliers = cur.fetchall()
        conn.close()
        return suppliers
    except Exception as e:
        st.error(f"Error loading suppliers: {e}")
        return []

def get_default_dates():
    end = datetime.today()
    start = end - timedelta(days=30)
    return start, end

# --- SIDEBAR NAVIGATION ---
def render_sidebar():
    st.sidebar.title("OWLIN Navigation")
    role = st.session_state.get("role", "User")
    nav_options = ["Invoices", "Suppliers"]
    nav_map = {"Invoices": "invoices", "Suppliers": "suppliers"}
    if role in ("GM", "Finance"):
        nav_options += ["Product Trends", "Supplier Scorecard"]
        nav_map["Product Trends"] = "product_trends"
        nav_map["Supplier Scorecard"] = "supplier_scorecard"
    selected = st.sidebar.radio("Go to", nav_options)
    return nav_map[selected]

# --- PAGE ROUTING ---
def main():
    page = render_sidebar()
    if page == "invoices":
        # Import and run the invoice functionality
        try:
            from invoices_page_refactored import render_invoices_page
            render_invoices_page()
        except ImportError:
            st.error("Invoice functionality not available. Please check the invoices_page_refactored.py file.")
        except Exception as e:
            st.error(f"Error loading invoice page: {e}")
    elif page == "suppliers":
        render_supplier_page()
    elif page == "product_trends":
        # The product_trend_page.py is a standalone Streamlit page and will run on import
        import pages.product_trend_page
    elif page == "supplier_scorecard":
        st.title("Supplier Scorecard")
        st.write("Select a supplier to view their scorecard.")
        suppliers = get_suppliers()
        supplier_options = {name: sid for sid, name in suppliers}
        supplier_name = st.selectbox(
            "Select Supplier",
            options=["-- Select --"] + list(supplier_options.keys()),
            index=0,
        )
        supplier_id = supplier_options.get(supplier_name)
        if supplier_id:
            render_supplier_scorecard(supplier_id)

# --- SUPPLIER PAGE LAYOUT ---
def render_supplier_page():
    st.set_page_config(page_title="Supplier Overview", layout="wide")
    st.title("Supplier Overview")
    with st.container():
        col1, col2, col3 = st.columns([3, 3, 2])
        with col1:
            suppliers = get_suppliers()
            supplier_options = {name: sid for sid, name in suppliers}
            supplier_name = st.selectbox(
                "Select Supplier",
                options=["-- Select --"] + list(supplier_options.keys()),
                index=0,
            )
            supplier_id = supplier_options.get(supplier_name)
        with col2:
            default_start, default_end = get_default_dates()
            date_range = st.date_input(
                "Date Range",
                value=(default_start, default_end),
                min_value=datetime(2000, 1, 1),
                max_value=datetime.today(),
                format="YYYY-MM-DD",
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = default_start, default_end
        with col3:
            st.write("")  # spacing
            st.write("")
            export_btn = st.button("Export All Supplier Reports", help="Coming soon!")
            if export_btn:
                st.info("Export functionality coming soon.")
    st.markdown("---")
    if supplier_id:
        render_supplier_scorecard(supplier_id)
    else:
        st.info("Please select a supplier to view their performance summary.")

if __name__ == "__main__":
    main() 