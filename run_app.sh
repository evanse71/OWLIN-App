#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run Streamlit with the updated main.py that handles its own path setup
streamlit run app/main.py --server.headless true --server.port 8502 --server.runOnSave true 