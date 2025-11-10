import { useState, useEffect } from 'react';
import { api } from '../api/api';
import { Package, CheckCircle, AlertCircle } from 'lucide-react';

function Dashboard() {
  const [chainInfo, setChainInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadChainInfo();
  }, []);

  const loadChainInfo = async () => {
    try {
      const response = await api.getChain();
      setChainInfo(response.data);
    } catch (error) {
      console.error('Failed to load chain:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="dashboard">
      <h1>Supply Chain Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <Package size={32} />
          <h3>Chain Length</h3>
          <p className="stat-value">{chainInfo?.length || 0}</p>
        </div>

        <div className="stat-card">
          <CheckCircle size={32} />
          <h3>Chain Status</h3>
          <p className="stat-value">{chainInfo?.valid ? '✅ Valid' : '❌ Invalid'}</p>
        </div>

        <div className="stat-card">
          <AlertCircle size={32} />
          <h3>Total Blocks</h3>
          <p className="stat-value">{chainInfo?.chain?.length || 0}</p>
        </div>
      </div>

      <div className="recent-blocks">
        <h2>Recent Blocks</h2>
        {chainInfo?.chain?.slice(-5).reverse().map((block, idx) => (
          <div key={idx} className="block-card">
            <h4>Block #{block.index}</h4>
            <p>Transactions: {block.transactions.length}</p>
            <p>Hash: {block.hash.substring(0, 20)}...</p>
            <p>Timestamp: {new Date(block.timestamp).toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;