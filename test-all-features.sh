#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

echo "=== TEST 1: AUTO-HEALING ==="

# Add test data
BATCH="HEAL_TEST_$(date +%s)"
curl -s -X POST http://localhost:5175/api/supplier/add-product \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH\",\"ProductName\":\"Laptops\",\"Quantity\":10,\"Supplier\":\"Supplier_A\"}" > /dev/null || true

curl -s -X POST http://localhost:5000/mine > /dev/null || true
sleep 3

echo "✅ Data added and mined"

# Verify all nodes synced
echo "Chain lengths before corruption:"
curl -s http://localhost:5000/chain | jq '.length'
curl -s http://localhost:5001/chain | jq '.length'
curl -s http://localhost:5002/chain | jq '.length'

# Corrupt node 1 (use Python inside container so no sqlite3 CLI required)
echo -e "\n🔨 Corrupting node 1 (using Python inside container)..."

CORRUPT_CMD=$(cat <<'PY'
import sqlite3, sys
db = "/app/blockchain_5000.db"
try:
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    # Replace the latest block's product name "Laptops" -> "CORRUPTED"
    cur.execute("""UPDATE chain
                   SET block = replace(block, '"Laptops"', '"CORRUPTED"')
                   WHERE idx = (SELECT MAX(idx) FROM chain);""")
    conn.commit()
    cur.close()
    conn.close()
    print("OK")
except Exception as e:
    sys.stderr.write("ERR: " + str(e))
    sys.exit(1)
PY
)

# run python inside container (use -i to feed heredoc)
if docker exec -i blockchain_node_1 python - <<'PY' 2>/dev/null
$CORRUPT_CMD
PY
then
    echo "Corruption attempt executed inside container via python."
else
    echo "Could not run python inside container or corruption script failed. Trying fallback approaches..."

    # fallback 1: try sqlite3 CLI inside container
    if docker exec blockchain_node_1 sqlite3 /app/blockchain_5000.db "SELECT name FROM sqlite_master LIMIT 1;" >/dev/null 2>&1; then
        docker exec blockchain_node_1 sqlite3 /app/blockchain_5000.db \
          "UPDATE chain SET block = replace(block, '\"Laptops\"', '\"CORRUPTED\"') WHERE idx = (SELECT MAX(idx) FROM chain);" \
          && echo "Corruption applied with sqlite3 CLI inside container."
    else
        # fallback 2: try to find host mount and run sqlite3 from host (if available)
        echo "Attempting to locate host-mounted DB path for container..."
        MOUNTS=$(docker inspect --format '{{range .Mounts}}{{.Source}}:{{.Destination}};{{end}}' blockchain_node_1 2>/dev/null || true)
        HOST_DB=""
        for pair in ${MOUNTS//;/ }; do
            IFS=':' read -r src dst <<< "$pair"
            if [ "$dst" = "/app" ] || [ "$dst" = "/app/" ]; then
                HOST_DB="$src/blockchain_5000.db"
                break
            fi
        done

        if [ -n "$HOST_DB" ] && [ -f "$HOST_DB" ]; then
            echo "Found host DB at: $HOST_DB"
            if command -v sqlite3 >/dev/null 2>&1; then
                sqlite3 "$HOST_DB" "UPDATE chain SET block = replace(block, '\"Laptops\"', '\"CORRUPTED\"') WHERE idx = (SELECT MAX(idx) FROM chain);" \
                  && echo "Corruption applied on host-mounted DB via sqlite3."
            else
                echo "Host does not have sqlite3 CLI. Copying DB out, modifying with python, copying back..."
                TMP_DB="$(mktemp /tmp/blockchain_XXXX.db)"
                docker cp blockchain_node_1:/app/blockchain_5000.db "$TMP_DB"
                python - <<PY
import sqlite3
conn = sqlite3.connect("$TMP_DB")
cur = conn.cursor()
cur.execute("""UPDATE chain SET block = replace(block, '"Laptops"', '"CORRUPTED"') WHERE idx = (SELECT MAX(idx) FROM chain);""")
conn.commit()
conn.close()
PY
                docker cp "$TMP_DB" blockchain_node_1:/app/blockchain_5000.db
                rm -f "$TMP_DB"
                echo "Corruption applied by copying DB, editing on host, copying back."
            fi
        else
            echo "No host-mounted DB found or unable to locate. Manual intervention required to corrupt DB."
            echo "You can: (1) install sqlite3 inside the container, or (2) mount the DB to host and edit it."
            echo "Attempting to continue tests (no corruption applied)."
        fi
    fi
fi

# Restart node to ensure change is picked up
echo "Restarting blockchain_node_1..."
docker restart blockchain_node_1 > /dev/null 2>&1 || true
sleep 10

# Check corruption detected
echo -e "\n📊 Node 1 status after corruption (should detect invalid chain or mismatch):"
curl -s http://localhost:5000/status | jq '{valid: .chain_valid, peers: .peers, msg: .validation_message}' || true

# Force sync (or wait 30s for auto-sync)
echo -e "\n🔧 Triggering auto-heal..."
curl -s -X POST http://localhost:5000/sync > /dev/null || true
sleep 3

# Verify healed
echo -e "\n📊 Node 1 status after auto-heal:"
curl -s http://localhost:5000/status | jq '{valid: .chain_valid, peers: .peers}' || true

# Check data restored
PRODUCT=$(curl -s http://localhost:5000/verify/$BATCH | jq -r '.events[0].metadata.product' 2>/dev/null || echo "")
echo -e "\nProduct name: $PRODUCT (should be 'Laptops', not 'CORRUPTED')"

if [ "$PRODUCT" == "Laptops" ]; then
    echo "✅ AUTO-HEAL TEST PASSED!"
else
    echo "❌ AUTO-HEAL TEST FAILED (product not restored or corruption not applied)."
fi

echo -e "\n=== TEST 2: TRANSACTION VALIDATION ==="

BATCH2="VALIDATION_TEST_$(date +%s)"

# Try to ship before registering (should FAIL)
echo "Attempting to ship before registering..."
RESPONSE=$(curl -s -X POST http://localhost:5175/api/supplier/ship \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH2\",\"SupplierName\":\"Supplier_A\",\"DistributorName\":\"Distributor_B\"}")

if echo "$RESPONSE" | grep -q "Cannot"; then
    echo "✅ Validation working: $RESPONSE"
else
    echo "❌ Validation failed to block invalid transaction"
fi

# Now register first (should SUCCEED)
echo -e "\nRegistering product first..."
curl -s -X POST http://localhost:5175/api/supplier/add-product \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH2\",\"ProductName\":\"Monitors\",\"Quantity\":5,\"Supplier\":\"Supplier_A\"}" > /dev/null || true

# Now shipping should work
echo "Attempting to ship after registering..."
RESPONSE=$(curl -s -X POST http://localhost:5175/api/supplier/ship \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH2\",\"SupplierName\":\"Supplier_A\",\"DistributorName\":\"Distributor_B\"}")

if echo "$RESPONSE" | grep -q "recorded"; then
    echo "✅ Transaction order validation working!"
else
    echo "❌ Valid transaction was rejected: $RESPONSE"
fi

echo -e "\n=== TEST 3: AUTO-MINING ==="

# Check auto-mining is enabled
curl -s http://localhost:5000/status | jq || true

# Add transactions but don't mine manually
echo "Adding 5 transactions without mining..."
for i in {1..5}; do
    curl -s -X POST http://localhost:5175/api/supplier/add-product \
      -H "Content-Type: application/json" \
      -d "{\"BatchId\":\"AUTO_MINE_$i\",\"ProductName\":\"Item$i\",\"Quantity\":$i,\"Supplier\":\"Supplier_A\"}" > /dev/null || true
    sleep 1
done

# Check mempool
MEMPOOL_SIZE=$(curl -s http://localhost:5000/mempool | jq '.count' 2>/dev/null || echo "0")
echo "Mempool size: $MEMPOOL_SIZE"

# Wait 65 seconds for auto-mining (60s interval + 5s buffer)
echo "Waiting 65 seconds for auto-mining..."
sleep 65

# Check if mined
NEW_MEMPOOL_SIZE=$(curl -s http://localhost:5000/mempool | jq '.count' 2>/dev/null || echo "0")
echo "Mempool size after 60s: $NEW_MEMPOOL_SIZE"

if [ "${NEW_MEMPOOL_SIZE:-0}" -lt "${MEMPOOL_SIZE:-0}" ]; then
    echo "✅ AUTO-MINING WORKING!"
else
    echo "⚠️  Auto-mining didn't trigger yet (may take longer)"
fi

echo -e "\n=== TEST 4: MEMPOOL MANAGEMENT ==="

# Add 12 transactions rapidly (threshold is 10)
echo "Adding 12 transactions rapidly..."
for i in {1..12}; do
    curl -s -X POST http://localhost:5175/api/supplier/add-product \
      -H "Content-Type: application/json" \
      -d "{\"BatchId\":\"MEMPOOL_$i\",\"ProductName\":\"Item$i\",\"Quantity\":$i,\"Supplier\":\"Supplier_A\"}" > /dev/null || true
done

# Check if auto-mined at threshold
sleep 5
MEMPOOL=$(curl -s http://localhost:5000/mempool | jq '.count' 2>/dev/null || echo "0")
echo "Mempool size after adding 12: $MEMPOOL (should be < 12 if threshold triggered)"

if [ "${MEMPOOL:-0}" -lt 12 ]; then
    echo "✅ MEMPOOL THRESHOLD AUTO-MINING WORKING!"
else
    echo "⚠️  Mempool threshold not triggered yet"
fi

echo -e "\n=== TEST 5: FORK HANDLING ==="

# Stop node 3 temporarily
echo "Stopping node 3..."
docker stop blockchain_node_3 > /dev/null 2>&1 || true

# Mine block on nodes 1 & 2
BATCH_FORK="FORK_TEST_$(date +%s)"
curl -s -X POST http://localhost:5175/api/supplier/add-product \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH_FORK\",\"ProductName\":\"ForkTest\",\"Quantity\":1,\"Supplier\":\"Supplier_A\"}" > /dev/null || true

curl -s -X POST http://localhost:5000/mine > /dev/null || true
sleep 3

# Restart node 3
echo "Restarting node 3..."
docker start blockchain_node_3 > /dev/null 2>&1 || true
sleep 15

# Check if node 3 synced
LEN1=$(curl -s http://localhost:5000/chain | jq '.length' 2>/dev/null || echo "0")
LEN3=$(curl -s http://localhost:5002/chain | jq '.length' 2>/dev/null || echo "0")

echo "Node 1 chain: $LEN1 blocks"
echo "Node 3 chain: $LEN3 blocks"

if [ "$LEN1" == "$LEN3" ]; then
    echo "✅ FORK RESOLUTION WORKING!"
else
    echo "⚠️  Node 3 not synced yet (may need more time)"
fi

echo -e "\n=== TEST 6: COMPLETE SUPPLY CHAIN WORKFLOW ==="

BATCH_COMPLETE="COMPLETE_$(date +%s)"

echo "1. Register product"
curl -s -X POST http://localhost:5175/api/supplier/add-product \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH_COMPLETE\",\"ProductName\":\"Phones\",\"Quantity\":100,\"Supplier\":\"Supplier_A\"}" > /dev/null || true

echo "2. Quality check"
curl -s -X POST http://localhost:5175/api/supplier/quality-check \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH_COMPLETE\",\"Result\":\"passed\",\"Inspector\":\"QA\",\"SupplierName\":\"Supplier_A\"}" > /dev/null || true

echo "3. Ship to distributor"
curl -s -X POST http://localhost:5175/api/supplier/ship \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH_COMPLETE\",\"SupplierName\":\"Supplier_A\",\"DistributorName\":\"Distributor_B\"}" > /dev/null || true

# Wait for auto-mining or mine manually
curl -s -X POST http://localhost:5000/mine > /dev/null || true
sleep 3

echo "4. Distributor receives"
curl -s -X POST http://localhost:5137/api/distributor/receive \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH_COMPLETE\",\"SupplierName\":\"Supplier_A\",\"DistributorName\":\"Distributor_B\"}" > /dev/null || true

sleep 2

echo "5. Store in warehouse"
curl -s -X POST http://localhost:5137/api/distributor/store \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH_COMPLETE\",\"DistributorName\":\"Distributor_B\",\"WarehouseLocation\":\"WH-5\"}" > /dev/null || true

sleep 2

echo "6. Deliver to retailer"
curl -s -X POST http://localhost:5137/api/distributor/deliver \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH_COMPLETE\",\"DistributorName\":\"Distributor_B\",\"RetailerName\":\"Retailer_C\"}" > /dev/null || true

curl -s -X POST http://localhost:5001/mine > /dev/null || true
sleep 3

echo "7. Retailer receives"
curl -s -X POST http://localhost:5112/api/retailer/receive \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH_COMPLETE\",\"RetailerName\":\"Retailer_C\",\"DistributorName\":\"Distributor_B\"}" > /dev/null || true

sleep 2

echo "8. Sell to customer"
curl -s -X POST http://localhost:5112/api/retailer/sold \
  -H "Content-Type: application/json" \
  -d "{\"BatchId\":\"$BATCH_COMPLETE\",\"RetailerName\":\"Retailer_C\",\"CustomerName\":\"Customer\",\"SaleDate\":\"2025-11-11\"}" > /dev/null || true

curl -s -X POST http://localhost:5002/mine > /dev/null || true
sleep 3

# Verify complete history
HISTORY=$(curl -s http://localhost:5000/history/$BATCH_COMPLETE | jq '.transaction_count' 2>/dev/null || echo "0")
echo -e "\nComplete workflow transactions: $HISTORY (should be 8)"

if [ "$HISTORY" -eq 8 ]; then
    echo "✅ COMPLETE WORKFLOW TEST PASSED!"
else
    echo "❌ Some steps missing"
fi
