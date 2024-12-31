@echo off
cd /d %~dp0
python -m streamlit run main.py --server.port 8501 --server.address localhost
