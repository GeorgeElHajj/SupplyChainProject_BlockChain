# election.py - FIXED VERSION

import requests

MASTER_PRIORITY = [
    "blockchain1",
    "blockchain2",
    "blockchain3"
]


def detect_master(local_hostname, current_chain_length=None):
    """
    Returns hostname of current master node.
    Master is determined by:
    1. Longest valid chain (consensus-based)
    2. If chains are equal length, use priority order
    """

    node_scores = {}

    for idx, node in enumerate(MASTER_PRIORITY):
        if node == local_hostname:
            node_scores[node] = {
                'alive': True,
                'chain_length': current_chain_length if current_chain_length is not None else 0,
                'priority': idx
            }
            continue

        try:
            r = requests.get(f"http://{node}:5000/status", timeout=2)
            if r.status_code == 200:
                data = r.json()
                node_scores[node] = {
                    'alive': True,
                    'chain_length': data.get('chain_length', 0),
                    'priority': idx
                }
        except:
            node_scores[node] = {
                'alive': False,
                'chain_length': 0,
                'priority': idx
            }

    alive_nodes = {node: score for node, score in node_scores.items() if score['alive']}

    if not alive_nodes:
        return None

    # Sort by: 1) chain_length (DESC), 2) priority (ASC)
    sorted_nodes = sorted(
        alive_nodes.items(),
        key=lambda x: (-x[1]['chain_length'], x[1]['priority'])
    )

    master = sorted_nodes[0][0]

    print(f"🔍 Master election:")
    for node, score in sorted_nodes:
        marker = "👑" if node == master else "  "
        print(f"  {marker} {node}: chain_length={score['chain_length']}, priority={score['priority']}")

    return master