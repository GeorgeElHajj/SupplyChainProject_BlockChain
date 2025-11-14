"""
Test Script: Strict Sequential Transaction Order Validation
============================================================

This script demonstrates that the blockchain now enforces STRICT SEQUENTIAL order:
1. registered → 2. quality_checked → 3. shipped → 4. received →
5. stored → 6. delivered → 7. received_retail → 8. sold

You CANNOT skip steps or perform them out of order.
"""

import requests
import time
import json

BASE_URL = "http://localhost:5000"
BATCH_ID = "BATCH_TEST_001"


def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def send_transaction(action, actor, metadata):
    """Send a transaction to the blockchain"""
    payload = {
        "batch_id": BATCH_ID,
        "action": action,
        "actor": actor,
        "metadata": metadata
    }

    try:
        response = requests.post(f"{BASE_URL}/add-transaction", json=payload, timeout=5)

        if response.status_code == 201:
            print(f"✅ SUCCESS: {action} by {actor}")
            return True
        else:
            error_msg = response.json().get("error", "Unknown error")
            print(f"❌ FAILED: {action} - {error_msg}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def get_history():
    """Get transaction history"""
    try:
        response = requests.get(f"{BASE_URL}/history/{BATCH_ID}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("history", [])
    except:
        pass
    return []


def test_correct_sequence():
    """Test 1: Correct sequential order (should succeed)"""
    print_section("TEST 1: Correct Sequential Order ✅")

    steps = [
        ("registered", "Supplier_A", {"product": "Laptop", "quantity": 100}),
        ("quality_checked", "Supplier_A", {"result": "Passed", "inspector": "QC_Team"}),
        ("shipped", "Supplier_A", {"from": "Supplier_A", "to": "Distributor_B"}),
        ("received", "Distributor_B", {"from": "Supplier_A"}),
        ("stored", "Distributor_B", {"location": "Warehouse_North"}),
        ("delivered", "Distributor_B", {"retailer": "Retailer_C"}),
        ("received_retail", "Retailer_C", {"from": "Distributor_B"}),
        ("sold", "Retailer_C", {"customer": "Customer_001", "date": "2025-01-15"})
    ]

    for i, (action, actor, metadata) in enumerate(steps, 1):
        print(f"Step {i}: {action}")
        result = send_transaction(action, actor, metadata)
        if not result:
            print(f"\n⚠️  TEST FAILED at step {i}")
            return False
        time.sleep(0.5)

    print(f"\n✅ All 8 steps completed successfully!")
    return True


def test_skip_step():
    """Test 2: Try to skip a step (should fail)"""
    print_section("TEST 2: Skip Step (should FAIL) ❌")

    batch_id = "BATCH_TEST_002"

    # Step 1: Register product
    print("Step 1: Registering product...")
    payload = {
        "batch_id": batch_id,
        "action": "registered",
        "actor": "Supplier_A",
        "metadata": {"product": "Phone", "quantity": 50}
    }
    requests.post(f"{BASE_URL}/add-transaction", json=payload)
    time.sleep(0.5)

    # Step 2: Try to SHIP without quality check (should FAIL)
    print("\nStep 2: Attempting to SHIP without quality check...")
    payload = {
        "batch_id": batch_id,
        "action": "shipped",  # Skipping quality_checked
        "actor": "Supplier_A",
        "metadata": {"from": "Supplier_A", "to": "Distributor_B"}
    }

    response = requests.post(f"{BASE_URL}/add-transaction", json=payload)

    if response.status_code == 400:
        error = response.json().get("error", "")
        print(f"❌ Transaction correctly REJECTED: {error}")
        print("✅ TEST PASSED: System prevents skipping steps")
        return True
    else:
        print(f"⚠️  TEST FAILED: Transaction was accepted (should have been rejected)")
        return False


def test_out_of_order():
    """Test 3: Try to perform steps out of order (should fail)"""
    print_section("TEST 3: Out of Order Steps (should FAIL) ❌")

    batch_id = "BATCH_TEST_003"

    # Try to start with Step 5 (stored) without any previous steps
    print("Attempting to STORE without any previous steps...")
    payload = {
        "batch_id": batch_id,
        "action": "stored",
        "actor": "Distributor_B",
        "metadata": {"location": "Warehouse_South"}
    }

    response = requests.post(f"{BASE_URL}/add-transaction", json=payload)

    if response.status_code == 400:
        error = response.json().get("error", "")
        print(f"❌ Transaction correctly REJECTED: {error}")
        print("✅ TEST PASSED: System prevents out-of-order execution")
        return True
    else:
        print(f"⚠️  TEST FAILED: Transaction was accepted (should have been rejected)")
        return False


def test_duplicate_step():
    """Test 4: Try to perform the same step twice (should fail)"""
    print_section("TEST 4: Duplicate Step (should FAIL) ❌")

    batch_id = "BATCH_TEST_004"

    # Step 1: Register product
    print("Step 1: Registering product...")
    payload = {
        "batch_id": batch_id,
        "action": "registered",
        "actor": "Supplier_A",
        "metadata": {"product": "Tablet", "quantity": 75}
    }
    requests.post(f"{BASE_URL}/add-transaction", json=payload)
    time.sleep(0.5)

    # Step 2: Try to register AGAIN (should FAIL)
    print("\nStep 2: Attempting to register the SAME batch again...")
    response = requests.post(f"{BASE_URL}/add-transaction", json=payload)

    if response.status_code == 400:
        error = response.json().get("error", "")
        print(f"❌ Transaction correctly REJECTED: {error}")
        print("✅ TEST PASSED: System prevents duplicate actions")
        return True
    else:
        print(f"⚠️  TEST FAILED: Duplicate was accepted (should have been rejected)")
        return False


def display_history():
    """Display transaction history"""
    print_section("Transaction History")

    history = get_history()

    if not history:
        print("No transactions found")
        return

    print(f"Batch ID: {BATCH_ID}")
    print(f"Total Transactions: {len(history)}\n")

    for i, tx in enumerate(history, 1):
        print(f"{i}. {tx['action']:<20} - {tx['actor']:<15} - {tx['timestamp']}")


def main():
    print("\n" + "=" * 60)
    print("  BLOCKCHAIN SEQUENTIAL ORDER VALIDATION TEST SUITE")
    print("=" * 60)

    # Check if blockchain is running
    try:
        response = requests.get(f"{BASE_URL}/status", timeout=5)
        if response.status_code != 200:
            print("\n❌ ERROR: Blockchain node not responding")
            print(f"   Make sure the node is running on {BASE_URL}")
            return
    except:
        print(f"\n❌ ERROR: Cannot connect to blockchain at {BASE_URL}")
        print("   Start the blockchain node first:")
        print("   python node.py --port 5000")
        return

    print("\n✅ Blockchain node is running")

    # Run tests
    results = []

    results.append(("Correct Sequential Order", test_correct_sequence()))
    time.sleep(1)

    results.append(("Skip Step Prevention", test_skip_step()))
    time.sleep(1)

    results.append(("Out of Order Prevention", test_out_of_order()))
    time.sleep(1)

    results.append(("Duplicate Prevention", test_duplicate_step()))
    time.sleep(1)

    # Display history
    display_history()

    # Summary
    print_section("TEST SUMMARY")
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:<30} {status}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\n{total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 ALL TESTS PASSED! Sequential order enforcement is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the implementation.")


if __name__ == "__main__":
    main()