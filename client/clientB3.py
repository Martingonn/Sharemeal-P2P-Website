import requests
import time
import os
import random

SERVER_URL = "http://localhost:5000"
PEER_ID = "client_" + str(random.randint(1000, 9999))
FILES_DIR = "website_files"

def get_files_from_peers():
    while True:
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
                print("No other peers found. Waiting...")

        except requests.exceptions.RequestException as e:
            print(f"Error getting peer list: {e}")

        time.sleep(60)  # Check every 60 seconds

if __name__ == '__main__':
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)

    get_files_from_peers()
