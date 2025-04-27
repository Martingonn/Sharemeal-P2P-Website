import requests
import time
from flask import Flask, send_from_directory, abort
import os
import random

SERVER_URL = "http://your_server_ip:5000"  # Replace with your server's public IP or domain
PEER_ID = "peer_" + str(random.randint(1000, 9999))
FILES_DIR = "website_files"
SECRET_TOKEN = "MY_CLIENT_SECRET"  # Define the secret token

app = Flask(__name__)

def register_with_server():
    files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
    headers = {'X-Client-Token': SECRET_TOKEN}  # Set the secret token in header
    response = requests.post(f"{SERVER_URL}/register", headers=headers, json={
        "peer_id": PEER_ID,
        "address": f"http://localhost:{os.getenv('PORT', 5001)}",  # Keep localhost for client's own serving
        "files": files
    })
    if response.status_code == 200:
        print("Successfully registered with server")
    else:
        print(f"Registration failed: {response.status_code} - {response.text}")

def get_files_from_peers():
    try:
        response = requests.get(f"{SERVER_URL}/peers")
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        peers = response.json().get('peers', [])

        # Exclude self from the list of peers
        other_peers = [peer for peer in peers if peer['id'] != PEER_ID]

        if other_peers:
            # Select a random peer
            chosen_peer = random.choice(other_peers)
            peer_address = chosen_peer['address']
            peer_files = chosen_peer['files']
            print(f"Attempting to fetch files from peer: {peer_address}")

            # Download files from the selected peer
            for file in peer_files:
                try:
                    file_url = f"{peer_address}/files/{file}"
                    file_response = requests.get(file_url)
                    file_response.raise_for_status()
                    file_path = os.path.join(FILES_DIR, file)
                    with open(file_path, 'wb') as f:
                        f.write(file_response.content)
                    print(f"Downloaded {file} from {peer_address}")
                except requests.exceptions.RequestException as e:
                    print(f"Error downloading {file} from {peer_address}: {e}")
        else:
            print("No other peers found. Serving local files.")
    except requests.exceptions.RequestException as e:
        print(f"Error getting peer list: {e}")

@app.route('/files/<filename>')
def serve_file(filename):
    file_path = os.path.join(FILES_DIR, filename)
    if os.path.isfile(file_path):
        return send_from_directory(FILES_DIR, filename)
    else:
        abort(404)

if __name__ == '__main__':
    # Create the website_files directory if it doesn't exist
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)

    register_with_server()
    get_files_from_peers()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5001)))
