import { useEffect, useState } from 'react';
import { api } from '../api/api';

function Dashboard() {
  const [chainInfo, setChainInfo] = useState({
    length: 0,
    valid: false,
    message: '',
    recentBlocks: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadChainInfo();
    const interval = setInterval(loadChainInfo, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const loadChainInfo = async () => {
    try {
      // The /chain endpoint returns { chain: [...], length: 1, valid: true, message: "..." }
      const response = await api.getChain();

      // Handle the response structure
      const data = response.data || response;

      setChainInfo({
        length: data.length || 0,
        valid: data.valid || false,
        message: data.message || 'Unknown',
        recentBlocks: (data.chain || []).slice(-5).reverse() // Last 5 blocks, newest first
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
        <button onClick={loadChainInfo} className="btn-secondary">
          🔄 Refresh
        </button>
      </div>
    </div>
  );
}

export default Dashboard;