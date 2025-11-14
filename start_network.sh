#!/bin/bash
# start_network.sh - Launch a 3-node blockchain network

echo "🚀 Starting 3-Node Blockchain Network"
echo "======================================"
echo ""

# Clean up old database files (optional - comment out to persist data)
# rm -f blockchain_5000.db blockchain_5001.db blockchain_5002.db

# Start Node 1 (Bootstrap node - no peers)
echo "Starting Node 1 (Bootstrap) on port 5000..."
python blockchain_service.py --port 5000 --difficulty 2 > node1.log 2>&1 &
NODE1_PID=$!
echo "✅ Node 1 PID: $NODE1_PID"

# Wait for Node 1 to be ready
sleep 3

# Start Node 2 (connects to Node 1)
echo "Starting Node 2 on port 5001..."
python blockchain_service.py --port 5001 --difficulty 2 --bootstrap "http://localhost:5000" > node2.log 2>&1 &
NODE2_PID=$!
echo "✅ Node 2 PID: $NODE2_PID"

# Wait a bit
sleep 2

# Start Node 3 (connects to Node 1 and discovers Node 2)
echo "Starting Node 3 on port 5002..."
pythondi blockchain_service.py --port 5002 --difficulty 2 --bootstrap "http://localhost:5000" > node3.log 2>&1 &
NODE3_PID=$!
echo "✅ Node 3 PID: $NODE3_PID"

echo ""
echo "======================================"
echo "✅ All nodes started!"
echo "======================================"
echo "Node 1: http://localhost:5000 (PID: $NODE1_PID)"
echo "Node 2: http://localhost:5001 (PID: $NODE2_PID)"
echo "Node 3: http://localhost:5002 (PID: $NODE3_PID)"
echo ""
echo "📋 Logs:"
echo "  Node 1: tail -f node1.log"
echo "  Node 2: tail -f node2.log"
echo "  Node 3: tail -f node3.log"
echo ""
echo "🛑 To stop all nodes: ./stop_network.sh"
echo ""
echo "Saving PIDs to .node_pids file..."
echo "$NODE1_PID $NODE2_PID $NODE3_PID" > .node_pids