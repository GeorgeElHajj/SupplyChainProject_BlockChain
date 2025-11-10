#!/bin/bash
# stop_network.sh - Stop all blockchain nodes

echo "🛑 Stopping Blockchain Network"
echo "======================================"

if [ -f .node_pids ]; then
    PIDS=$(cat .node_pids)
    for PID in $PIDS; do
        if kill -0 $PID 2>/dev/null; then
            echo "Stopping process $PID..."
            kill $PID
        else
            echo "Process $PID not found"
        fi
    done
    rm .node_pids
    echo "✅ All nodes stopped"
else
    echo "⚠️  No .node_pids file found. Searching for python processes..."
    pkill -f "blockchain_service_v2.py"
    echo "✅ Killed all blockchain_service.py processes"
fi

echo "======================================"