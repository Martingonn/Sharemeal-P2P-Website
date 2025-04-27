# Server Code (server.py)
from flask import Flask, jsonify, request
import threading
import random

app = Flask(__name__)
peers = {}
peer_lock = threading.Lock()
WORKLOAD_THRESHOLD = 5

@app.route('/register', methods=['POST'])
def register_peer():
    data = request.json
    with peer_lock:
        peers[data['peer_id']] = {
            'address': data['address'],
            'workload': 0,
            'files': data.get('files', [])
        }
    return jsonify({"status": "registered"})

@app.route('/peers', methods=['GET'])
def list_peers():
    with peer_lock:
        return jsonify({
            "peers": [
                {
                    "id": pid, 
                    "address": p['address'],
                    "workload": p['workload'],
                    "files": p['files']
                } for pid, p in peers.items()
            ]
        })

@app.route('/assign-workload', methods=['POST'])
def assign_workload():
    data = request.json
    suitable_peers = []
    
    with peer_lock:
        for pid, peer in peers.items():
            if peer['workload'] < WORKLOAD_THRESHOLD:
                suitable_peers.append(pid)
                
        if not suitable_peers:
            return jsonify({"error": "No available peers"}), 503
            
        selected_peer = random.choice(suitable_peers)
        peers[selected_peer]['workload'] += 1
        
    return jsonify({
        "assigned_peer": peers[selected_peer]['address'],
        "files": peers[selected_peer]['files']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
