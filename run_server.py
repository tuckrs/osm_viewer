import subprocess
import sys
import webbrowser
import time

def main():
    port = 8545
    
    # Kill any existing Python processes (optional, be careful with this)
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                      capture_output=True)
    except Exception:
        pass
    
    # Start the Streamlit server
    cmd = [
        sys.executable,
        '-m',
        'streamlit',
        'run',
        'main.py',
        '--server.address=0.0.0.0',
        f'--server.port={port}',
        '--server.headless=false',
        '--browser.serverAddress=localhost'
    ]
    
    print(f"Starting server on port {port}...")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait a bit for the server to start
    time.sleep(5)
    
    # Open the browser
    url = f'http://localhost:{port}'
    print(f"Opening {url}")
    webbrowser.open(url)
    
    # Keep the script running and monitor the process
    while True:
        if process.poll() is not None:
            print("Server process ended")
            break
        time.sleep(1)

if __name__ == '__main__':
    main()
