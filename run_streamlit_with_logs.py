import subprocess
import socket
import time

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def run_streamlit_app():
    try:
        process = subprocess.Popen(
            ["streamlit", "run", "app/main.py", "--server.port", "8501", "--logger.level", "debug"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait a moment to let server start
        time.sleep(5)

        # Check if port is now in use
        if is_port_in_use(8501):
            print("Streamlit server is running and listening on port 8501.")
        else:
            print("Streamlit server did NOT start or is not listening on port 8501.")

        # Print live logs
        while True:
            output = process.stdout.readline() if process.stdout else ''
            if output:
                print(output.strip())
            err = process.stderr.readline() if process.stderr else ''
            if err:
                print("ERROR:", err.strip())
            if output == '' and err == '' and process.poll() is not None:
                break

        return_code = process.poll()
        if return_code != 0:
            print(f"Streamlit exited with code {return_code}")

    except Exception as e:
        print(f"Failed to start Streamlit app: {e}")

if __name__ == "__main__":
    port = 8501
    if is_port_in_use(port):
        print(f"Port {port} is already in use. Please free this port or change the Streamlit port.")
    else:
        run_streamlit_app() 