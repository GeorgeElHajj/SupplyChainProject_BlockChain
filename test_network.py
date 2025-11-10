#!/usr/bin/env python
"""
test_network.py - Test the blockchain network functionality
"""
import requests
import time
import json
import sys

BASE_URLS = [
    "http://localhost:5000",
    "http://localhost:5001",
    "http://localhost:5002"
]

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def check_node_status(url):
    """Check if a node is running"""
    try:
        r = requests.get(f"{url}/status", timeout=2)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ {url}")
            print(f"   Chain Length: {data['chain_length']}")
            print(f"   Mempool: {data['mempool_size']}")
            print(f"   Peers: {data['peers']}")
            return True
    except Exception as e:
        print(f"❌ {url} - {e}")
        return False

def check_all_nodes():
    """Check status of all nodes"""
    print_section("NODE STATUS CHECK")
    alive = []
    for url in BASE_URLS:
        if check_node_status(url):
            alive.append(url)
    return alive

def check_peer_discovery():
    """Verify that nodes discovered each other"""
    print_section("PEER DISCOVERY CHECK")
    for url in BASE_URLS:
        try:
            r = requests.get(f"{url}/nodes", timeout=2)
            if r.status_code == 200:
                data = r.json()
                print(f"✅ {url} knows about {data['count']} peers:")
                for peer in data['nodes']:
                    print(f"   - {peer}")
        except Exception as e:
            print(f"❌ {url} - {e}")

def add_transaction(url, batch_id, action, actor):
    """Add a transaction to a specific node"""
    payload = {
        "batch_id": batch_id,
        "action": action,
        "actor": actor,
        "metadata": {"test": "data"}
    }
    try:
        r = requests.post(f"{url}/add-transaction", json=payload, timeout=5)
        if r.status_code == 201:
            print(f"✅ Transaction added to {url}")
            return True
        else:
            print(f"❌ Failed: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_transaction_propagation():
    """Test if transactions propagate to all nodes"""
    print_section("TRANSACTION PROPAGATION TEST")

    batch_id = f"BATCH_{int(time.time())}"
    print(f"📦 Creating transaction with batch_id: {batch_id}")
    print(f"📤 Adding transaction to Node 1 (port 5000)...")

    if not add_transaction(BASE_URLS[0], batch_id, "registered", "Supplier_A"):
        print("❌ Failed to add transaction")
        return False

    print("\n⏳ Waiting 3 seconds for propagation...")
    time.sleep(3)

    print("\n🔍 Checking if transaction reached all nodes...")
    for url in BASE_URLS:
        try:
            r = requests.get(f"{url}/mempool", timeout=2)
            if r.status_code == 200:
                data = r.json()
                found = any(tx['batch_id'] == batch_id for tx in data['mempool'])
                if found:
                    print(f"✅ {url} - Transaction found in mempool")
                else:
                    print(f"⚠️  {url} - Transaction NOT in mempool")
        except Exception as e:
            print(f"❌ {url} - Error: {e}")

    return True

def test_mining_and_sync():
    """Test mining and chain synchronization"""
    print_section("MINING & CHAIN SYNC TEST")

    batch_id = f"BATCH_MINE_{int(time.time())}"

    print("Step 1: Add transaction to Node 1")
    add_transaction(BASE_URLS[0], batch_id, "quality_checked", "Supplier_B")

    time.sleep(2)

    print("\nStep 2: Mine block on Node 1")
    try:
        r = requests.post(f"{BASE_URLS[0]}/mine", timeout=10)
        if r.status_code == 201:
            print("✅ Block mined successfully")
            block_data = r.json()
            print(f"   Block: {block_data['block']['index']}")
        else:
            print(f"❌ Mining failed: {r.status_code}")
            return False
    except Exception as e:
        print(f"❌ Mining error: {e}")
        return False

    print("\n⏳ Waiting 5 seconds for chain sync...")
    time.sleep(5)

    print("\nStep 3: Verify all nodes have the same chain")
    chain_lengths = []
    for url in BASE_URLS:
        try:
            r = requests.get(f"{url}/chain", timeout=2)
            if r.status_code == 200:
                data = r.json()
                chain_lengths.append(data['length'])
                print(f"✅ {url} - Chain length: {data['length']}, Valid: {data['valid']}")
        except Exception as e:
            print(f"❌ {url} - {e}")

    if len(set(chain_lengths)) == 1:
        print(f"\n🎉 SUCCESS! All nodes synchronized (chain length: {chain_lengths[0]})")
        return True
    else:
        print(f"\n❌ SYNC ISSUE! Chain lengths differ: {chain_lengths}")
        return False

def test_node_recovery():
    """Instructions for testing node recovery"""
    print_section("NODE RECOVERY TEST (MANUAL)")
    print("To test node recovery:")
    print("1. Stop Node 2: kill $(ps aux | grep 'port 5001' | grep -v grep | awk '{print $2}')")
    print("2. Add transactions and mine blocks")
    print("3. Restart Node 2: python blockchain_service.py --port 5001 --bootstrap 'http://localhost:5000'")
    print("4. Check if Node 2 syncs: curl http://localhost:5001/status")
    print("\nNote: Automated recovery testing requires more complex orchestration")

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║         BLOCKCHAIN NETWORK TEST SUITE                    ║
╚══════════════════════════════════════════════════════════╝
    """)

    # Test 1: Check if all nodes are running
    alive_nodes = check_all_nodes()
    if len(alive_nodes) < 3:
        print("\n⚠️  Not all nodes are running. Please start the network first:")
        print("   ./start_network.sh")
        sys.exit(1)

    # Test 2: Check peer discovery
    time.sleep(2)
    check_peer_discovery()

    # Test 3: Transaction propagation
    time.sleep(2)
    if not test_transaction_propagation():
        print("\n❌ Transaction propagation test failed")

    # Test 4: Mining and synchronization
    time.sleep(2)
    if not test_mining_and_sync():
        print("\n❌ Mining/sync test failed")

    # Test 5: Manual recovery test instructions
    time.sleep(2)
    test_node_recovery()

    print_section("TEST SUITE COMPLETE")
    print("✅ All automated tests finished")
    print("\n💡 Next steps:")
    print("   - View logs: tail -f node1.log")
    print("   - Stop network: ./stop_network.sh")
    print("   - Test recovery manually (see instructions above)")

if __name__ == "__main__":
    main()