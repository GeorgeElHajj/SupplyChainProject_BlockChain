import hashlib
import json
import sqlite3
import threading
from datetime import datetime

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
    def __init__(self, port=None, db_file=None, difficulty=2):
        self.db_file = db_file
        self.chain = []
        self.mempool = []
        self.nodes = set()
        self.port = port
        self.difficulty = difficulty

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

    # -------------------- Transactions --------------------
    def add_transaction(self, batch_id, action, actor, metadata):
        tx = {
            "batch_id": batch_id,
            "action": action,
            "actor": actor,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat()
        }
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
        self.chain = [b.to_dict() if isinstance(b, Block) else b for b in new_chain]
        if self.db_file:
            import sqlite3
            with sqlite3.connect(self.db_file) as conn:
                c = conn.cursor()
                c.execute("DELETE FROM chain")
                for b in self.chain:
                    c.execute("INSERT INTO chain (block) VALUES (?)", (json.dumps(b),))
                conn.commit()

    # -------------------- Nodes --------------------
    def add_node(self, address):
        self.nodes.add(address)
        if self.db_file:
            with sqlite3.connect(self.db_file) as conn:
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO nodes (node) VALUES (?)", (address,))
                conn.commit()
        else:
            self._save_json(self.nodes_file, list(self.nodes))

    # -------------------- Verification --------------------
    def is_chain_valid(self, chain=None):
        chain_to_check = chain if chain else self.chain
        for i in range(1, len(chain_to_check)):
            prev = chain_to_check[i - 1]
            curr = chain_to_check[i]
            block_obj = Block(curr["index"], curr["timestamp"], curr["transactions"], curr["previous_hash"], curr["nonce"])
            if curr["previous_hash"] != prev["hash"] or block_obj.compute_hash() != curr["hash"]:
                return False, f"Invalid block at index {i}"
        return True, "Chain is valid"

    # -------------------- Batch History --------------------
    def get_history(self, batch_id):
        history = []
        for block in self.chain:
            for tx in block["transactions"]:
                if tx["batch_id"] == batch_id:
                    tx_copy = tx.copy()
                    tx_copy["block_timestamp"] = datetime.fromisoformat(block["timestamp"]).timestamp()
                    history.append(tx_copy)
        return history
