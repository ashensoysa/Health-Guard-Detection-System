import threading
import webbrowser
from app import app  # Make sure your Flask instance is in app.py

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == "__main__":
    # Start browser after a short delay
    threading.Timer(1.5, open_browser).start()
    app.run(debug=True)
