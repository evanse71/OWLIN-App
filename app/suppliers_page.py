import streamlit as st
import pandas as pd
import sqlite3
import os
from app.theme import render_header, render_divider, get_theme
from io import BytesIO

def get_db_connection():
    db_path = os.path.join("data", "owlin.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn

def load_invoice_data(conn):
    try:
        df = pd.read_sql_query("SELECT * FROM invoices_line_items", conn)
        return df
    except Exception as e:
        st.error(f"Error loading invoice data: {e}")
        return pd.DataFrame()

def compute_supplier_analytics(df):
    if df.empty:
        return pd.DataFrame()
    grouped = df.groupby('item').agg(
        total_invoices=('id', 'count'),
        mismatch_count=('flagged', 'sum'),
        mismatch_rate=('flagged', 'mean'),
        avg_price=('price', 'mean'),
        price_volatility=('price', 'std')
    ).reset_index()
    grouped['mismatch_rate'] = (grouped['mismatch_rate'] * 100).round(1)
    grouped['price_volatility'] = grouped['price_volatility'].fillna(0).round(3)
    return grouped

def load_invoice_summary(conn):
    try:
        df = pd.read_sql_query("""
            SELECT 
                COALESCE(invoice_number, 'Unknown') as invoice_number,
                COALESCE(invoice_date, 'Unknown') as invoice_date,
                COALESCE(supplier, item, 'Unknown') as supplier,
                SUM(qty * price) as total_value,
                SUM(CASE WHEN flagged = 1 THEN 1 ELSE 0 END) as flagged_count
            FROM invoices_line_items
            GROUP BY invoice_number, invoice_date, supplier
            ORDER BY invoice_date DESC
        """, conn)
        return df
    except Exception as e:
        st.error(f"Error loading invoice summary: {e}")
        return pd.DataFrame()

def render_suppliers_page():
    theme = get_theme()
    render_header("Suppliers")
    conn = get_db_connection()
    df = load_invoice_data(conn)
    analytics_df = compute_supplier_analytics(df)

    # Load summary data
    invoice_df = load_invoice_summary(conn)
    detailed_df = pd.read_sql_query("SELECT * FROM invoices_line_items", conn)

    # Compute summary metrics
    total_value = invoice_df['total_value'].sum() if not invoice_df.empty else 0
    no_issues = invoice_df['flagged_count'].sum() if not invoice_df.empty else 0

    # Compute total error: sum of absolute discrepancies for flagged items
    if not detailed_df.empty and 'flagged' in detailed_df.columns:
        flagged_items = detailed_df[detailed_df['flagged'] == 1]
        error_series = flagged_items['qty'] * flagged_items['price']
        total_error = pd.Series(error_series).abs().sum()
    else:
        total_error = 0

    # --- Top Summary Panel ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div style='background:{theme['secondary_color']}; color:white; border-radius:0.7rem; padding:1.1rem 1rem; text-align:center; font-size:1.25rem; font-weight:600;'>
                £{total_value:,.2f}<br><span style='font-size:1rem; font-weight:400;'>Total Value</span>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div style='background:{theme['alert_color']}; color:white; border-radius:0.7rem; padding:1.1rem 1rem; text-align:center; font-size:1.25rem; font-weight:600;'>
                {int(no_issues)}<br><span style='font-size:1rem; font-weight:400;'>No. Issues</span>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div style='background:{theme['primary_color']}; color:white; border-radius:0.7rem; padding:1.1rem 1rem; text-align:center; font-size:1.25rem; font-weight:600;'>
                £{total_error:,.2f}<br><span style='font-size:1rem; font-weight:400;'>Total Error</span>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

    # --- Invoice Cards Grid ---
    if not invoice_df.empty:
        st.markdown(f"<div style='font-weight:600; color:{theme['primary_color']}; margin-bottom:0.5rem;'>Invoices</div>", unsafe_allow_html=True)
        cols_per_row = 3
        for i in range(0, len(invoice_df), cols_per_row):
            row = invoice_df.iloc[i:i+cols_per_row]
            cols = st.columns(len(row))
            for idx, (col, (_, inv)) in enumerate(zip(cols, row.iterrows())):
                # Status icon
                if inv['flagged_count'] == 0:
                    icon = "✅"
                    icon_color = theme['secondary_color']
                else:
                    icon = "⚠️"
                    icon_color = theme['alert_color']
                card_html = f"""
                <div style="
                    border-radius: 1rem;
                    background: {theme['background']};
                    box-shadow: 0 2px 8px #0001;
                    padding: 1.2rem 1rem 1rem 1rem;
                    margin-bottom: 1rem;
                    border: 1.5px solid {theme['border_color']};
                    min-height: 120px;
                ">
                    <div style="font-size:1.6rem; float:right; color:{icon_color};">{icon}</div>
                    <div style="font-size:1.1rem; font-weight:600; color:{theme['primary_color']}; margin-bottom:0.2rem;">
                        Invoice #{inv['invoice_number']}
                    </div>
                    <div style="color:{theme['secondary_color']}; font-size:0.98rem; margin-bottom:0.2rem;">
                        {inv['supplier']}
                    </div>
                    <div style="color:{theme['border_color']}; font-size:0.95rem;">
                        Date: {inv['invoice_date']}
                    </div>
                    <div style="color:{theme['primary_color']}; font-size:1.05rem; margin-top:0.3rem;">
                        <b>Total: £{inv['total_value']:.2f}</b>
                    </div>
                </div>
                """
                col.markdown(card_html, unsafe_allow_html=True)

    render_divider()

    # --- Supplier Scorecard ---
    if analytics_df.empty:
        st.markdown(
            f"<div style='color:{theme['border_color']}; font-size:1.1rem; margin:1.5rem 0;'>No supplier data yet.</div>",
            unsafe_allow_html=True
        )
        st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)
        return

    st.markdown(f"<div style='font-weight:600; color:{theme['primary_color']}; margin-bottom:0.5rem;'>Supplier Scorecard</div>", unsafe_allow_html=True)
    st.dataframe(
        analytics_df.rename(columns={
            'item': 'Supplier (Item)',
            'total_invoices': 'Total Invoices',
            'mismatch_rate': 'Mismatch Rate (%)',
            'price_volatility': 'Price Volatility (Std Dev)'
        }),
        use_container_width=True,
        height=350
    )

    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Export as CSV", key="export_csv"):
            csv = analytics_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="supplier_scorecard.csv",
                mime="text/csv",
                key="download_csv_btn"
            )
            st.markdown(f"<div style='background:{theme['secondary_color']}; color:white; padding:0.5rem 1rem; border-radius:0.5rem; margin:0.5rem 0;'>Export ready. Click 'Download CSV' above.</div>", unsafe_allow_html=True)
    with col2:
        if st.button("Export as Excel", key="export_excel"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:  # type: ignore
                analytics_df.to_excel(writer, index=False, sheet_name='Supplier Scorecard')
            output.seek(0)
            excel_data = output.read()
            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name="supplier_scorecard.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel_btn"
            )
            st.markdown(f"<div style='background:{theme['secondary_color']}; color:white; padding:0.5rem 1rem; border-radius:0.5rem; margin:0.5rem 0;'>Export ready. Click 'Download Excel' above.</div>", unsafe_allow_html=True)
    render_divider() 