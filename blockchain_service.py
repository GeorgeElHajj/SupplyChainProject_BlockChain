import argparse
import threading
import requests
from flask import Flask, jsonify, request
from blockchain import Blockchain, Block
import datetime
import time

app = Flask(__name__)
lock = threading.Lock()

blockchain = None
PORT = None


# ------------------ UTILITIES ------------------
def ts_to_iso(ts):
    return datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z"


def broadcast(endpoint, data):
    def task():
        for node in list(blockchain.nodes):
            if f"localhost:{PORT}" not in node:
                try:
                    requests.post(f"{node}{endpoint}", json=data, timeout=3)
                except Exception:
                    continue
    threading.Thread(target=task, daemon=True).start()


def sync_with_network():
    with lock:
        if blockchain is None:
            return
        longest_chain = blockchain.chain
        for node in list(blockchain.nodes):
            if f"localhost:{PORT}" not in node:
                try:
                    r = requests.get(f"{node}/chain", timeout=3)
                    if r.status_code == 200:
                        data = r.json()
                        remote_chain = [Block.from_dict(b) for b in data["chain"]]
                        valid, _ = blockchain.is_chain_valid(data["chain"])
                        if len(remote_chain) > len(longest_chain) and valid:
                            longest_chain = remote_chain
                except Exception:
                    continue
        if longest_chain != blockchain.chain:
            blockchain.replace_chain(longest_chain)


# ------------------ ROUTES ------------------
@app.route("/add-transaction", methods=["POST"])
def add_transaction():
    tx_data = request.get_json()
    required = ["batch_id", "action", "actor", "metadata"]
    if not all(k in tx_data for k in required):
        return jsonify({"error": "Missing transaction fields"}), 400

    blockchain.add_transaction(tx_data["batch_id"], tx_data["action"], tx_data["actor"], tx_data["metadata"])
    broadcast("/receive-transaction", tx_data)
    return jsonify({"message": "Transaction added"}), 201


@app.route("/receive-transaction", methods=["POST"])
def receive_transaction():
    tx_data = request.get_json()
    blockchain.add_transaction(tx_data["batch_id"], tx_data["action"], tx_data["actor"], tx_data["metadata"])
    return jsonify({"message": "Transaction received"}), 200


@app.route("/mine", methods=["POST"])
def mine_block():
    block = blockchain.mine_block()
    if not block:
        return jsonify({"message": "No transactions to mine"}), 400
    broadcast("/receive-block", block.to_dict())
    return jsonify({"message": "Block mined successfully", "block": block.to_dict()}), 201


@app.route("/receive-block", methods=["POST"])
def receive_block():
    data = request.get_json()
    new_block = Block.from_dict(data)
    with lock:
        last_block = blockchain.chain[-1]
        if last_block["hash"] != new_block.previous_hash:
            threading.Thread(target=sync_with_network, daemon=True).start()
            return jsonify({"message": "Chain out of sync. Resolving..."}), 409
        elif new_block.hash != new_block.compute_hash():
            return jsonify({"message": "Invalid block"}), 400
        else:
            blockchain.chain.append(new_block.to_dict())
            return jsonify({"message": "Block accepted"}), 200


@app.route("/chain", methods=["GET"])
def get_chain():
    valid, msg = blockchain.is_chain_valid()
    return jsonify({
        "length": len(blockchain.chain),
        "valid": valid,
        "message": msg,
        "chain": blockchain.chain
    }), 200


@app.route("/history/<batch_id>", methods=["GET"])
def get_history(batch_id):
    history = blockchain.get_history(batch_id)
    if not history:
        return jsonify({"message": f"No transactions found for batch {batch_id}", "history": []}), 404
    history.sort(key=lambda h: h.get("block_timestamp", 0))
    formatted = [
        {
            "batch_id": h["batch_id"],
            "action": h["action"],
            "actor": h["actor"],
            "timestamp": h["timestamp"],
            "block_timestamp": ts_to_iso(h["block_timestamp"])
        } for h in history
    ]
    return jsonify({"batch_id": batch_id, "transaction_count": len(formatted), "history": formatted}), 200


@app.route("/verify/<batch_id>", methods=["GET"])
def verify(batch_id):
    valid, msg = blockchain.is_chain_valid()
    events = blockchain.get_history(batch_id)
    verified = valid and len(events) > 0
    return jsonify({"batch_id": batch_id, "verified": verified, "events": events, "message": msg}), 200


@app.route("/nodes/register", methods=["POST"])
def register_node():
    data = request.get_json()
    node_url = data.get("node_url")
    if not node_url:
        return jsonify({"error": "Missing node URL"}), 400
    blockchain.add_node(node_url)
    return jsonify({"message": "Node registered", "all_nodes": list(blockchain.nodes)}), 201


@app.route("/nodes", methods=["GET"])
def get_nodes():
    return jsonify({"nodes": list(blockchain.nodes)}), 200


# ------------------ CONSENSUS ------------------
def periodic_consensus():
    while True:
        sync_with_network()
        time.sleep(5)


# ------------------ MAIN ------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    PORT = args.port

    db_file = f"blockchain_{PORT}.db"
    blockchain = Blockchain(db_file=db_file, difficulty=3)

    print(f"\n🚀 Node running on port {PORT}")
    print(f"📦 Using database file: {db_file}")
    print(f"🌐 Registered nodes: {list(blockchain.nodes)}\n")

    threading.Thread(target=periodic_consensus, daemon=True).start()

    app.run(host="0.0.0.0", port=PORT, debug=True)
