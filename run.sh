#!/bin/bash

# Background mein FastAPI server chalu karein
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Foreground mein Streamlit app chalu karein
streamlit run app/POC_frontend.py --server.port 8501 --server.address 0.0.0.0
