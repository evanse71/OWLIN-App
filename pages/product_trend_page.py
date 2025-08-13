import streamlit as st
import streamlit.components.v1 as components
import json

def load_forecast_data(product_name):
    # Mocked data for demonstration
    if product_name == "Carrots":
        return {
            "historic": [
                {"x": "2024-08-01", "y": 1.20},
                {"x": "2024-09-01", "y": 1.35},
                {"x": "2024-10-01", "y": 1.50},
                {"x": "2024-11-01", "y": 1.65},
                {"x": "2024-12-01", "y": 1.80},
            ],
            "forecast": [
                {"x": "2025-01-01", "y": 1.90, "upper": 2.05, "lower": 1.75},
                {"x": "2025-02-01", "y": 2.00, "upper": 2.20, "lower": 1.80},
                {"x": "2025-03-01", "y": 2.10, "upper": 2.35, "lower": 1.85},
            ],
            "confidence": "medium",
            "volatility": "moderate",
            "data_points": 8,
        }
    elif product_name == "Milk":
        return {
            "historic": [
                {"x": "2024-08-01", "y": 0.95},
                {"x": "2024-09-01", "y": 1.05},
                {"x": "2024-10-01", "y": 1.10},
                {"x": "2024-11-01", "y": 1.15},
                {"x": "2024-12-01", "y": 1.20},
            ],
            "forecast": [
                {"x": "2025-01-01", "y": 1.22, "upper": 1.30, "lower": 1.15},
                {"x": "2025-02-01", "y": 1.25, "upper": 1.35, "lower": 1.18},
                {"x": "2025-03-01", "y": 1.28, "upper": 1.40, "lower": 1.20},
            ],
            "confidence": "high",
            "volatility": "low",
            "data_points": 8,
        }
    else:
        return {
            "historic": [
                {"x": "2024-08-01", "y": 2.10},
                {"x": "2024-09-01", "y": 2.25},
                {"x": "2024-10-01", "y": 2.40},
                {"x": "2024-11-01", "y": 2.55},
                {"x": "2024-12-01", "y": 2.70},
            ],
            "forecast": [
                {"x": "2025-01-01", "y": 2.80, "upper": 3.00, "lower": 2.60},
                {"x": "2025-02-01", "y": 2.90, "upper": 3.10, "lower": 2.70},
                {"x": "2025-03-01", "y": 3.00, "upper": 3.20, "lower": 2.80},
            ],
            "confidence": "low",
            "volatility": "high",
            "data_points": 8,
        }

PRODUCTS = ["Carrots", "Milk", "Pork Shoulder"]

st.set_page_config(page_title="Product Price Trends", layout="wide")
st.markdown("<style>div[data-testid='stSidebar'] { min-width: 270px; max-width: 320px; } .owlin-header { font-size: 2.1rem; font-weight: 700; margin-bottom: 0.5rem; } .owlin-subtle { color: #6b7280; font-size: 1.1rem; } .owlin-divider { border-top: 1px solid #e5e7eb; margin: 1.5rem 0 1.5rem 0; } </style>", unsafe_allow_html=True)
st.markdown("<div class='owlin-header'>📈 Product Price Trends</div>", unsafe_allow_html=True)
st.markdown("<div class='owlin-subtle'>Track historical unit price changes for any product</div>", unsafe_allow_html=True)
st.markdown("<div class='owlin-divider'></div>", unsafe_allow_html=True)

product = st.selectbox("Select Product", PRODUCTS, index=0)
data = load_forecast_data(product)

# Prepare data for UniversalTrendGraph
chart_props = {
    "historic": data["historic"],
    "forecast": data["forecast"],
    "xLabel": "Date",
    "yLabel": "Price (£)",
    "lineLabel": "Unit Price",
    "color": "#059669",
    "height": 380,
    "fadeIn": True,
    "theme": "light",
    "showDots": False,
    "confidence": data["confidence"],
    "volatility": data["volatility"],
    "data_points": data["data_points"],
}

chart_html = f"""
<div id='owlin-trend-graph' style='width: 700px; height: 380px; margin: 0 auto;'></div>
<script>
window.renderUniversalTrendGraph && window.renderUniversalTrendGraph(
    document.getElementById('owlin-trend-graph'),
    {json.dumps(chart_props)}
);
</script>
"""

st.markdown("<div style='display: flex; justify-content: center; align-items: center; padding: 2rem 0;'>", unsafe_allow_html=True)
components.html(chart_html, height=420, width=740)
st.markdown("</div>", unsafe_allow_html=True) 