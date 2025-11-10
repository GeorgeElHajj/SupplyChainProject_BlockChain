"""
crypto_utils.py - Cryptographic utilities for blockchain
Handles RSA key generation, transaction signing, and verification
"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import json
import base64
import os


class CryptoManager:
    """Manages cryptographic operations for blockchain transactions"""

    def __init__(self, keys_dir="keys"):
        self.keys_dir = keys_dir
        self.actors = {}  # actor_name -> public_key
        self._ensure_keys_dir()

    def _ensure_keys_dir(self):
        """Create keys directory if it doesn't exist"""
        if not os.path.exists(self.keys_dir):
            os.makedirs(self.keys_dir)

    def generate_key_pair(self, actor_name):
        """
        Generate RSA key pair for an actor
        Returns: (private_key, public_key)
        """
        print(f"🔐 Generating key pair for {actor_name}...")

        # Generate private key (2048 bits)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Get public key
        public_key = private_key.public_key()

        # Save keys to files
        self._save_private_key(actor_name, private_key)
        self._save_public_key(actor_name, public_key)

        # Store public key in memory
        self.actors[actor_name] = public_key

        print(f"✅ Keys generated for {actor_name}")
        return private_key, public_key

    def _save_private_key(self, actor_name, private_key):
        """Save private key to PEM file"""
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        filepath = os.path.join(self.keys_dir, f"{actor_name}_private.pem")
        with open(filepath, 'wb') as f:
            f.write(pem)

        # Set file permissions (read/write for owner only)
        os.chmod(filepath, 0o600)

    def _save_public_key(self, actor_name, public_key):
        """Save public key to PEM file"""
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        filepath = os.path.join(self.keys_dir, f"{actor_name}_public.pem")
        with open(filepath, 'wb') as f:
            f.write(pem)

    def load_private_key(self, actor_name):
        """Load private key from file"""
        filepath = os.path.join(self.keys_dir, f"{actor_name}_private.pem")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Private key for {actor_name} not found")

        with open(filepath, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )

        return private_key

    def load_public_key(self, actor_name):
        """Load public key from file"""
        filepath = os.path.join(self.keys_dir, f"{actor_name}_public.pem")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Public key for {actor_name} not found")

        with open(filepath, 'rb') as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

        # Store in memory
        self.actors[actor_name] = public_key
        return public_key

    def get_public_key_string(self, actor_name):
        """Get public key as base64 string for storage"""
        if actor_name not in self.actors:
            self.load_public_key(actor_name)

        public_key = self.actors[actor_name]
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return base64.b64encode(pem).decode('utf-8')

    def sign_transaction(self, actor_name, transaction_data):
        """
        Sign transaction data with actor's private key

        Args:
            actor_name: Name of the actor signing
            transaction_data: Dict containing transaction details

        Returns:
            signature: Base64 encoded signature
        """
        # Load private key
        private_key = self.load_private_key(actor_name)

        # Create canonical JSON (sorted keys, no whitespace)
        message = json.dumps(transaction_data, sort_keys=True, separators=(',', ':')).encode('utf-8')

        # Sign the message
        signature = private_key.sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        # Return base64 encoded signature
        return base64.b64encode(signature).decode('utf-8')

    def verify_signature(self, actor_name, transaction_data, signature_b64):
        """
        Verify transaction signature

        Args:
            actor_name: Name of the actor who signed
            transaction_data: Dict containing transaction details
            signature_b64: Base64 encoded signature

        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Load public key
            if actor_name not in self.actors:
                self.load_public_key(actor_name)

            public_key = self.actors[actor_name]

            # Decode signature
            signature = base64.b64decode(signature_b64)

            # Create canonical JSON
            message = json.dumps(transaction_data, sort_keys=True, separators=(',', ':')).encode('utf-8')

            # Verify signature
            public_key.verify(
                signature,
                message,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            return True

        except Exception as e:
            print(f"❌ Signature verification failed: {e}")
            return False

    def register_actor(self, actor_name):
        """
        Register a new actor (generate keys if they don't exist)

        Returns:
            dict: Actor information including public key
        """
        private_key_path = os.path.join(self.keys_dir, f"{actor_name}_private.pem")

        if os.path.exists(private_key_path):
            # Keys already exist, load them
            print(f"📂 Loading existing keys for {actor_name}")
            self.load_public_key(actor_name)
        else:
            # Generate new keys
            self.generate_key_pair(actor_name)

        return {
            "actor": actor_name,
            "public_key": self.get_public_key_string(actor_name),
            "registered": True
        }

    def list_actors(self):
        """List all registered actors"""
        actors = []

        if not os.path.exists(self.keys_dir):
            return actors

        for filename in os.listdir(self.keys_dir):
            if filename.endswith("_public.pem"):
                actor_name = filename.replace("_public.pem", "")
                actors.append(actor_name)

        return actors


# Helper functions for easy use

def create_signed_transaction(actor_name, batch_id, action, metadata, crypto_manager):
    """
    Create a signed transaction

    Returns:
        dict: Transaction with signature
    """
    import datetime

    # Transaction data (what gets signed)
    transaction_data = {
        "batch_id": batch_id,
        "action": action,
        "actor": actor_name,
        "metadata": metadata,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    # Sign the transaction
    signature = crypto_manager.sign_transaction(actor_name, transaction_data)

    # Add signature and public key to transaction
    transaction_data["signature"] = signature
    transaction_data["public_key"] = crypto_manager.get_public_key_string(actor_name)

    return transaction_data


def verify_transaction(transaction, crypto_manager):
    """
    Verify a transaction's signature

    Returns:
        bool: True if valid, False otherwise
    """
    if "signature" not in transaction or "actor" not in transaction:
        print("❌ Transaction missing signature or actor")
        return False

    # Extract signature
    signature = transaction["signature"]

    # Create transaction data without signature
    tx_data = {k: v for k, v in transaction.items() if k not in ["signature", "public_key"]}

    # Verify
    return crypto_manager.verify_signature(transaction["actor"], tx_data, signature)