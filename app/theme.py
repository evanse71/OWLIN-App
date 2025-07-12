import streamlit as st

def get_theme():
    """Return a dictionary of theme values for the Owlin app UI."""
    return {
        'primary_color': '#2C3E50',      # Desaturated navy
        'secondary_color': '#8DAA91',    # Sage green
        'alert_color': '#FFB347',        # Soft orange for warnings
        'critical_color': '#E74C3C',     # Red for critical errors only
        'background': '#F4F6F8',         # Soft gray background
        'border_color': '#B0B8C1',       # Soft gray border
        'spacing': '1rem',               # 16px
        'border_radius': '0.5rem',       # 8px
        'font': 'Inter, Work Sans, sans-serif',
    }


def render_header(text):
    """Render a styled header using the Owlin theme."""
    theme = get_theme()
    st.markdown(f"""
        <h2 style="
            font-family: {theme['font']};
            color: {theme['primary_color']};
            background: {theme['background']};
            padding: 0.5rem 0;
            margin-bottom: 0.5rem;
            border-bottom: 2px solid {theme['secondary_color']};
        ">{text}</h2>
    """, unsafe_allow_html=True)


def render_divider():
    """Render a soft, styled divider using the Owlin theme."""
    theme = get_theme()
    st.markdown(f"""
        <hr style="
            border: none;
            border-top: 1.5px solid {theme['border_color']};
            margin: 1.5rem 0;
        "/>
    """, unsafe_allow_html=True) 