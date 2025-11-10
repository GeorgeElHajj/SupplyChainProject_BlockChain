import argparse
import threading
import requests
import time
from flask import Flask, jsonify, request
from flask_cors import CORS

from blockchain import Blockchain, Block
from crypto_utils import create_signed_transaction
import datetime
import sys

sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
CORS(app)
lock = threading.Lock()

blockchain = None
PORT = None


# ------------------ UTILITIES ------------------
def ts_to_iso(ts):
    return datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z"


def get_my_address():
    """Get this node's address"""
    return f"http://localhost:{PORT}"


def broadcast(endpoint, data, exclude_self=True):
    """Broadcast data to all known nodes"""

    def task():
        my_address = get_my_address()
        for node in list(blockchain.nodes):
            if exclude_self and node == my_address:
                continue
            try:
                requests.post(f"{node}{endpoint}", json=data, timeout=3)
                print(f"✅ Broadcasted to {node}{endpoint}")
            except Exception as e:
                print(f"❌ Failed to broadcast to {node}: {e}")

    threading.Thread(target=task, daemon=True).start()


def sync_with_network():
    """Enhanced synchronization: syncs both chain and mempool"""
    with lock:
        if blockchain is None:
            return

        print("🔄 Starting network sync...")
        my_address = get_my_address()
        longest_chain = blockchain.chain
        max_mempool = blockchain.mempool.copy()

        for node in list(blockchain.nodes):
            if node == my_address:
                continue

            try:
                # Sync chain
                r = requests.get(f"{node}/chain", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    remote_chain = data["chain"]
                    valid, _ = blockchain.is_chain_valid(remote_chain)

                    if len(remote_chain) > len(longest_chain) and valid:
                        longest_chain = remote_chain
                        print(f"📥 Found longer valid chain at {node}")

                # Sync mempool
                r = requests.get(f"{node}/mempool", timeout=3)
                if r.status_code == 200:
                    remote_mempool = r.json().get("mempool", [])
                    if len(remote_mempool) > len(max_mempool):
                        max_mempool = remote_mempool
                        print(f"📥 Found larger mempool at {node}")

                # Sync node list
                r = requests.get(f"{node}/nodes", timeout=3)
                if r.status_code == 200:
                    remote_nodes = r.json().get("nodes", [])
                    for remote_node in remote_nodes:
                        if remote_node == my_address:
                            continue
                        if remote_node not in blockchain.nodes:
                            blockchain.add_node(remote_node)
                            print(f"🆕 Discovered new node: {remote_node}")

            except Exception as e:
                print(f"⚠️  Node {node} appears to be down: {e}")

        if longest_chain != blockchain.chain:
            blockchain.replace_chain(longest_chain)
            print("✅ Chain updated from network")

        if len(max_mempool) > len(blockchain.mempool):
            blockchain.sync_mempool(max_mempool)
            print("✅ Mempool synced from network")

        print(
            f"✅ Sync complete. Chain: {len(blockchain.chain)}, Mempool: {len(blockchain.mempool)}, Nodes: {len(blockchain.nodes)}")


def register_with_bootstrap_nodes():
    """Register this node with all bootstrap nodes"""
    time.sleep(2)

    my_address = get_my_address()
    print(f"\n🚀 Registering with network as {my_address}")

    for peer in blockchain.bootstrap_nodes:
        if peer == my_address:
            continue

        try:
            response = requests.post(
                f"{peer}/nodes/register",
                json={"node_url": my_address},
                timeout=5
            )
            if response.status_code in [200, 201]:
                print(f"✅ Registered with {peer}")
                blockchain.add_node(peer)

                r = requests.get(f"{peer}/nodes", timeout=3)
                if r.status_code == 200:
                    their_nodes = r.json().get("nodes", [])
                    for node in their_nodes:
                        if node == my_address:
                            continue
                        if node not in blockchain.nodes:
                            blockchain.add_node(node)
                            print(f"🔍 Discovered peer: {node}")
            else:
                print(f"⚠️  Registration failed with {peer}: {response.status_code}")

        except Exception as e:
            print(f"❌ Could not register with {peer}: {e}")

    print("\n🔄 Performing initial sync...")
    sync_with_network()
    print(f"✅ Node ready! Connected to {len(blockchain.nodes)} peers\n")


# ------------------ ROUTES ------------------
@app.route("/add-transaction", methods=["POST"])
def add_transaction():
    tx_data = request.get_json()
    required = ["batch_id", "action", "actor", "metadata"]
    if not all(k in tx_data for k in required):
        return jsonify({"error": "Missing transaction fields"}), 400

    # Extract signature if present
    signature = tx_data.get("signature")
    public_key = tx_data.get("public_key")

    result = blockchain.add_transaction(
        tx_data["batch_id"],
        tx_data["action"],
        tx_data["actor"],
        tx_data["metadata"],
        signature=signature,
        public_key=public_key,
        timestamp = tx_data.get("timestamp")  # <-- add this line

    )

    if result is None:
        return jsonify({"error": "Invalid signature"}), 401

    broadcast("/receive-transaction", tx_data)
    return jsonify({"message": "Transaction added"}), 201


@app.route("/receive-transaction", methods=["POST"])
def receive_transaction():
    tx_data = request.get_json()
    signature = tx_data.get("signature")
    public_key = tx_data.get("public_key")

    result = blockchain.add_transaction(
        tx_data["batch_id"],
        tx_data["action"],
        tx_data["actor"],
        tx_data["metadata"],
        signature=signature,
        public_key=public_key,
        timestamp=tx_data.get("timestamp")

    )

    if result is None:
        return jsonify({"error": "Invalid signature"}), 401

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
            blockchain.mempool = []
            blockchain._delete_mempool_db()
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


@app.route("/mempool", methods=["GET"])
def get_mempool():
    return jsonify({
        "mempool": blockchain.mempool,
        "count": len(blockchain.mempool)
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
            "block_timestamp": ts_to_iso(h["block_timestamp"]),
            "signature_valid": h.get("signature_valid", None),
            "has_signature": "signature" in h
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
    print(f"🆕 New node registered: {node_url}")

    return jsonify({
        "message": "Node registered successfully",
        "your_node": node_url,
        "all_nodes": list(blockchain.nodes)
    }), 201


@app.route("/nodes", methods=["GET"])
def get_nodes():
    return jsonify({"nodes": list(blockchain.nodes), "count": len(blockchain.nodes)}), 200


@app.route("/status", methods=["GET"])
def get_status():
    return jsonify({
        "node": get_my_address(),
        "chain_length": len(blockchain.chain),
        "mempool_size": len(blockchain.mempool),
        "peers": len(blockchain.nodes),
        "difficulty": blockchain.difficulty,
        "crypto_enabled": blockchain.enable_crypto,
        "status": "healthy"
    }), 200


# ------------------ CRYPTO ENDPOINTS (NEW) ------------------
@app.route("/actors/register", methods=["POST"])
def register_actor():
    """Register a new actor and generate keys"""
    data = request.get_json()
    actor_name = data.get("actor_name")

    if not actor_name:
        return jsonify({"error": "Missing actor_name"}), 400

    if not blockchain.enable_crypto:
        return jsonify({"error": "Cryptography not enabled"}), 400

    result = blockchain.register_actor(actor_name)
    return jsonify(result), 201


@app.route("/actors", methods=["GET"])
def list_actors():
    """List all registered actors"""
    if not blockchain.enable_crypto:
        return jsonify({"actors": [], "crypto_enabled": False}), 200

    actors = blockchain.list_actors()
    return jsonify({"actors": actors, "count": len(actors), "crypto_enabled": True}), 200


# ------------------ CONSENSUS ------------------
def periodic_consensus():
    time.sleep(10)
    while True:
        try:
            sync_with_network()
        except Exception as e:
            print(f"❌ Sync error: {e}")
        time.sleep(30)


# ------------------ MAIN ------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--bootstrap", type=str, default="")
    parser.add_argument("--difficulty", type=int, default=2)
    parser.add_argument("--no-crypto", action="store_true", help="Disable cryptographic signatures")
    args = parser.parse_args()

    PORT = args.port

    bootstrap_nodes = []
    if args.bootstrap:
        bootstrap_nodes = [node.strip() for node in args.bootstrap.split(",") if node.strip()]

    db_file = f"blockchain_{PORT}.db"
    blockchain = Blockchain(
        port=PORT,
        db_file=db_file,
        difficulty=args.difficulty,
        bootstrap_nodes=bootstrap_nodes,
        enable_crypto=not args.no_crypto
    )

    print(f"\n{'=' * 60}")
    print(f"🚀 BLOCKCHAIN NODE STARTING")
    print(f"{'=' * 60}")
    print(f"📍 Port: {PORT}")
    print(f"💾 Database: {db_file}")
    print(f"⛏️  Difficulty: {blockchain.difficulty}")
    print(f"🔐 Cryptography: {'ENABLED' if blockchain.enable_crypto else 'DISABLED'}")
    print(f"🌐 Bootstrap: {bootstrap_nodes if bootstrap_nodes else 'None (Standalone)'}")
    print(f"📊 Chain: {len(blockchain.chain)}")
    print(f"📦 Mempool: {len(blockchain.mempool)}")
    print(f"👥 Peers: {len(blockchain.nodes)}")
    print(f"{'=' * 60}\n")

    threading.Thread(target=periodic_consensus, daemon=True).start()

    if bootstrap_nodes:
        threading.Thread(target=register_with_bootstrap_nodes, daemon=True).start()

    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)