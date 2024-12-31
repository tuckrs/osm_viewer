@echo on
echo Starting OSM Viewer Application...

:: Check Python installation
python --version
if errorlevel 1 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)

:: Verify Streamlit installation
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Installing required packages...
    pip install -r requirements.txt
)

:: Kill any existing Streamlit processes
taskkill /F /IM "streamlit.exe" 2>nul
taskkill /F /FI "WINDOWTITLE eq Streamlit" 2>nul

:: Start Streamlit with specific configuration
echo Starting Streamlit server...
start "Streamlit" /B python -m streamlit run main.py --server.port 8505 --server.address 127.0.0.1 --server.headless false --browser.serverAddress localhost

:: Wait a few seconds
timeout /t 5

:: Try to open the browser
start http://localhost:8505

echo If the application doesn't open automatically, please try accessing it at:
echo http://localhost:8505
