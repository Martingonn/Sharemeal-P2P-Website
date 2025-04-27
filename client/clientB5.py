import requests
import time
from flask import Flask, send_from_directory, abort, request
import os
import random
import subprocess

SERVER_URL = "http://localhost:5000"
PEER_ID = "peer_" + str(random.randint(1000, 9999))
FILES_DIR = "website_files"
SECRET_TOKEN = "MY_CLIENT_SECRET"

app = Flask(__name__)

def register_with_server():
    files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
    headers = {'X-Client-Token': SECRET_TOKEN}
    response = requests.post(f"{SERVER_URL}/register", headers=headers, json={
        "peer_id": PEER_ID,
        "address": f"http://localhost:{os.getenv('PORT', 5001)}",
        "files": files
    })
    if response.status_code == 200:
        print("Successfully registered with server")
    else:
        print(f"Registration failed: {response.status_code} - {response.text}")

def get_files_from_peers():
    try:
        response = requests.get(f"{SERVER_URL}/peers")
        response.raise_for_status()
        peers = response.json().get('peers', [])
        other_peers = [peer for peer in peers if peer['id'] != PEER_ID]

        if other_peers:
            chosen_peer = random.choice(other_peers)
            peer_address = chosen_peer['address']
            peer_files = chosen_peer['files']
            print(f"Attempting to fetch files from peer: {peer_address}")

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

@app.route('/update_server', methods=['POST'])
def update_server():
    data = request.json
    file_url = data['file_url']
    print(f"Received update request. Downloading from {file_url}")

    try:
        response = requests.get(file_url)
        response.raise_for_status()
        file_name = os.path.basename(file_url)
        file_path = os.path.join(FILES_DIR, file_name)

        with open(file_path, 'wb') as f:
            f.write(response.content)

        print(f"Downloaded update to {file_path}")

        #Replace server files
        for file in os.listdir(FILES_DIR):
            if file.endswith(".py"):
                os.remove(os.path.join(FILES_DIR,file))
        shutil.copy(file_path,FILES_DIR)

        #Restart
        print("Restarting server...")
        os.execv(__file__, ['python'] + [__file__])

        return jsonify({"status": "Update successful"})

    except requests.exceptions.RequestException as e:
        print(f"Error during update: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)

    register_with_server()
    get_files_from_peers()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5001)))
