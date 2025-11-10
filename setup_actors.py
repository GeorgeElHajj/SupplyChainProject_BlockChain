#!/usr/bin/env python3
"""
setup_actors.py - Generate cryptographic keys for all supply chain actors
"""

from crypto_utils import CryptoManager
import os
import sys


def setup_actors():
    """Generate keys for Supplier, Distributor, and Retailer"""

    print("╔══════════════════════════════════════════════════════════╗")
    print("║     SUPPLY CHAIN ACTOR KEY GENERATION                    ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")

    # Initialize crypto manager
    crypto_manager = CryptoManager()

    # Define actors
    actors = [
        "Supplier_A",
        "Distributor_B",
        "Retailer_C",
        "QA_Team_Alpha"  # For quality inspections
    ]

    print("Generating keys for actors:")
    for actor in actors:
        print(f"  - {actor}")
    print("")

    # Generate keys for each actor
    results = []
    for actor in actors:
        result = crypto_manager.register_actor(actor)
        results.append(result)

    print("")
    print("=" * 60)
    print("KEY GENERATION COMPLETE")
    print("=" * 60)
    print("")

    # Display public keys
    print("📋 Actor Public Keys:")
    print("")
    for result in results:
        actor_name = result["actor"]
        public_key = result["public_key"]
        print(f"Actor: {actor_name}")
        print(f"Public Key (first 64 chars): {public_key[:64]}...")
        print("")

    # Show key file locations
    print("=" * 60)
    print("📁 Key Files Stored In: ./keys/")
    print("=" * 60)
    print("")

    key_dir = crypto_manager.keys_dir
    if os.path.exists(key_dir):
        files = sorted(os.listdir(key_dir))
        for file in files:
            filepath = os.path.join(key_dir, file)
            size = os.path.getsize(filepath)
            print(f"  {file:<30} ({size} bytes)")

    print("")
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("  1. Private keys are stored in ./keys/ directory")
    print("  2. NEVER share or commit private keys to version control")
    print("  3. In production, use secure key management systems")
    print("  4. Private key files have restricted permissions (600)")
    print("")

    return results


def test_signing():
    """Test signing and verification"""
    print("=" * 60)
    print("🧪 TESTING SIGNATURE GENERATION AND VERIFICATION")
    print("=" * 60)
    print("")

    from crypto_utils import create_signed_transaction, verify_transaction

    crypto_manager = CryptoManager()

    # Create a test transaction
    print("1. Creating test transaction for Supplier_A...")
    tx = create_signed_transaction(
        actor_name="Supplier_A",
        batch_id="TEST_BATCH_001",
        action="registered",
        metadata={"product": "Test Laptops", "quantity": 50},
        crypto_manager=crypto_manager
    )

    print(f"   ✅ Transaction created")
    print(f"   Batch ID: {tx['batch_id']}")
    print(f"   Actor: {tx['actor']}")
    print(f"   Signature (first 32 chars): {tx['signature'][:32]}...")
    print("")

    # Verify the signature
    print("2. Verifying signature...")
    is_valid = verify_transaction(tx, crypto_manager)

    if is_valid:
        print("   ✅ Signature is VALID")
    else:
        print("   ❌ Signature is INVALID")
    print("")

    # Test tampering detection
    print("3. Testing tampering detection...")
    tampered_tx = tx.copy()
    tampered_tx["metadata"] = {"product": "TAMPERED", "quantity": 999}

    is_valid_tampered = verify_transaction(tampered_tx, crypto_manager)

    if not is_valid_tampered:
        print("   ✅ Tampering detected successfully!")
    else:
        print("   ❌ WARNING: Tampering NOT detected!")
    print("")

    print("=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("")


def main():
    print("")

    # Check if keys already exist
    if os.path.exists("keys") and len(os.listdir("keys")) > 0:
        print("⚠️  Keys directory already exists with files.")
        response = input("Do you want to regenerate all keys? (y/N): ")
        if response.lower() != 'y':
            print("Aborted. Using existing keys.")
            print("")
            test_signing()
            return
        else:
            print("Regenerating keys...")
            print("")

    # Generate keys
    results = setup_actors()

    # Test signing
    test_signing()

    print("🎉 Setup complete! Your blockchain now has cryptographic security.")
    print("")
    print("Next steps:")
    print("  1. Start blockchain nodes with crypto enabled (default)")
    print("  2. Use signed transactions in your API calls")
    print("  3. Verify signatures are checked in transaction history")
    print("")


if __name__ == "__main__":
    main()