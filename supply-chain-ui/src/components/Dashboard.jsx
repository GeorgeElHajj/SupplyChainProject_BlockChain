import { useEffect, useState } from 'react';
import { api } from '../api/api';

function Dashboard() {
  const [chainInfo, setChainInfo] = useState({
    length: 0,
    valid: false,
    message: '',
    recentBlocks: []
  });
  const [nodeInfo, setNodeInfo] = useState({
    currentNode: 0,
    nodeHealth: [true, true, true]
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      // Load chain info
      const response = await api.getChain();
      const data = response.data || response;

      setChainInfo({
        length: data.length || 0,
        valid: data.valid || false,
        message: data.message || 'Unknown',
        recentBlocks: (data.chain || []).slice(-5).reverse()
      });

      // Load node info
      const currentNodeData = api.getCurrentNode();
      setNodeInfo({
        currentNode: currentNodeData.index,
        nodeHealth: currentNodeData.health
      });

      setLoading(false);
    } catch (error) {
      console.error('Failed to load chain:', error);
      setChainInfo({
        length: 0,
        valid: false,
        message: 'Failed to connect to blockchain',
        recentBlocks: []
      });
      setLoading(false);
    }
  };

  const getNodePort = (index) => {
    const ports = [5000, 5001, 5002];
    return ports[index];
  };

  if (loading) {
    return (
      <div className="dashboard-container">
        <h1>📊 Supply Chain Dashboard</h1>
        <div className="loading">Loading blockchain data...</div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <h1>📊 Supply Chain Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">🔗</div>
          <div className="stat-info">
            <h3>Chain Length</h3>
            <p className="stat-value">{chainInfo.length}</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            {chainInfo.valid ? '✅' : '❌'}
          </div>
          <div className="stat-info">
            <h3>Chain Status</h3>
            <p className={`stat-value ${chainInfo.valid ? 'valid' : 'invalid'}`}>
              {chainInfo.valid ? 'Valid' : 'Invalid'}
            </p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📦</div>
          <div className="stat-info">
            <h3>Total Blocks</h3>
            <p className="stat-value">{chainInfo.length}</p>
          </div>
        </div>
      </div>

      {/* Blockchain Nodes Status */}
      <div className="nodes-status">
        <h2>🖥️ Blockchain Nodes</h2>
        <div className="nodes-grid">
          {nodeInfo.nodeHealth.map((isHealthy, index) => (
            <div
              key={index}
              className={`node-card ${isHealthy ? 'healthy' : 'unhealthy'} ${index === nodeInfo.currentNode ? 'active' : ''}`}
            >
              <div className="node-header">
                <span className="node-name">Node {index}</span>
                {index === nodeInfo.currentNode && (
                  <span className="node-badge active-badge">ACTIVE</span>
                )}
              </div>
              <div className="node-body">
                <div className="node-info">
                  <span className="node-label">Port:</span>
                  <span className="node-value">{getNodePort(index)}</span>
                </div>
                <div className="node-info">
                  <span className="node-label">Status:</span>
                  <span className={`node-status ${isHealthy ? 'status-healthy' : 'status-down'}`}>
                    {isHealthy ? '🟢 Healthy' : '🔴 Down'}
                  </span>
                </div>
                <div className="node-info">
                  <span className="node-label">URL:</span>
                  <span className="node-value">localhost:{getNodePort(index)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="nodes-summary">
          <p>
            <strong>Active Nodes:</strong> {nodeInfo.nodeHealth.filter(h => h).length} / {nodeInfo.nodeHealth.length}
          </p>
          <p>
            <strong>Primary Node:</strong> Node {nodeInfo.currentNode} (Port {getNodePort(nodeInfo.currentNode)})
          </p>
        </div>
      </div>

      <div className="recent-blocks">
        <h2>Recent Blocks</h2>
        {chainInfo.recentBlocks.length === 0 ? (
          <p className="no-blocks">No blocks yet. Start by adding a product!</p>
        ) : (
          <div className="blocks-list">
            {chainInfo.recentBlocks.map((block, index) => (
              <div key={block.index || index} className="block-card">
                <div className="block-header">
                  <span className="block-index">Block #{block.index}</span>
                  <span className="block-timestamp">
                      {new Date(block.timestamp).toLocaleString()}
                  </span>
                </div>
                <div className="block-body">
                  <div className="block-info">
                    <strong>Hash:</strong>
                    <code className="hash">{block.hash?.substring(0, 16)}...</code>
                  </div>
                  <div className="block-info">
                    <strong>Previous:</strong>
                    <code className="hash">{block.previous_hash?.substring(0, 16)}...</code>
                  </div>
                  <div className="block-info">
                    <strong>Transactions:</strong>
                    <span className="transaction-count">{block.transactions?.length || 0}</span>
                  </div>
                  {block.transactions && block.transactions.length > 0 && (
                    <div className="transactions-preview">
                      {block.transactions.map((tx, txIndex) => (
                        <div key={txIndex} className="transaction-item">
                          <span className="tx-action">{tx.action}</span>
                          <span className="tx-actor">{tx.actor}</span>
                          <span className="tx-batch">{tx.batch_id}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="dashboard-actions">
        <button onClick={loadDashboardData} className="btn-secondary">
          🔄 Refresh
        </button>
      </div>
    </div>
  );
}

export default Dashboard;