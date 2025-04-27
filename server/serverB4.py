from flask import Flask, jsonify, request, redirect
import threading
import random

app = Flask(__name__)

peers = {}
peer_lock = threading.Lock()
SECRET_TOKEN = "MY_CLIENT_SECRET"
MAX_PEER_LOAD = 5

@app.route('/register', methods=['POST'])
def register_peer():
    data = request.json
    token = request.headers.get('X-Client-Token')

    if token != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    with peer_lock:
        peers[data['peer_id']] = {
            'address': data['address'],
            'load': 0,
            'files': data.get('files', [])
        }
        print(f"Peer {data['peer_id']} registered with address {data['address']}")
        return jsonify({"status": "registered"})

@app.route('/get-peer', methods=['GET'])
def get_peer():
    available_peers = []
    with peer_lock:
        for peer_id, peer_data in peers.items():
            if peer_data['load'] < MAX_PEER_LOAD:
                available_peers.append(peer_id)

        if not available_peers:
            return jsonify({"error": "No peers available"}), 503

        chosen_peer_id = random.choice(available_peers)
        peers[chosen_peer_id]['load'] += 1
        peer_address = peers[chosen_peer_id]['address']
        print(f"Redirecting to peer {chosen_peer_id} at {peer_address}")
        return jsonify({"peer_address": peer_address})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    response = requests.get(f"{SERVER_URL}/peers")
    response.raise_for_status()
    peers = response.json().get('peers', [])
    other_peers = [peer for peer in peers if peer['id'] != PEER_ID]

    if other_peers:
        chosen_peer = random.choice(other_peers)
        peer_address = chosen_peer['address']
        return redirect(peer_address, code=302)
    else:
        return "No peers available", 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
