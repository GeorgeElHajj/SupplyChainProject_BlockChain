import hashlib
import json
import sqlite3
import threading
from datetime import datetime

import requests

from crypto_utils import CryptoManager, verify_transaction

lock = threading.Lock()


# -------------------- BLOCK --------------------
class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, nonce=0, hash=None):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = hash or self.compute_hash()

    def compute_hash(self):
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        block_json = json.dumps(block_data, sort_keys=True).encode()
        return hashlib.sha256(block_json).hexdigest()

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            transactions=data["transactions"],
            previous_hash=data["previous_hash"],
            nonce=data["nonce"],
            hash=data.get("hash")
        )


# -------------------- BLOCKCHAIN --------------------
class Blockchain:
    def __init__(self, port=None, db_file=None, difficulty=2, bootstrap_nodes=None,
                 enable_crypto=True, max_mempool_size=1000, hostname=None):
        self.db_file = db_file
        self.chain = []
        self.mempool = []
        self.nodes = set()
        self.port = port
        self.hostname = hostname or "localhost"  # Use Docker hostname if provided
        self.difficulty = difficulty
        self.bootstrap_nodes = bootstrap_nodes or []
        self.max_mempool_size = max_mempool_size

        # CRITICAL FIX: Add current_metadata for validation
        self.current_metadata = {}

        # NEW: Cryptographic security
        self.enable_crypto = enable_crypto
        self.crypto_manager = CryptoManager() if enable_crypto else None

        if self.db_file:
            self._init_db()
            self._load_from_db()
        else:
            self.chain_file = f"chain_{port}.json"
            self.mempool_file = f"mempool_{port}.json"
            self.nodes_file = f"nodes_{port}.json"
            self._load_json_files()

        if not self.chain:
            self.create_genesis_block()

    # -------------------- DB INIT --------------------
    def _init_db(self):
        with sqlite3.connect(self.db_file) as conn:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS chain (
                    idx INTEGER PRIMARY KEY,
                    block TEXT
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS mempool (
                    idx INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx TEXT
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node TEXT PRIMARY KEY
                )
            """)
            conn.commit()

    def _load_from_db(self):
        with sqlite3.connect(self.db_file) as conn:
            c = conn.cursor()
            c.execute("SELECT block FROM chain ORDER BY idx")
            rows = c.fetchall()
            self.chain = [json.loads(row[0]) for row in rows]

            c.execute("SELECT tx FROM mempool ORDER BY idx")
            rows = c.fetchall()
            self.mempool = [json.loads(row[0]) for row in rows]

            c.execute("SELECT node FROM nodes")
            rows = c.fetchall()
            self.nodes = set([row[0] for row in rows])

    def _reload_chain_from_db(self):
        """Reload chain from database after replacement"""
        if not self.db_file:
            return

        with sqlite3.connect(self.db_file) as conn:
            c = conn.cursor()

            # Clear and reload chain
            c.execute("SELECT block FROM chain ORDER BY idx")
            rows = c.fetchall()
            self.chain = [json.loads(row[0]) for row in rows]

            print(f"🔄 Reloaded {len(self.chain)} blocks from database")

    def _save_block_to_db(self, block):
        with sqlite3.connect(self.db_file) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO chain (block) VALUES (?)", (json.dumps(block.to_dict()),))
            conn.commit()

    def _save_tx_to_db(self, tx):
        with sqlite3.connect(self.db_file) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO mempool (tx) VALUES (?)", (json.dumps(tx),))
            conn.commit()

    def _delete_mempool_db(self):
        with sqlite3.connect(self.db_file) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM mempool")
            conn.commit()

    # -------------------- JSON fallback --------------------
    def _load_json_files(self):
        import os
        def load(filename, default):
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    try:
                        return json.load(f)
                    except:
                        return default
            return default

        self.chain = load(self.chain_file, [])
        self.mempool = load(self.mempool_file, [])
        self.nodes = set(load(self.nodes_file, []))

    def _save_json(self, filename, data):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    # -------------------- Genesis --------------------
    def create_genesis_block(self):
        genesis = Block(0, datetime.utcnow().isoformat(), [], "0")
        self.chain.append(genesis.to_dict())
        if self.db_file:
            self._save_block_to_db(genesis)
        else:
            self._save_json(self.chain_file, self.chain)

    # -------------------- Transaction Validation (FIXED) --------------------
    def validate_transaction_order(self, batch_id, action, actor):
        """
        Validate transaction follows STRICT SEQUENTIAL order:
        1. registered -> 2. quality_checked -> 3. shipped -> 4. received ->
        5. stored -> 6. delivered -> 7. received_retail -> 8. sold

        Checks BOTH blockchain (mined) AND mempool (pending) for prerequisites.
        """
        # Get existing actions from BLOCKCHAIN
        history = self.get_history(batch_id)
        existing_actions = [tx['action'] for tx in history]

        # ALSO check MEMPOOL for pending transactions (not yet mined)
        mempool_actions = [tx['action'] for tx in self.mempool if tx['batch_id'] == batch_id]

        # Define STRICT sequential order - each step requires the EXACT previous step
        strict_sequence = {
            'registered': None,  # Step 1: Can always register (no prerequisite)
            'quality_checked': 'registered',  # Step 2: Must have Step 1
            'shipped': 'quality_checked',  # Step 3: Must have Step 2
            'received': 'shipped',  # Step 4: Must have Step 3
            'stored': 'received',  # Step 5: Must have Step 4
            'delivered': 'stored',  # Step 6: Must have Step 5
            'received_retail': 'delivered',  # Step 7: Must have Step 6
            'sold': 'received_retail'  # Step 8: Must have Step 7
        }

        # CRITICAL FIX: Check for duplicate actions ONLY in blockchain (not mempool)
        # Mempool can be cleared by mining, so checking it can cause race conditions
        if action in existing_actions:
            return False, f"Action '{action}' already performed for batch {batch_id}"

        # ALSO check mempool to prevent adding duplicate pending transactions
        if action in mempool_actions:
            return False, f"Action '{action}' is already pending in mempool for batch {batch_id}"

        # Validate action is in the allowed sequence
        if action not in strict_sequence:
            return False, f"Invalid action '{action}'. Not in allowed sequence."

        # Check if prerequisite is met (check BOTH blockchain and mempool)
        required_previous = strict_sequence[action]
        all_actions = existing_actions + mempool_actions

        if required_previous is not None:
            # EXACT previous step MUST exist
            if required_previous not in all_actions:
                return False, f"Cannot perform '{action}' without first completing '{required_previous}'"

        # SUCCESS: All validations passed
        return True, "Valid transaction"

    # -------------------- Transactions (WITH SIGNATURE VERIFICATION) --------------------
    def validate_actor_permissions(self, batch_id, action, actor):
        """
        Enforces:
        - Supplier consistency
        - Distributor consistency
        - Retailer consistency
        - SHIPPED -> RECEIVED matching (both supplier & distributor)
        - DELIVERED -> RECEIVED_RETAIL matching (both distributor & retailer)
        """

        history = self.get_history(batch_id)

        # Required roles for each action:
        actor_roles = {
            "registered": "supplier",
            "quality_checked": "supplier",
            "shipped": "supplier",
            "received": "distributor",
            "stored": "distributor",
            "delivered": "distributor",
            "received_retail": "retailer",
            "sold": "retailer",
        }

        # 1 — Unknown action?
        if action not in actor_roles:
            return False, f"Unknown action '{action}'"

        expected_role = actor_roles[action]

        # 2 — First action must be "registered"
        if action == "registered":
            if not actor.lower().startswith("supplier"):
                return False, "Only suppliers can register batches"
            return True, "OK"

        # 3 — Batch must already exist after registration
        if not history:
            return False, f"Batch {batch_id} does not exist yet"

        # 4 — Determine current owner (last actor)
        last_actor = history[-1]["actor"]

        if last_actor.lower().startswith("supplier"):
            owner_role = "supplier"
        elif last_actor.lower().startswith("distributor"):
            owner_role = "distributor"
        elif last_actor.lower().startswith("retailer"):
            owner_role = "retailer"
        else:
            return False, f"Unknown previous actor '{last_actor}'"

        # 5 — Role of current action must match actor type
        if not actor.lower().startswith(expected_role):
            return False, f"'{actor}' is not a valid {expected_role} for action '{action}'"

        # 6 — SAME-ACTOR restriction inside group stages
        group_actions = {
            "supplier": {"registered", "quality_checked", "shipped"},
            "distributor": {"received", "stored", "delivered"},
            "retailer": {"received_retail", "sold"}
        }

        if action in group_actions.get(owner_role, set()):
            if actor != last_actor:
                return False, (
                    f"Ownership violation: '{actor}' cannot perform '{action}'. "
                    f"Current owner is '{last_actor}'."
                )

        # -------------------------------------------------------------------------------------------------------
        # 7 — STRICT CHECK: SHIPPED → RECEIVED (FIXED)
        # -------------------------------------------------------------------------------------------------------
        if action == "received":
            shipped = next((tx for tx in history if tx["action"] == "shipped"), None)
            if shipped is None:
                return False, "Batch must be shipped first"

            # Extract from shipment metadata
            shipped_from = shipped["actor"]  # Supplier who performed the action
            shipped_to = shipped.get("metadata", {}).get("to")  # Intended distributor recipient

            # The current metadata should have "from" field
            current_from = self.current_metadata.get("from")

            # VALIDATION:
            # 1. The distributor receiving MUST match the "to" in shipment
            if shipped_to and actor != shipped_to:
                return False, (
                    f"Invalid receiver. Shipment was sent to '{shipped_to}', "
                    f"but '{actor}' is trying to receive it."
                )

            # 2. The "from" in receive metadata MUST match the supplier who shipped
            if current_from and current_from != shipped_from:
                return False, (
                    f"Invalid supplier in receive metadata. Shipment came from '{shipped_from}', "
                    f"but receive form says '{current_from}'."
                )

        # -------------------------------------------------------------------------------------------------------
        # 8 — STRICT CHECK: DELIVERED → RECEIVED_RETAIL (FIXED)
        # -------------------------------------------------------------------------------------------------------
        if action == "received_retail":
            delivered = next((tx for tx in history if tx["action"] == "delivered"), None)
            if delivered is None:
                return False, "Batch must be delivered before retailer can receive"

            # Extract from delivery metadata
            delivered_from = delivered["actor"]  # Distributor who performed the action
            delivered_to = delivered.get("metadata", {}).get("to")  # Intended retailer recipient

            # The current metadata should have "from" field
            current_from = self.current_metadata.get("from")

            # VALIDATION:
            # 1. The retailer receiving MUST match the "to" in delivery
            if delivered_to and actor != delivered_to:
                return False, (
                    f"Invalid receiver. Delivery was made to '{delivered_to}', "
                    f"but '{actor}' is trying to receive it."
                )

            # 2. The "from" in receive metadata MUST match the distributor who delivered
            if current_from and current_from != delivered_from:
                return False, (
                    f"Invalid distributor in receive metadata. Delivery was sent from '{delivered_from}', "
                    f"but receive form says '{current_from}'."
                )

        return True, "OK"

    def add_transaction(self, batch_id, action, actor, metadata, signature=None, public_key=None, timestamp=None):
        """
        Add transaction with optional signature verification and business logic validation.

        Rules:
        - If a signature is provided, the transaction must include a client-supplied 'timestamp'
          and we will NOT mutate any signed fields before verification.
        - If no signature is provided, we will add a server-side timestamp for bookkeeping.
        - Validates transaction order (e.g., can't ship before registering)
        """
        # Build tx exactly as the client intended (do not add/modify fields before verify)
        tx = {
            "batch_id": batch_id,
            "action": action,
            "actor": actor,
            "metadata": metadata
        }

        # Signed tx MUST provide timestamp to avoid later verification failures
        if signature:
            if timestamp is None:
                print("❌ Signed transaction missing 'timestamp'. Rejecting.")
                return None
            tx["timestamp"] = timestamp
        else:
            # For unsigned tx, it's safe to add a server timestamp
            tx["timestamp"] = timestamp if timestamp is not None else datetime.utcnow().isoformat()

        # Attach signature/public_key if present
        if signature:
            tx["signature"] = signature
        if public_key:
            tx["public_key"] = public_key

        # STEP 1: Validate transaction order (business logic)
        valid, msg = self.validate_transaction_order(batch_id, action, actor)
        if not valid:
            print(f"❌ Transaction validation failed: {msg}")
            return None

        # CRITICAL FIX: Store metadata temporarily for validation
        self.current_metadata = metadata

        ok, actor_msg = self.validate_actor_permissions(batch_id, action, actor)
        if not ok:
            print(f"❌ Permission error: {actor_msg}")
            return None

        # STEP 2: Verify signature if present
        if self.enable_crypto and signature:
            if not verify_transaction(tx, self.crypto_manager):
                print(f"❌ Invalid signature for transaction from {actor}")
                return None
            print(f"✅ Signature verified for {actor}")

        # STEP 3: Check mempool size and auto-mine if needed
        if len(self.mempool) >= self.max_mempool_size:
            print(f"⚠️  Mempool full ({self.max_mempool_size}). Auto-mining triggered...")
            self.mine_block()

        # STEP 4: Store in mempool
        self.mempool.append(tx)
        if self.db_file:
            self._save_tx_to_db(tx)
        else:
            self._save_json(self.mempool_file, self.mempool)

        print(f"✅ Transaction added: {action} for {batch_id} by {actor}")
        return tx

    # -------------------- Mining --------------------
    def proof_of_work(self, block):
        while True:
            hash_val = block.compute_hash()
            if hash_val.startswith("0" * self.difficulty):
                block.hash = hash_val
                return hash_val
            block.nonce += 1

    def mine_block(self):
        with lock:
            if not self.mempool:
                return None

            # CRITICAL FIX: Filter out transactions that are already in blockchain
            valid_mempool = []
            for tx in self.mempool:
                batch_id = tx.get("batch_id")
                action = tx.get("action")
                timestamp = tx.get("timestamp")

                # Check if already in blockchain
                history = self.get_history(batch_id)
                if any(h["action"] == action and h.get("timestamp") == timestamp for h in history):
                    print(f"🗑️ Removing duplicate from mempool before mining: {action} for {batch_id}")
                    continue

                valid_mempool.append(tx)

            if not valid_mempool:
                print("⚠️  No valid transactions to mine (all duplicates)")
                return None

            last_block = self.chain[-1]
            new_block = Block(
                index=last_block["index"] + 1,
                timestamp=datetime.utcnow().isoformat(),
                transactions=valid_mempool,  # Use filtered mempool!
                previous_hash=last_block["hash"]
            )
            new_block.hash = self.proof_of_work(new_block)
            self.chain.append(new_block.to_dict())
            self.broadcast_block(new_block.to_dict())

            if self.db_file:
                self._save_block_to_db(new_block)
                self._delete_mempool_db()
            else:
                self._save_json(self.chain_file, self.chain)
                self._save_json(self.mempool_file, [])

            self.mempool = []

        return new_block
    def replace_chain(self, new_chain):
        """Replace the entire chain with a new one"""
        self.chain = [b.to_dict() if isinstance(b, Block) else b for b in new_chain]
        if self.db_file:
            import sqlite3
            with sqlite3.connect(self.db_file) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM chain")
                for b in self.chain:
                    c.execute("INSERT INTO chain (block) VALUES (?)", (json.dumps(b),))
                conn.commit()

    def sync_mempool(self, remote_mempool):
        """Merge remote mempool with local"""
        with lock:
            existing_txs = set()
            for tx in self.mempool:
                ts = tx.get("timestamp", "")
                tx_sig = f"{tx['batch_id']}_{tx['action']}_{ts}"
                existing_txs.add(tx_sig)

            for tx in remote_mempool:
                ts = tx.get("timestamp", "")
                tx_sig = f"{tx['batch_id']}_{tx['action']}_{ts}"
                if tx_sig not in existing_txs:
                    # Verify signature if crypto enabled
                    if self.enable_crypto and "signature" in tx:
                        if not verify_transaction(tx, self.crypto_manager):
                            print(f"⚠️  Skipping transaction with invalid signature")
                            continue

                    # If unsigned and missing timestamp, stamp it server-side
                    if "signature" not in tx and "timestamp" not in tx:
                        tx["timestamp"] = datetime.utcnow().isoformat()

                    self.mempool.append(tx)
                    if self.db_file:
                        self._save_tx_to_db(tx)
                    existing_txs.add(tx_sig)

    # -------------------- Nodes --------------------
    def get_my_address(self):
        """Return this node's address"""
        return f"http://{self.hostname}:{self.port}"

    def add_node(self, address):
        """Add a node to the network - CRITICAL: Don't add ourselves"""
        my_address = self.get_my_address()
        if address == my_address:
            print(f"⚠️  Skipping self-addition: {address}")
            return

        self.nodes.add(address)
        if self.db_file:
            with sqlite3.connect(self.db_file) as conn:
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO nodes (node) VALUES (?)", (address,))
                conn.commit()
        else:
            self._save_json(self.nodes_file, list(self.nodes))

    def remove_node(self, address):
        """Remove a dead node"""
        if address in self.nodes:
            self.nodes.remove(address)
            if self.db_file:
                with sqlite3.connect(self.db_file) as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM nodes WHERE node = ?", (address,))
                    conn.commit()
            else:
                self._save_json(self.nodes_file, list(self.nodes))

    # -------------------- Verification --------------------
    def is_chain_valid(self, chain=None):
        """Validate blockchain integrity"""
        chain_to_check = chain if chain else self.chain

        if len(chain_to_check) == 0:
            return True, "Empty chain"

        for i in range(1, len(chain_to_check)):
            prev = chain_to_check[i - 1]
            curr = chain_to_check[i]

            # Reconstruct block to verify hash
            block_obj = Block(
                curr["index"],
                curr["timestamp"],
                curr["transactions"],
                curr["previous_hash"],
                curr["nonce"]
            )

            # Check previous hash linkage
            if curr["previous_hash"] != prev["hash"]:
                return False, f"Invalid previous_hash at block {i}"

            # Check block hash
            if block_obj.compute_hash() != curr["hash"]:
                return False, f"Invalid block hash at block {i}"

        return True, "Chain is valid"

    # -------------------- Actor Management --------------------
    def register_actor(self, actor_name):
        """Register a new actor and generate keys"""
        if not self.enable_crypto:
            return {"actor": actor_name, "registered": False, "message": "Crypto disabled"}

        return self.crypto_manager.register_actor(actor_name)

    def list_actors(self):
        """List all registered actors"""
        if not self.enable_crypto:
            return []

        return self.crypto_manager.list_actors()

    # -------------------- Batch History --------------------
    def get_history(self, batch_id):
        """Get complete history for a batch"""
        history = []
        for block in self.chain:
            for tx in block["transactions"]:
                if tx["batch_id"] == batch_id:
                    tx_copy = tx.copy()
                    tx_copy["block_timestamp"] = datetime.fromisoformat(block["timestamp"]).timestamp()

                    # Mark signature status
                    if self.enable_crypto and "signature" in tx_copy:
                        tx_copy["signature_valid"] = True
                        tx_copy["has_signature"] = True
                    else:
                        tx_copy["signature_valid"] = None
                        tx_copy["has_signature"] = False

                    history.append(tx_copy)
        return history

    def broadcast_transaction(self, tx):
        """Broadcast a single transaction to all nodes"""
        for node in list(self.nodes):
            try:
                requests.post(f"{node}/receive-transaction", json=tx, timeout=3)
            except:
                print(f"⚠️ Failed to broadcast transaction to {node}")

    def broadcast_block(self, block_dict):
        """Broadcast newly mined block to all nodes"""
        for node in list(self.nodes):
            try:
                requests.post(f"{node}/receive-block", json=block_dict, timeout=3)
            except:
                print(f"⚠️ Failed to broadcast block to {node}")

    def accept_block(self, block_dict):
        """Accept an incoming block from another node"""
        new_block = Block.from_dict(block_dict)

        # Validate previous hash matches
        last_block = self.chain[-1]
        if new_block.previous_hash != last_block["hash"]:
            return False, "Previous hash mismatch"

        # Validate PoW hash
        if new_block.compute_hash() != new_block.hash:
            return False, "Invalid block hash"

        # ========== ADD THIS: Check for duplicate transactions ==========
        for tx in new_block.transactions:
            batch_id = tx.get("batch_id")
            action = tx.get("action")
            timestamp = tx.get("timestamp")

            # Check if this EXACT transaction already exists in blockchain
            history = self.get_history(batch_id)
            if any(h["action"] == action and h.get("timestamp") == timestamp for h in history):
                print(f"⚠️  Rejecting block with duplicate transaction: {action} for {batch_id}")
                return False, f"Block contains duplicate transaction: {action} for {batch_id}"
        # ========== END ADD ==========
        # Append
        self.chain.append(new_block.to_dict())

        # CRITICAL FIX: Only remove transactions that were INCLUDED in this block
        # Keep other pending transactions in mempool
        mined_transactions = set()
        for tx in new_block.transactions:
            tx_sig = f"{tx['batch_id']}_{tx['action']}_{tx.get('timestamp', '')}"
            mined_transactions.add(tx_sig)

        # Filter mempool to keep only transactions NOT in this block
        new_mempool = []
        for tx in self.mempool:
            tx_sig = f"{tx['batch_id']}_{tx['action']}_{tx.get('timestamp', '')}"
            if tx_sig not in mined_transactions:
                new_mempool.append(tx)
            else:
                print(f"🗑️ Removing mined transaction from mempool: {tx['action']} for {tx['batch_id']}")

        self.mempool = new_mempool

        # Update database if using DB
        if self.db_file:
            # Clear and re-save mempool
            self._delete_mempool_db()
            for tx in self.mempool:
                self._save_tx_to_db(tx)

        print(f"✅ Block accepted. Mempool now has {len(self.mempool)} pending transactions")

        return True, "Block accepted"

    def request_chain_from_peers(self):
        """Pull chain from peers and replace if longer"""
        my_len = len(self.chain)
        best_chain = self.chain

        for node in list(self.nodes):
            try:
                r = requests.get(f"{node}/chain", timeout=3)
                remote = r.json().get("chain", [])
                if len(remote) > my_len:
                    valid, _ = self.is_chain_valid(remote)
                    if valid:
                        best_chain = remote
            except:
                continue

        if best_chain != self.chain:
            self.replace_chain(best_chain)
            return True
        return False

    # -------------------- Bootstrap --------------------
    def bootstrap(self):
        """Called on startup to join the network"""
        if not self.bootstrap_nodes:
            print("⚠️  No bootstrap nodes configured. Running as standalone node.")
            return True

        connected = False
        my_address = self.get_my_address()

        for peer in self.bootstrap_nodes:
            if peer == my_address:
                continue

            try:
                print(f"📡 Attempting to connect to bootstrap node: {peer}")
                self.add_node(peer)
                connected = True
            except Exception as e:
                print(f"❌ Failed to connect to {peer}: {e}")

        if connected:
            print(f"✅ Successfully bootstrapped. Known nodes: {len(self.nodes)}")
        else:
            print("⚠️  Could not connect to any bootstrap nodes. Running as standalone.")

        return connected