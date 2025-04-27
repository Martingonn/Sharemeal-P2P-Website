# Client Code (client.py)
import requests
import time
from flask import Flask, send_from_directory
import os

SERVER_URL = "http://localhost:5000"
PEER_ID = "peer_" + str(random.randint(1000,9999))
FILES_DIR = "website_files"

app = Flask(__name__)

def register_with_server():
    files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
    
    response = requests.post(f"{SERVER_URL}/register", json={
        "peer_id": PEER_ID,
        "address": f"http://localhost:{os.getenv('PORT', 5001)}",
        "files": files
    })
    
    if response.status_code == 200:
        print("Successfully registered with server")
    else:
        print("Registration failed")

def retrieve_website_files():
    response = requests.post(f"{SERVER_URL}/assign-workload")
    if response.status_code == 200:
        data = response.json()
        print(f"Assigned to peer: {data['assigned_peer']}")
        # Implement actual file transfer logic here
    else:
        print("Failed to retrieve workload assignment")

@app.route('/files/<path:filename>')
def serve_file(filename):
    return send_from_directory(FILES_DIR, filename)

if __name__ == '__main__':
    register_with_server()
    app.run(host='0.0.0.0', port=os.getenv('PORT', 5001))
