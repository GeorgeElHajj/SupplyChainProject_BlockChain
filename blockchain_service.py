import argparse
import threading
import requests
import time
from flask import Flask, jsonify, request
from flask_cors import CORS
from election import detect_master

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
node_ready = False  # CRITICAL: Track if node is ready to accept transactions


# ------------------ UTILITIES ------------------
def ts_to_iso(ts):
    return datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z"


def get_my_address():
    """Get this node's address"""
    return f"http://{blockchain.hostname}:{PORT}"


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
    """Enhanced synchronization: repairs invalid chains and syncs mempool"""
    with lock:
        if blockchain is None:
            return

        print("🔄 Starting network sync...")
        my_address = get_my_address()

        # CRITICAL FIX: Check our chain validity FIRST
        current_valid, validation_msg = blockchain.is_chain_valid()

        if not current_valid:
            print(f"⚠️  LOCAL CHAIN INVALID: {validation_msg}")
            print("🔧 Attempting to repair from network...")

        longest_chain = blockchain.chain
        best_chain_valid = current_valid
        chain_replaced = False
        max_mempool = blockchain.mempool.copy()

        for node in list(blockchain.nodes):
            if node == my_address:
                continue

            try:
                # --- Sync chain ---
                r = requests.get(f"{node}/chain", timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    remote_chain = data["chain"]
                    valid_remote, _ = blockchain.is_chain_valid(remote_chain)

                    # IMPROVED REPLACEMENT LOGIC:
                    # Replace if ANY of these conditions:
                    # (1) Our chain is invalid AND theirs is valid
                    # (2) Both valid, theirs is longer
                    # (3) Both same length, but ours is invalid and theirs is valid
                    should_replace = False

                    if not current_valid and valid_remote:
                        # We're broken, they're good
                        should_replace = True
                        print(f"🔧 Found valid replacement chain at {node}")
                    elif current_valid and valid_remote and len(remote_chain) > len(longest_chain):
                        # Both good, theirs is longer
                        should_replace = True
                        print(f"📥 Found longer valid chain at {node}")
                    elif not current_valid and not valid_remote:
                        # Both broken, skip
                        print(f"⚠️  Node {node} also has invalid chain")
                        continue

                    if should_replace:
                        longest_chain = remote_chain
                        best_chain_valid = valid_remote
                        chain_replaced = True

                # --- Sync mempool ---
                r = requests.get(f"{node}/mempool", timeout=3)
                if r.status_code == 200:
                    remote_mempool = r.json().get("mempool", [])
                    if len(remote_mempool) > len(max_mempool):
                        max_mempool = remote_mempool
                        print(f"📥 Found larger mempool at {node}")

                # --- Sync node list ---
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

        # Apply replacement if found a better chain
        if chain_replaced and longest_chain != blockchain.chain:
            blockchain.replace_chain(longest_chain)
            print("✅ Chain repaired/updated from network!")

            # CRITICAL: Also reload from DB to persist changes
            if blockchain.db_file:
                blockchain._reload_chain_from_db()

        # Sync mempool if needed
        if len(max_mempool) > len(blockchain.mempool):
            blockchain.sync_mempool(max_mempool)
            print("✅ Mempool synced from network")

        print(f"✅ Sync complete. Chain: {len(blockchain.chain)}, "
              f"Mempool: {len(blockchain.mempool)}, Nodes: {len(blockchain.nodes)}")


def register_with_bootstrap_nodes():
    """Register this node with all bootstrap nodes"""
    global node_ready

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

    # CRITICAL: Mark node as ready after sync
    node_ready = True


# ------------------ ROUTES (FIXED) ------------------
@app.route("/add-transaction", methods=["POST"])
def add_transaction():
    # CRITICAL: Check if node is ready
    if not node_ready:
        print(f"⚠️  Node not ready yet, still syncing...")
        return jsonify({
            "error": "Node not ready",
            "message": "Node is still syncing with the network. Please try again in a few seconds."
        }), 503

    # ADD LOGGING AT THE VERY TOP
    print(f"📨 Received add-transaction request from {request.remote_addr}")

    # Determine MASTER at this moment
    master = detect_master(blockchain.hostname, len(blockchain.chain))

    print(f"🔍 Master election:")
    print(f"   Current node: {blockchain.hostname}")
    print(f"   Detected master: {master}")

    if blockchain.hostname != master:
        print(f"ℹ️  Node {blockchain.hostname} is FOLLOWER, redirecting to master {master}")

        # Forward the request to the master
        try:
            tx_data = request.get_json()
            print(f"🔄 Forwarding transaction: {tx_data.get('action')} for {tx_data.get('batch_id')}")

            response = requests.post(
                f"http://{master}:5000/add-transaction",
                json=tx_data,
                timeout=5
            )

            # CRITICAL: Check if the forward succeeded
            if response.status_code >= 200 and response.status_code < 300:
                print(f"✅ Successfully forwarded to master {master}")
                return jsonify(response.json()), response.status_code
            else:
                # Master rejected it, return the error
                print(f"⚠️  Master {master} rejected: {response.status_code}")
                try:
                    return jsonify(response.json()), response.status_code
                except:
                    return jsonify({"error": f"Master rejected transaction: {response.text}"}), response.status_code

        except requests.exceptions.Timeout:
            print(f"❌ Timeout forwarding to master {master}")
            return jsonify({"error": f"Master node {master} is not responding (timeout)"}), 503
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Cannot connect to master {master}: {e}")
            return jsonify({"error": f"Master node {master} is not available"}), 503
        except Exception as e:
            print(f"❌ Failed to forward to master: {e}")
            return jsonify({"error": f"Failed to forward to master {master}: {str(e)}"}), 503

    # === MASTER NODE LOGIC ===
    print(f"👑 Processing as MASTER node")

    tx_data = request.get_json()
    print(f"📦 Transaction data received: {tx_data}")

    required = ["batch_id", "action", "actor", "metadata"]
    if not all(k in tx_data for k in required):
        missing = [k for k in required if k not in tx_data]
        print(f"❌ Missing required fields: {missing}")
        print(f"   Received keys: {list(tx_data.keys())}")
        return jsonify({"error": f"Missing transaction fields: {missing}"}), 400

    # Check if already exists BEFORE adding
    batch_id = tx_data["batch_id"]
    action = tx_data["action"]
    timestamp = tx_data.get("timestamp")

    print(f"🔍 Checking for duplicates: {action} for {batch_id}")

    # Check blockchain
    history = blockchain.get_history(batch_id)
    if any(tx["action"] == action and tx.get("timestamp") == timestamp for tx in history):
        print(f"⚠️  Transaction already in blockchain: {action} for {batch_id}")
        return jsonify({"error": "Transaction already exists", "message": "Duplicate detected"}), 409

    # Check mempool
    if any(tx["batch_id"] == batch_id and tx["action"] == action and tx.get("timestamp") == timestamp
           for tx in blockchain.mempool):
        print(f"⚠️  Transaction already in mempool: {action} for {batch_id}")
        return jsonify({"error": "Transaction already pending", "message": "Duplicate detected"}), 409

    signature = tx_data.get("signature")
    public_key = tx_data.get("public_key")

    print(f"🔐 Adding transaction to blockchain...")
    print(f"   - Has signature: {signature is not None}")
    print(f"   - Has public_key: {public_key is not None}")

    result = blockchain.add_transaction(
        tx_data["batch_id"],
        tx_data["action"],
        tx_data["actor"],
        tx_data["metadata"],
        signature=signature,
        public_key=public_key,
        timestamp=tx_data.get("timestamp"),
    )

    if result is None:
        print(f"❌ Transaction validation failed")

        # Check if it's because action already exists (better error message)
        history = blockchain.get_history(batch_id)
        if any(tx["action"] == action for tx in history):
            return jsonify({
                "error": "Action already performed",
                "message": f"Action '{action}' has already been completed for batch '{batch_id}'"
            }), 409

        return jsonify({"error": "Transaction validation failed"}), 400

    print(f"✅ Transaction added to mempool: {action} for {batch_id}")
    print(f"📢 Broadcasting to network...")

    broadcast("/receive-transaction", tx_data)

    return jsonify({"message": "Transaction added"}), 201


@app.route("/receive-transaction", methods=["POST"])
def receive_transaction():
    master = detect_master(blockchain.hostname, len(blockchain.chain))
    tx_data = request.get_json()

    batch_id = tx_data.get("batch_id")
    action = tx_data.get("action")
    timestamp = tx_data.get("timestamp")

    # Check if already in blockchain
    history = blockchain.get_history(batch_id)
    if any(tx["action"] == action and tx.get("timestamp") == timestamp for tx in history):
        print(f"ℹ️ Transaction already in blockchain, skipping: {action} for {batch_id}")
        return jsonify({"message": "Transaction already exists"}), 200

    # Check if already in mempool
    if any(tx["batch_id"] == batch_id and tx["action"] == action and tx.get("timestamp") == timestamp
           for tx in blockchain.mempool):
        print(f"ℹ️ Transaction already in mempool, skipping: {action} for {batch_id}")
        return jsonify({"message": "Transaction already pending"}), 200

    # CRITICAL FIX: Followers DON'T add to mempool, they wait for the block
    if blockchain.hostname != master:
        print(f"ℹ️ Follower {blockchain.hostname} acknowledged transaction (waiting for block)")
        return jsonify({"message": "Transaction acknowledged by follower"}), 200

    # Only master adds to mempool
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
        return jsonify({"error": "Invalid replicated transaction"}), 400

    print(f"✅ Master added transaction to mempool: {action} for {batch_id}")
    return jsonify({"message": "Transaction received"}), 200


@app.route("/mine", methods=["POST"])
def mine_block():
    master = detect_master(blockchain.hostname, len(blockchain.chain))
    if blockchain.hostname != master:
        return jsonify({"error": "Only master can mine"}), 403

    block = blockchain.mine_block()
    if not block:
        return jsonify({"message": "No transactions to mine"}), 400

    broadcast("/receive-block", block.to_dict())
    return jsonify({"message": "Block mined", "block": block.to_dict()}), 201


@app.route("/receive-block", methods=["POST"])
def receive_block():
    data = request.get_json()
    new_block = Block.from_dict(data)

    with lock:
        last_block = blockchain.chain[-1]

        # If chain mismatch → trigger network sync
        if last_block["hash"] != new_block.previous_hash:
            threading.Thread(target=sync_with_network, daemon=True).start()
            return jsonify({"message": "Chain out of sync. Resolving..."}), 409

        # Accept the block
        success, msg = blockchain.accept_block(data)

        if success:
            return jsonify({"message": msg}), 200
        else:
            return jsonify({"message": msg}), 400


@app.route("/chain", methods=["GET"])
def get_chain():
    """
    Get the entire blockchain.

    FIXED: Handles both Block objects and dicts (when loaded from database)
    """
    valid, msg = blockchain.is_chain_valid()

    # Handle both Block objects and dicts
    chain_data = []
    for block in blockchain.chain:
        if isinstance(block, dict):
            # Already a dict (loaded from DB)
            chain_data.append(block)
        else:
            # Block object, convert to dict
            chain_data.append(block.to_dict())

    return jsonify({
        "chain": chain_data,
        "length": len(blockchain.chain),
        "valid": valid,
        "message": msg
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
    valid, msg = blockchain.is_chain_valid()
    return jsonify({
        "node": get_my_address(),
        "chain_length": len(blockchain.chain),
        "chain_valid": valid,
        "validation_message": msg,
        "mempool_size": len(blockchain.mempool),
        "peers": len(blockchain.nodes),
        "difficulty": blockchain.difficulty,
        "crypto_enabled": blockchain.enable_crypto,
        "ready": node_ready,  # CRITICAL: Include ready status
        "status": "healthy" if node_ready else "syncing"
    }), 200


# ------------------ NEW UTILITY ENDPOINTS ------------------
@app.route("/sync", methods=["POST"])
def force_sync():
    """Manually trigger network sync - useful for testing and recovery"""
    print("🔄 Manual sync triggered...")
    sync_with_network()

    valid, msg = blockchain.is_chain_valid()

    return jsonify({
        "message": "Sync completed",
        "chain_valid": valid,
        "validation_message": msg,
        "chain_length": len(blockchain.chain),
        "mempool_size": len(blockchain.mempool),
        "peers": len(blockchain.nodes)
    }), 200


@app.route("/reload", methods=["POST"])
def reload_from_db():
    """Reload blockchain from database - useful after manual edits"""
    if not blockchain.db_file:
        return jsonify({"error": "Not using database mode"}), 400

    print("🔄 Reloading blockchain from database...")

    with lock:
        blockchain._load_from_db()

    valid, msg = blockchain.is_chain_valid()

    return jsonify({
        "message": "Blockchain reloaded from database",
        "chain_valid": valid,
        "validation_message": msg,
        "chain_length": len(blockchain.chain),
        "mempool_size": len(blockchain.mempool)
    }), 200


# ------------------ CRYPTO ENDPOINTS ------------------
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


# ------------------ CONSENSUS & AUTO-MINING ------------------
def periodic_consensus():
    """Periodic sync with network every 30 seconds"""
    time.sleep(10)  # Wait for node to stabilize
    while True:
        try:
            sync_with_network()
        except Exception as e:
            print(f"❌ Sync error: {e}")
        time.sleep(30)


def auto_mining_daemon():
    """Automatically mine when mempool reaches threshold or time interval"""
    time.sleep(15)  # Wait for node to stabilize

    MINING_THRESHOLD = 10  # Mine when mempool has 10+ transactions
    MINING_INTERVAL = 60  # Or mine every 60 seconds if mempool not empty

    last_mine_time = time.time()

    print(f"⛏️  Auto-mining daemon started")
    print(f"   - Threshold: {MINING_THRESHOLD} transactions")
    print(f"   - Interval: {MINING_INTERVAL} seconds")

    while True:
        try:
            current_time = time.time()
            mempool_size = len(blockchain.mempool)

            should_mine = False
            reason = ""

            # Mine if threshold reached
            if mempool_size >= MINING_THRESHOLD:
                should_mine = True
                reason = f"Mempool threshold ({MINING_THRESHOLD}) reached"

            # Mine if enough time passed and mempool not empty
            elif mempool_size > 0 and (current_time - last_mine_time) >= MINING_INTERVAL:
                should_mine = True
                reason = f"Mining interval ({MINING_INTERVAL}s) elapsed"

            if should_mine:
                print(f"⛏️  {reason}. Mining block with {mempool_size} transactions...")
                block = blockchain.mine_block()

                if block:
                    print(f"✅ Auto-mined block #{block.index} with {len(block.transactions)} transactions")
                    broadcast("/receive-block", block.to_dict())
                    last_mine_time = current_time
                else:
                    print("⚠️  No transactions to mine")

        except Exception as e:
            print(f"❌ Auto-mining error: {e}")

        time.sleep(10)  # Check every 10 seconds


# ------------------ MAIN ------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--hostname", type=str, default="localhost",
                        help="Node hostname (for Docker use container name)")
    parser.add_argument("--bootstrap", type=str, default="")
    parser.add_argument("--difficulty", type=int, default=2)
    parser.add_argument("--no-crypto", action="store_true", help="Disable cryptographic signatures")
    parser.add_argument("--no-auto-mine", action="store_true", help="Disable automatic mining")
    args = parser.parse_args()

    PORT = args.port

    bootstrap_nodes = []
    if args.bootstrap:
        bootstrap_nodes = [node.strip() for node in args.bootstrap.split(",") if node.strip()]

    db_file = f"blockchain_{PORT}.db"
    blockchain = Blockchain(
        port=PORT,
        hostname=args.hostname,
        db_file=db_file,
        difficulty=args.difficulty,
        bootstrap_nodes=bootstrap_nodes,
        enable_crypto=not args.no_crypto,
        max_mempool_size=1000
    )

    print(f"\n{'=' * 60}")
    print(f"🚀 BLOCKCHAIN NODE STARTING")
    print(f"{'=' * 60}")
    print(f"📍 Port: {PORT}")
    print(f"🏠 Hostname: {blockchain.hostname}")
    print(f"💾 Database: {db_file}")
    print(f"⛏️  Difficulty: {blockchain.difficulty}")
    print(f"🔐 Cryptography: {'ENABLED' if blockchain.enable_crypto else 'DISABLED'}")
    print(f"⛏️  Auto-mining: {'ENABLED' if not args.no_auto_mine else 'DISABLED'}")
    print(f"🌐 Bootstrap: {bootstrap_nodes if bootstrap_nodes else 'None (Standalone)'}")
    print(f"📊 Chain: {len(blockchain.chain)} blocks")
    print(f"📦 Mempool: {len(blockchain.mempool)} transactions")
    print(f"👥 Peers: {len(blockchain.nodes)} connected")

    # Validate chain on startup
    valid, msg = blockchain.is_chain_valid()
    print(f"🔍 Chain Status: {'✅ VALID' if valid else '❌ INVALID'}")
    if not valid:
        print(f"   ⚠️  {msg}")
        print(f"   🔧 Will attempt auto-repair on next sync cycle")

    print(f"{'=' * 60}\n")

    # CRITICAL: If standalone (no bootstrap), mark as ready immediately
    if not bootstrap_nodes:
        node_ready = True
        print("✅ Standalone node ready immediately\n")

    # Start background daemons
    threading.Thread(target=periodic_consensus, daemon=True).start()

    if not args.no_auto_mine:
        threading.Thread(target=auto_mining_daemon, daemon=True).start()

    if bootstrap_nodes:
        threading.Thread(target=register_with_bootstrap_nodes, daemon=True).start()

    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)