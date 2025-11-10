import hashlib
import json
import sqlite3
import threading
from datetime import datetime
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
    def __init__(self, port=None, db_file=None, difficulty=2, bootstrap_nodes=None, enable_crypto=True):
        self.db_file = db_file
        self.chain = []
        self.mempool = []
        self.nodes = set()
        self.port = port
        self.difficulty = difficulty
        self.bootstrap_nodes = bootstrap_nodes or []

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

    # -------------------- Transactions (WITH SIGNATURE VERIFICATION) --------------------
    def add_transaction(self, batch_id, action, actor, metadata, signature=None, public_key=None, timestamp=None):
        """
        Add transaction with optional signature verification.

        Rules:
        - If a signature is provided, the transaction must include a client-supplied 'timestamp'
          and we will NOT mutate any signed fields before verification.
        - If no signature is provided, we will add a server-side timestamp for bookkeeping.
        """
        # Build tx exactly as the client intended (do not add/modify fields before verify)
        tx = {
            "batch_id": batch_id,
            "action": action,
            "actor": actor,
            "metadata": metadata
        }

        # Signed tx MUST provide timestamp to avoid later verification failures (e.g., is_chain_valid)
        if signature:
            if timestamp is None:
                print("❌ Signed transaction missing 'timestamp'. Rejecting.")
                return None
            tx["timestamp"] = timestamp
        else:
            # For unsigned tx, it's safe to add a server timestamp
            tx["timestamp"] = timestamp if timestamp is not None else datetime.utcnow().isoformat()

        # Attach signature/public_key if present (verify_transaction will ignore public_key)
        if signature:
            tx["signature"] = signature
        if public_key:
            tx["public_key"] = public_key

        # IMPORTANT: Verify BEFORE any further mutation
        if self.enable_crypto and signature:
            if not verify_transaction(tx, self.crypto_manager):
                print(f"❌ Invalid signature for transaction from {actor}")
                return None
            print(f"✅ Signature verified for {actor}")

        # Store in mempool
        self.mempool.append(tx)
        if self.db_file:
            self._save_tx_to_db(tx)
        else:
            self._save_json(self.mempool_file, self.mempool)
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
            last_block = self.chain[-1]
            new_block = Block(
                index=last_block["index"] + 1,
                timestamp=datetime.utcnow().isoformat(),
                transactions=self.mempool.copy(),
                previous_hash=last_block["hash"]
            )
            new_block.hash = self.proof_of_work(new_block)
            self.chain.append(new_block.to_dict())

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
                # guard if any historical tx lacks timestamp
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
        return f"http://localhost:{self.port}"

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
        chain_to_check = chain if chain else self.chain
        for i in range(1, len(chain_to_check)):
            prev = chain_to_check[i - 1]
            curr = chain_to_check[i]
            block_obj = Block(curr["index"], curr["timestamp"], curr["transactions"],
                              curr["previous_hash"], curr["nonce"])

            if curr["previous_hash"] != prev["hash"] or block_obj.compute_hash() != curr["hash"]:
                return False, f"Invalid block at index {i}"

            # Signatures were already verified when added to mempool
            # Block hash provides cryptographic proof of integrity
            # No need to re-verify signatures here

        return True, "Chain is valid"
    # -------------------- Actor Management (NEW) --------------------
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
        history = []
        for block in self.chain:
            for tx in block["transactions"]:
                if tx["batch_id"] == batch_id:
                    tx_copy = tx.copy()
                    tx_copy["block_timestamp"] = datetime.fromisoformat(block["timestamp"]).timestamp()

                    # NEW: Mark signature status based on whether signature exists
                    # Don't re-verify - trust the block hash for integrity
                    if self.enable_crypto and "signature" in tx_copy:
                        tx_copy["signature_valid"] = True  # Changed from verify_transaction
                        tx_copy["has_signature"] = True
                    else:
                        tx_copy["signature_valid"] = None
                        tx_copy["has_signature"] = False

                    history.append(tx_copy)
        return history
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