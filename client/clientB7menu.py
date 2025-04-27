import requests
import time
from flask import Flask, send_from_directory, abort, request, jsonify
import os
import random
import shutil
import multiprocessing
import signal
import sys

SERVER_URL = "http://localhost:5000"
PEER_ID = "peer_" + str(random.randint(1000, 9999))
FILES_DIR = "website_files"
SECRET_TOKEN = "MY_CLIENT_SECRET"

app = Flask(__name__)

# --- Your existing functions here (unchanged) ---

def find_peers_for_package(package_name):
    try:
        response = requests.get(f"{SERVER_URL}/find_peers_for_file/{package_name}")
        response.raise_for_status()
        data = response.json()
        return data['peers']
    except requests.exceptions.RequestException as e:
        print(f"Error finding peers for package {package_name}: {e}")
        return None


def download_package(peer_address, package_name, destination_path):
    try:
        download_url = f"{peer_address}/files/{package_name}"
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Successfully downloaded {package_name} from {peer_address} to {destination_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {package_name} from {peer_address}: {e}")
        return False


def register_with_server(port):
    files = [f for f in os.listdir(FILES_DIR) if os.path.isfile(os.path.join(FILES_DIR, f))]
    headers = {'X-Client-Token': SECRET_TOKEN}
    response = requests.post(f"{SERVER_URL}/register", headers=headers, json={
        "peer_id": PEER_ID,
        "address": f"http://localhost:{port}",
        "files": files
    })
    if response.status_code == 200:
        print(f"Successfully registered with server on port {port}")
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

        # Replace server files
        for file in os.listdir(FILES_DIR):
            if file.endswith(".py"):
                os.remove(os.path.join(FILES_DIR, file))
        shutil.copy(file_path, FILES_DIR)

        # Restart
        print("Restarting server...")
        os.execv(__file__, ['python'] + [__file__])

        return jsonify({"status": "Update successful"})

    except requests.exceptions.RequestException as e:
        print(f"Error during update: {e}")
        return jsonify({"error": str(e)}), 500


def run_flask_server(port):
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)

    register_with_server(port)
    get_files_from_peers()

    app.run(host='0.0.0.0', port=port)


# --- Menu and server process management ---

server_processes = {}  # port -> multiprocessing.Process


def start_server(port):
    if port in server_processes and server_processes[port].is_alive():
        print(f"Server already running on port {port}")
        return
    p = multiprocessing.Process(target=run_flask_server, args=(port,), daemon=True)
    p.start()
    server_processes[port] = p
    time.sleep(1)  # Give server time to start
    if p.is_alive():
        print(f"Server started on port {port}")
    else:
        print(f"Failed to start server on port {port}")


def stop_server(port):
    p = server_processes.get(port)
    if p and p.is_alive():
        p.terminate()
        p.join()
        print(f"Server stopped on port {port}")
        del server_processes[port]
    else:
        print(f"No running server found on port {port}")


def list_servers():
    if not server_processes:
        print("No servers running.")
    else:
        print("Running servers:")
        for port, proc in server_processes.items():
            status = "alive" if proc.is_alive() else "stopped"
            print(f" - Port {port}: {status}")


def menu():
    while True:
        print("\n=== Peer Server Menu ===")
        print("1. Start server on port")
        print("2. Stop server on port")
        print("3. List running servers")
        print("4. Download package from peers")
        print("5. Exit")
        choice = input("Choose an option: ").strip()

        if choice == '1':
            port_str = input("Enter port to start server on (default 5001): ").strip()
            port = int(port_str) if port_str.isdigit() else 5001
            start_server(port)

        elif choice == '2':
            port_str = input("Enter port to stop server on: ").strip()
            if port_str.isdigit():
                port = int(port_str)
                stop_server(port)
            else:
                print("Invalid port number.")

        elif choice == '3':
            list_servers()

        elif choice == '4':
            package_name = input("Enter package name to download: ").strip()
            if not package_name:
                print("Package name cannot be empty.")
                continue

            peers = find_peers_for_package(package_name)
            if peers:
                print(f"Found peers with {package_name}: {peers}")
                selected_peer = peers[0]  # Select the first peer
                peer_address = selected_peer["address"]
                peer_id = selected_peer["peer_id"]
                print(f"Downloading {package_name} from peer {peer_id} at {peer_address}")
                destination_path = f"downloaded_{package_name}"
                if download_package(peer_address, package_name, destination_path):
                    print(f"Download complete: {destination_path}")
                else:
                    print("Download failed.")
            else:
                print(f"No peers found for {package_name}")

        elif choice == '5':
            print("Exiting...")
            # Stop all servers before exiting
            for port in list(server_processes.keys()):
                stop_server(port)
            break

        else:
            print("Invalid choice. Please select a valid option.")


if __name__ == '__main__':
    menu()
