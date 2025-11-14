#!/bin/bash
# test_complete_system.sh - Test entire supply chain system
# Blockchain nodes: 5000, 5001, 5002
# APIs: Supplier=5175, Distributor=5137, Retailer=5112

echo "╔══════════════════════════════════════════════════════════╗"
echo "║     SUPPLY CHAIN BLOCKCHAIN - COMPLETE SYSTEM TEST       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC} - $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC} - $2"
        ((TESTS_FAILED++))
    fi
}

# Function to make HTTP request and check response
http_test() {
    local url=$1
    local method=$2
    local data=$3
    local expected_code=$4

    if [ "$method" = "GET" ]; then
        response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    else
        response=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" \
                   -H "Content-Type: application/json" \
                   -d "$data" "$url" 2>/dev/null)
    fi

    if [ "$response" = "$expected_code" ]; then
        return 0
    else
        return 1
    fi
}

echo "============================================================"
echo "  PHASE 1: BLOCKCHAIN NODES HEALTH CHECK"
echo "============================================================"
echo ""

echo "Testing Node 1 (Port 5000)..."
http_test "http://localhost:5000/status" "GET" "" "200"
test_result $? "Blockchain Node 1 is running"

echo "Testing Node 2 (Port 5001)..."
http_test "http://localhost:5001/status" "GET" "" "200"
test_result $? "Blockchain Node 2 is running"

echo "Testing Node 3 (Port 5002)..."
http_test "http://localhost:5002/status" "GET" "" "200"
test_result $? "Blockchain Node 3 is running"

echo ""
echo "============================================================"
echo "  PHASE 2: API SERVICES HEALTH CHECK"
echo "============================================================"
echo ""

echo "Testing Supplier API (Port 5175)..."
http_test "http://localhost:5175/api/supplier/health" "GET" "" "200"
test_result $? "Supplier API is running"

echo "Testing Distributor API (Port 5137)..."
http_test "http://localhost:5137/api/distributor/health" "GET" "" "200"
test_result $? "Distributor API is running"

echo "Testing Retailer API (Port 5112)..."
http_test "http://localhost:5112/api/retailer/health" "GET" "" "200"
test_result $? "Retailer API is running"

echo ""
echo "============================================================"
echo "  PHASE 3: BLOCKCHAIN NETWORK CONNECTIVITY"
echo "============================================================"
echo ""

echo "Waiting for peer discovery..."
for i in {1..10}; do
    PEERS_NODE1=$(curl -s http://localhost:5000/nodes 2>/dev/null | jq '.count')
    if [ "$PEERS_NODE1" -ge 2 ]; then
        break
    fi
    sleep 1
done

echo "Checking peer discovery..."
if [ "$PEERS_NODE1" -ge 2 ]; then
    test_result 0 "Node 1 has discovered peers ($PEERS_NODE1 peers found)"
else
    test_result 1 "Node 1 peer discovery issue (has $PEERS_NODE1 peers, expected 2)"
fi


echo "Checking chain synchronization..."
CHAIN1=$(curl -s http://localhost:5000/chain 2>/dev/null | grep -o '"length":[0-9]*' | grep -o '[0-9]*')
CHAIN2=$(curl -s http://localhost:5001/chain 2>/dev/null | grep -o '"length":[0-9]*' | grep -o '[0-9]*')
CHAIN3=$(curl -s http://localhost:5002/chain 2>/dev/null | grep -o '"length":[0-9]*' | grep -o '[0-9]*')

if [ "$CHAIN1" = "$CHAIN2" ] && [ "$CHAIN2" = "$CHAIN3" ]; then
    test_result 0 "All nodes have synchronized chains (length: $CHAIN1)"
else
    test_result 1 "Chain sync issue (Node1:$CHAIN1, Node2:$CHAIN2, Node3:$CHAIN3)"
fi

echo ""
echo "============================================================"
echo "  PHASE 4: SUPPLY CHAIN WORKFLOW TEST"
echo "============================================================"
echo ""

# Generate unique batch ID
BATCH_ID="BATCH_TEST_$(date +%s)"
echo -e "${BLUE}Testing with Batch ID: $BATCH_ID${NC}"
echo ""

# Step 1: Register Product
echo "Step 1: Supplier registers product..."
STEP1_DATA='{
  "batchId": "'$BATCH_ID'",
  "supplier": "Supplier_A",
  "productName": "Test_Laptops",
  "quantity": 50
}'

http_test "http://localhost:5175/api/supplier/add-product" "POST" "$STEP1_DATA" "200"
test_result $? "Product registration"
sleep 2

# Step 2: Quality Check
echo "Step 2: Supplier performs quality check..."
STEP2_DATA='{
  "batchId": "'$BATCH_ID'",
  "supplierName": "Supplier_A",
  "result": "passed",
  "inspector": "QA_Team_Alpha"
}'

http_test "http://localhost:5175/api/supplier/quality-check" "POST" "$STEP2_DATA" "200"
test_result $? "Quality check"
sleep 2

# Step 3: Ship to Distributor
echo "Step 3: Supplier ships to distributor..."
STEP3_DATA='{
  "batchId": "'$BATCH_ID'",
  "supplierName": "Supplier_A",
  "distributorName": "Distributor_B"
}'

http_test "http://localhost:5175/api/supplier/ship" "POST" "$STEP3_DATA" "200"
test_result $? "Shipment to distributor"
sleep 2

# Mine block after supplier actions
echo ""
echo -e "${YELLOW}Mining block for supplier transactions...${NC}"
curl -s -X POST http://localhost:5000/mine > /dev/null 2>&1
sleep 3

# Step 4: Distributor receives
echo "Step 4: Distributor receives shipment..."
STEP4_DATA='{
  "batchId": "'$BATCH_ID'",
  "distributorName": "Distributor_B",
  "supplierName": "Supplier_A"
}'

http_test "http://localhost:5137/api/distributor/receive" "POST" "$STEP4_DATA" "200"
test_result $? "Distributor receives shipment"
sleep 2

# Step 5: Store in warehouse
echo "Step 5: Distributor stores in warehouse..."
STEP5_DATA='{
  "batchId": "'$BATCH_ID'",
  "distributorName": "Distributor_B",
  "warehouseLocation": "Warehouse_7"
}'

http_test "http://localhost:5137/api/distributor/store" "POST" "$STEP5_DATA" "200"
test_result $? "Store in warehouse"
sleep 2

# Step 6: Deliver to Retailer
echo "Step 6: Distributor delivers to retailer..."
STEP6_DATA='{
  "batchId": "'$BATCH_ID'",
  "distributorName": "Distributor_B",
  "retailerName": "Retailer_C"
}'

http_test "http://localhost:5137/api/distributor/deliver" "POST" "$STEP6_DATA" "200"
test_result $? "Delivery to retailer"
sleep 2

# Mine block after distributor actions
echo ""
echo -e "${YELLOW}Mining block for distributor transactions...${NC}"
curl -s -X POST http://localhost:5001/mine > /dev/null 2>&1
sleep 3

# Step 7: Retailer receives
echo "Step 7: Retailer receives product..."
STEP7_DATA='{
  "batchId": "'$BATCH_ID'",
  "retailerName": "Retailer_C",
  "distributorName": "Distributor_B"
}'

http_test "http://localhost:5112/api/retailer/receive" "POST" "$STEP7_DATA" "200"
test_result $? "Retailer receives product"
sleep 2

# Step 8: Sell to customer
echo "Step 8: Retailer sells to customer..."
STEP8_DATA='{
  "batchId": "'$BATCH_ID'",
  "retailerName": "Retailer_C",
  "customerName": "John_Doe",
  "saleDate": "'$(date +%Y-%m-%d)'"
}'

http_test "http://localhost:5112/api/retailer/sold" "POST" "$STEP8_DATA" "200"
test_result $? "Sale to customer"
sleep 2

# Mine block after retailer actions
echo ""
echo -e "${YELLOW}Mining block for retailer transactions...${NC}"
curl -s -X POST http://localhost:5002/mine > /dev/null 2>&1
sleep 3

echo ""
echo "============================================================"
echo "  PHASE 5: DATA VERIFICATION"
echo "============================================================"
echo ""

# Wait for chain sync
echo "Waiting for chain synchronization..."
sleep 5

# Check transaction history
echo "Verifying transaction history..."
HISTORY_RESPONSE=$(curl -s "http://localhost:5175/api/supplier/history/$BATCH_ID" 2>/dev/null)

if echo "$HISTORY_RESPONSE" | grep -q "$BATCH_ID"; then
    TRANSACTION_COUNT=$(echo "$HISTORY_RESPONSE" | grep -o "registered\|quality_checked\|shipped\|received\|stored\|delivered\|received_retail\|sold" | wc -l)

    if [ "$TRANSACTION_COUNT" -ge 7 ]; then
        test_result 0 "Transaction history retrieved ($TRANSACTION_COUNT transactions)"
    else
        test_result 1 "Incomplete transaction history (found $TRANSACTION_COUNT, expected 8)"
    fi
else
    test_result 1 "Transaction history not found"
fi

# Verify product authenticity
echo "Verifying product authenticity..."
VERIFY_RESPONSE=$(curl -s "http://localhost:5112/api/retailer/verify/$BATCH_ID" 2>/dev/null)

if echo "$VERIFY_RESPONSE" | grep -q "verified"; then
    test_result 0 "Product authenticity verified"
else
    test_result 1 "Product verification failed"
fi

# Check final chain state
echo "Checking final blockchain state..."
FINAL_CHAIN1=$(curl -s http://localhost:5000/chain 2>/dev/null | grep -o '"length":[0-9]*' | grep -o '[0-9]*')
FINAL_CHAIN2=$(curl -s http://localhost:5001/chain 2>/dev/null | grep -o '"length":[0-9]*' | grep -o '[0-9]*')
FINAL_CHAIN3=$(curl -s http://localhost:5002/chain 2>/dev/null | grep -o '"length":[0-9]*' | grep -o '[0-9]*')

if [ "$FINAL_CHAIN1" = "$FINAL_CHAIN2" ] && [ "$FINAL_CHAIN2" = "$FINAL_CHAIN3" ]; then
    test_result 0 "Final chain synchronization (all nodes at length $FINAL_CHAIN1)"
else
    test_result 1 "Final chain sync mismatch (Node1:$FINAL_CHAIN1, Node2:$FINAL_CHAIN2, Node3:$FINAL_CHAIN3)"
fi

echo ""
echo "============================================================"
echo "  TEST RESULTS SUMMARY"
echo "============================================================"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))

echo -e "Total Tests: ${BLUE}$TOTAL_TESTS${NC}"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "Pass Rate: ${YELLOW}$PASS_RATE%${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  🎉 ALL TESTS PASSED! SYSTEM FULLY OPERATIONAL! 🎉  ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ⚠️  SOME TESTS FAILED - CHECK LOGS ABOVE  ⚠️       ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════╝${NC}"
    exit 1
fi