from flask import Flask, jsonify, request, render_template, redirect, url_for, send_from_directory
import threading
import random
import os
import shutil
import requests


app = Flask(__name__)


peers = {}
peer_lock = threading.Lock()
SECRET_TOKEN = "MY_CLIENT_SECRET"
ADMIN_PASSWORD = "admin_password" #CHANGE THIS
UPDATE_FOLDER = "server_update"
BANNED_PEERS = set()


# Ensure update folder exists
if not os.path.exists(UPDATE_FOLDER):
    os.makedirs(UPDATE_FOLDER)


def get_peer_list():
    peer_list = []
    for pid, p in peers.items():
        peer_list.append({
            "id": pid,
            "address": p['address'],
            "files": p['files'],
            "banned": pid in BANNED_PEERS
        })
    return peer_list


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error='Invalid password')
    return render_template('login.html')


@app.route('/admin')
def admin():
    peer_list = get_peer_list()
    return render_template('admin.html', peers=peer_list)


@app.route('/ban_peer/<peer_address>')
def ban_peer(peer_address):
    with peer_lock:
        for peer_id, peer_data in peers.items():
            if peer_data['address'] == peer_address:
                BANNED_PEERS.add(peer_id)
                print(f"Peer with address {peer_address} banned")
                break
    return redirect(url_for('admin'))


@app.route('/unban_peer/<peer_address>')
def unban_peer(peer_address):
    with peer_lock:
        for peer_id, peer_data in peers.items():
            if peer_data['address'] == peer_address:
                BANNED_PEERS.discard(peer_id)
                print(f"Peer with address {peer_address} unbanned")
                break
    return redirect(url_for('admin'))


@app.route('/disconnect_peer/<peer_address>')
def disconnect_peer(peer_address):
    with peer_lock:
        peer_to_remove = None
        for peer_id, peer_data in peers.items():
            if peer_data['address'] == peer_address:
                peer_to_remove = peer_id
                break
        if peer_to_remove:
            del peers[peer_to_remove]
            print(f"Peer with address {peer_address} disconnected")
    return redirect(url_for('admin'))


@app.route('/update', methods=['POST'])
def update():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded file to the update folder
    file_path = os.path.join(UPDATE_FOLDER, file.filename)
    file.save(file_path)
    print(f"Update file saved to {file_path}")

    # Notify peers to update
    for peer_id, peer_data in peers.items():
        requests.post(f"{peer_data['address']}/update_server", json={"file_url": f"http://{request.host}/get_update/{file.filename}"})

    return jsonify({"status": "Update sent to peers"})


@app.route('/get_update/<filename>')
def get_update(filename):
    return send_from_directory(UPDATE_FOLDER, filename)


@app.route('/register', methods=['POST'])
def register_peer():
    data = request.json
    token = request.headers.get('X-Client-Token')

    if token != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    with peer_lock:
        if data['peer_id'] in BANNED_PEERS:
            return jsonify({"error": "Peer is banned"}), 403
        peers[data['peer_id']] = {
            'address': data['address'],
            'files': data.get('files', [])
        }
        print(f"Peer {data['peer_id']} registered with address {data['address']}")
        return jsonify({"status": "registered"})


@app.route('/peers', methods=['GET'])
def list_peers():
    with peer_lock:
        peer_list = get_peer_list()
        return jsonify({"peers": peer_list})


@app.route('/peer_list') # Add this route
def peer_list():
    peer_list = get_peer_list()
    return render_template('peer_list.html', peers=peer_list)


@app.route('/find_peers_for_file/<filename>')
def find_peers_for_file(filename):
    with peer_lock:
        available_peers = []
        for peer_id, peer_data in peers.items():
            if filename in peer_data['files']:
                available_peers.append(peer_data['address'])
        return jsonify({"peers": available_peers})


@app.route('/update_server', methods=['POST'])
def update_server():
    data = request.json
    file_url = data['file_url']
    print(f"Received update request. Downloading from {file_url}")

    try:
        response = requests.get(file_url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        file_name = os.path.basename(file_url)
        file_path = os.path.join(UPDATE_FOLDER, file_name)

        with open(file_path, 'wb') as f:
            f.write(response.content)

        print(f"Downloaded update to {file_path}")

        # Replace the peer's own .py file
        script_name = os.path.basename(__file__)  # Get the name of this script
        script_path = os.path.join(UPDATE_FOLDER, script_name)
        if os.path.exists(script_path):
            # Create a backup
            backup_path = script_path + ".bak"
            shutil.move(script_path, backup_path)
            try:
                shutil.copy(file_path, script_path)
                print(f"Successfully updated {script_name}")
            except Exception as e:
                print(f"Error replacing {script_name}: {e}")
                # Restore from backup if copy failed
                shutil.move(backup_path, script_path)
            return jsonify({"status": "Update successful, restart manually."})  # Suggest manual restart
        else:
            print(f"Script {script_name} not found in {UPDATE_FOLDER}")
            return jsonify({"error": "Script not found"}), 404

    except requests.exceptions.RequestException as e:
        print(f"Error during update: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
