import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DATABASE_PATH = 'data/owlin.db'

def get_db_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def calculate_supplier_metrics(supplier_id: str):
    """Calculates all metrics for a given supplier."""
    conn = get_db_connection()
    metrics = {
        "supplier_name": "Unknown Supplier",
        "total_invoices": 0,
        "flagged_issues": 0,
        "avg_delay_days": 0.0,
        "price_volatility": 0.0, # As Coefficient of Variation percentage
        "recent_issues": pd.DataFrame(),
        "all_issues": pd.DataFrame()
    }

    try:
        # 1. Get Supplier Name
        supplier_row = conn.execute("SELECT name FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
        if supplier_row:
            metrics["supplier_name"] = supplier_row["name"]
        else:
            return None # Supplier not found

        # 2. Total Invoices
        total_invoices_row = conn.execute("SELECT COUNT(DISTINCT id) AS count FROM invoices WHERE supplier_id = ?", (supplier_id,)).fetchone()
        metrics["total_invoices"] = total_invoices_row["count"]

        # 3. Flagged Issues
        flagged_issues_row = conn.execute("""
            SELECT COUNT(fi.id) AS count
            FROM flagged_issues fi
            JOIN invoices i ON fi.invoice_id = i.id
            WHERE i.supplier_id = ?
        """, (supplier_id,)).fetchone()
        metrics["flagged_issues"] = flagged_issues_row["count"]

        # 4. Avg Delay in Days
        # Calculate difference between delivery_date and invoice_date
        avg_delay_row = conn.execute("""
            SELECT AVG(JULIANDAY(dn.delivery_date) - JULIANDAY(i.invoice_date)) AS avg_delay
            FROM invoices i
            JOIN delivery_notes dn ON i.id = dn.invoice_id
            WHERE i.supplier_id = ? AND dn.delivery_date IS NOT NULL AND i.invoice_date IS NOT NULL
        """, (supplier_id,)).fetchone()
        metrics["avg_delay_days"] = round(avg_delay_row["avg_delay"], 2) if avg_delay_row["avg_delay"] is not None else 0.0

        # 5. Price Volatility (Coefficient of Variation)
        unit_prices_rows = conn.execute("""
            SELECT li.unit_price
            FROM line_items li
            JOIN invoices i ON li.invoice_id = i.id
            WHERE i.supplier_id = ? AND li.unit_price IS NOT NULL
        """, (supplier_id,)).fetchall()

        prices = pd.Series([row["unit_price"] for row in unit_prices_rows])
        if len(prices) > 1:
            mean_price = prices.mean()
            std_dev_price = prices.std()
            if mean_price != 0:
                metrics["price_volatility"] = round((std_dev_price / mean_price) * 100, 2)
            else:
                metrics["price_volatility"] = 0.0 # Avoid division by zero if mean is 0
        else:
            metrics["price_volatility"] = 0.0 # Not enough data for volatility

        # 6. Recent Flagged Issues (last 5)
        recent_issues_data = conn.execute("""
            SELECT
                fi.created_at,
                fi.invoice_id,
                fi.issue_type,
                fi.description
            FROM flagged_issues fi
            JOIN invoices i ON fi.invoice_id = i.id
            WHERE i.supplier_id = ?
            ORDER BY fi.created_at DESC
            LIMIT 5
        """, (supplier_id,)).fetchall()
        
        recent_issues_df = pd.DataFrame.from_records(recent_issues_data, columns=["Date", "Invoice ID", "Issue Type", "Description"])
        if not recent_issues_df.empty:
            recent_issues_df["Date"] = pd.to_datetime(recent_issues_df["Date"]).dt.strftime('%d/%m/%Y')
        metrics["recent_issues"] = recent_issues_df

        # 7. All Flagged Issues for CSV download
        all_issues_data = conn.execute("""
            SELECT
                fi.created_at AS Date,
                fi.invoice_id AS "Invoice ID",
                fi.issue_type AS "Issue Type",
                fi.description AS Description
            FROM flagged_issues fi
            JOIN invoices i ON fi.invoice_id = i.id
            WHERE i.supplier_id = ?
            ORDER BY fi.created_at DESC
        """, (supplier_id,)).fetchall()
        
        all_issues_df = pd.DataFrame(all_issues_data)
        if not all_issues_df.empty:
            all_issues_df["Date"] = pd.to_datetime(all_issues_df["Date"]).dt.strftime('%Y-%m-%d %H:%M:%S')
        metrics["all_issues"] = all_issues_df

    except sqlite3.Error as e:
        st.error(f"A database error occurred: {e}")
        return None
    finally:
        conn.close()

    return metrics

def get_score_badge(metrics: dict):
    """Determines the supplier score badge based on calculated metrics."""
    if metrics["total_invoices"] == 0:
        return "⚪ Unknown", "No invoice data available for scoring."

    issue_rate = (metrics["flagged_issues"] / metrics["total_invoices"]) * 100 if metrics["total_invoices"] > 0 else 0
    delay = metrics["avg_delay_days"]
    volatility = metrics["price_volatility"]

    # Score based on thresholds:
    # 🟢 Reliable: issue rate <10%, delay <2 days, volatility <5%
    if issue_rate < 10 and delay < 2 and volatility < 5:
        return "🟢 Reliable", "This supplier consistently performs well."
    # 🟡 Moderate: issue rate 10–30%, delay 2–4 days, volatility 5–15%
    elif (10 <= issue_rate < 30) or \
         (2 <= delay < 4) or \
         (5 <= volatility < 15):
        return "🟡 Moderate", "This supplier has some areas for improvement."
    # 🔴 Unstable: issue rate >30%, delay >4 days, volatility >15%
    else:
        return "🔴 Unstable", "This supplier frequently experiences issues or significant price fluctuations."

def render_supplier_scorecard(supplier_id: str):
    """
    Renders a complete Streamlit scorecard for a given supplier,
    displaying reliability, pricing, and issue history.
    """
    if not supplier_id:
        st.warning("Please provide a supplier ID to display the scorecard.")
        return

    metrics = calculate_supplier_metrics(supplier_id)

    if metrics is None:
        st.error(f"Supplier with ID '{supplier_id}' not found in the database.")
        return
    
    supplier_name = metrics["supplier_name"]
    total_invoices = metrics["total_invoices"]
    flagged_issues = metrics["flagged_issues"]
    avg_delay_days = metrics["avg_delay_days"]
    price_volatility = metrics["price_volatility"]
    recent_issues_df = metrics["recent_issues"]
    all_issues_df = metrics["all_issues"]

    score_emoji, score_label = get_score_badge(metrics)

    # Custom CSS for the container and metric display
    st.markdown("""
        <style>
        .scorecard-container {
            background-color: white;
            padding: 20px 30px; /* Increased horizontal padding slightly */
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            margin-bottom: 30px;
            border: 1px solid #e0e0e0;
        }
        .metric-label {
            font-size: 0.85em; /* Slightly smaller for 'small' feel */
            color: #6a6a6a; /* Lighter gray */
            margin-bottom: 4px;
            font-weight: 500; /* Medium weight for labels */
        }
        .metric-value {
            font-size: 1.8em; /* Larger for impact */
            font-weight: bold;
            color: #2c3e50; /* Darker, professional color */
            line-height: 1.2;
        }
        .st-emotion-cache-1wivf4j { /* Target Streamlit column gap */
            gap: 25px; /* Increase gap between columns */
        }
        </style>
    """, unsafe_allow_html=True)

    # Main scorecard container
    with st.container():
        st.markdown('<div class="scorecard-container">', unsafe_allow_html=True)

        # 1. Supplier Name Header
        st.markdown(f"### **{supplier_name}**")
        st.markdown("---") # Simple separator for visual structure

        # 2. Metric Summary Row (4 columns)
        st.markdown("<br>", unsafe_allow_html=True) # Add space before metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown("<div class='metric-label'>Total Invoices (📄)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{total_invoices}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='metric-label'>Flagged Issues (⚠️)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{flagged_issues}</div>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div class='metric-label'>Avg Delay in Days (⏱)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{avg_delay_days:.1f}</div>", unsafe_allow_html=True)
        with col4:
            st.markdown("<div class='metric-label'>Price Volatility (📈)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{price_volatility:.1f}%</div>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True) # Add more space after metrics

        # 3. Score Badge
        st.markdown(f"**Supplier Status:** {score_emoji} {score_label}")
        st.markdown("<br>", unsafe_allow_html=True) # Add some space

        # 4. Timeline of Recent Flagged Issues
        st.subheader("Recent Flagged Issues")
        if not recent_issues_df.empty:
            # Display using st.dataframe for better formatting and interactivity
            st.dataframe(
                recent_issues_df,
                hide_index=True,
                column_config={
                    "Date": st.column_config.Column("Date", width="small"),
                    "Invoice ID": st.column_config.Column("Invoice ID", width="small"),
                    "Issue Type": st.column_config.Column("Issue Type", width="medium"),
                    "Description": st.column_config.Column("Description", width="large")
                }
            )
        else:
            st.info("No recent flagged issues found for this supplier.")

        st.markdown("<br>", unsafe_allow_html=True) # Add some space

        # 5. Optional: CSV download of all flagged issues
        if not all_issues_df.empty:
            csv_data = all_issues_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download All Issues (CSV)",
                data=csv_data,
                file_name=f"{supplier_name.replace(' ', '_').lower()}_issues.csv",
                mime="text/csv",
                help="Download a CSV file containing all flagged issues for this supplier."
            )
        else:
            st.info("No flagged issues to download for this supplier.")

        st.markdown('</div>', unsafe_allow_html=True) # Close the scorecard-container div 