import subprocess
import sys
import time
import webbrowser
import os

def main():
    print("Starting OSM Viewer Application...")
    
    # Kill any existing Streamlit processes (Windows)
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'streamlit.exe'], 
                      capture_output=True)
    except Exception as e:
        print(f"Note: Could not kill existing processes: {e}")
    
    # Start Streamlit
    port = 8506
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "main.py",
        "--server.port",
        str(port),
        "--server.address",
        "127.0.0.1",
        "--server.headless",
        "false",
        "--browser.serverAddress",
        "localhost"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Start the process
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Wait a bit and then open the browser
    time.sleep(3)
    url = f"http://localhost:{port}"
    print(f"Opening browser at: {url}")
    webbrowser.open(url)
    
    # Monitor the process output
    while True:
        output = process.stdout.readline()
        if output:
            print(output.strip())
        error = process.stderr.readline()
        if error:
            print(f"Error: {error.strip()}", file=sys.stderr)
        
        # Check if process has finished
        if process.poll() is not None:
            break
    
    # Get any remaining output
    stdout, stderr = process.communicate()
    if stdout:
        print(stdout)
    if stderr:
        print(f"Error: {stderr}", file=sys.stderr)
    
    return process.returncode

if __name__ == "__main__":
    sys.exit(main())
