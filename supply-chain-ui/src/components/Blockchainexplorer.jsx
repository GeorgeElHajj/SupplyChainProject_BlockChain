import { useState, useEffect } from 'react';
import {
  Layers,
  Box,
  Hash,
  Clock,
  Shield,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Database,
  Link as LinkIcon
} from 'lucide-react';
import axios from 'axios';

const BLOCKCHAIN_API = 'http://localhost:5000';

function BlockchainExplorer() {
  const [chain, setChain] = useState([]);
  const [mempool, setMempool] = useState([]);
  const [chainValid, setChainValid] = useState(true);
  const [validationMessage, setValidationMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [expandedBlocks, setExpandedBlocks] = useState(new Set());
  const [stats, setStats] = useState({
    totalBlocks: 0,
    totalTransactions: 0,
    mempoolSize: 0,
    chainLength: 0
  });

  useEffect(() => {
    loadBlockchain();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadBlockchain, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadBlockchain = async () => {
    setLoading(true);
    try {
      // Load full chain
      const chainResponse = await axios.get(`${BLOCKCHAIN_API}/chain`);
      const chainData = chainResponse.data;

      setChain(chainData.chain || []);
      setChainValid(chainData.valid);
      setValidationMessage(chainData.message);

      // Load mempool
      const mempoolResponse = await axios.get(`${BLOCKCHAIN_API}/mempool`);
      setMempool(mempoolResponse.data.mempool || []);

      // Calculate stats
      const totalTx = chainData.chain.reduce((sum, block) =>
        sum + (block.transactions?.length || 0), 0
      );

      setStats({
        totalBlocks: chainData.chain.length,
        totalTransactions: totalTx,
        mempoolSize: mempoolResponse.data.mempool.length,
        chainLength: chainData.chain.length
      });

    } catch (error) {
      console.error('Failed to load blockchain:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleBlock = (index) => {
    const newExpanded = new Set(expandedBlocks);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedBlocks(newExpanded);
  };

  const expandAll = () => {
    setExpandedBlocks(new Set(chain.map((_, i) => i)));
  };

  const collapseAll = () => {
    setExpandedBlocks(new Set());
  };

  const formatHash = (hash) => {
    if (!hash || hash === '0') return hash;
    return `${hash.substring(0, 8)}...${hash.substring(hash.length - 8)}`;
  };

  const formatTimestamp = (timestamp) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const getActionIcon = (action) => {
    const icons = {
      'registered': '📦',
      'quality_checked': '✓',
      'shipped': '🚚',
      'received': '📥',
      'stored': '🏪',
      'delivered': '🚛',
      'received_retail': '🏬',
      'sold': '💰'
    };
    return icons[action] || '📝';
  };

  if (loading) {
    return (
      <div className="blockchain-explorer">
        <div className="loading-container">
          <RefreshCw className="spin" size={48} />
          <p>Loading blockchain...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="blockchain-explorer">
      {/* Header */}
      <div className="explorer-header">
        <div className="header-title">
          <Layers size={32} />
          <div>
            <h1>🔗 Blockchain Explorer</h1>
            <p>Full chain view with transaction details</p>
          </div>
        </div>
        <button onClick={loadBlockchain} className="btn-refresh">
          <RefreshCw size={18} /> Refresh
        </button>
      </div>

      {/* Chain Status */}
      <div className="chain-status">
        {chainValid ? (
          <div className="status-card valid">
            <CheckCircle size={24} />
            <div>
              <h3>Chain Valid ✅</h3>
              <p>{validationMessage}</p>
            </div>
          </div>
        ) : (
          <div className="status-card invalid">
            <AlertCircle size={24} />
            <div>
              <h3>Chain Invalid ❌</h3>
              <p>{validationMessage}</p>
            </div>
          </div>
        )}
      </div>

      {/* Statistics */}
      <div className="stats-grid">
        <div className="stat-card">
          <Box size={28} />
          <div>
            <p className="stat-label">Total Blocks</p>
            <p className="stat-value">{stats.totalBlocks}</p>
          </div>
        </div>
        <div className="stat-card">
          <Database size={28} />
          <div>
            <p className="stat-label">Total Transactions</p>
            <p className="stat-value">{stats.totalTransactions}</p>
          </div>
        </div>
        <div className="stat-card">
          <Clock size={28} />
          <div>
            <p className="stat-label">Pending (Mempool)</p>
            <p className="stat-value">{stats.mempoolSize}</p>
          </div>
        </div>
        <div className="stat-card">
          <LinkIcon size={28} />
          <div>
            <p className="stat-label">Chain Height</p>
            <p className="stat-value">{stats.chainLength}</p>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="controls">
        <button onClick={expandAll} className="btn-secondary">
          <ChevronDown size={16} /> Expand All
        </button>
        <button onClick={collapseAll} className="btn-secondary">
          <ChevronUp size={16} /> Collapse All
        </button>
      </div>

      {/* Mempool Section */}
      {mempool.length > 0 && (
        <div className="mempool-section">
          <h2>
            <Clock size={24} />
            Pending Transactions (Mempool) - {mempool.length}
          </h2>
          <div className="mempool-grid">
            {mempool.map((tx, idx) => (
              <div key={idx} className="mempool-tx">
                <div className="tx-header">
                  <span className="tx-icon">{getActionIcon(tx.action)}</span>
                  <div>
                    <strong>{tx.action}</strong>
                    <span className="tx-batch">Batch: {tx.batch_id}</span>
                  </div>
                </div>
                <div className="tx-details">
                  <p><strong>Actor:</strong> {tx.actor}</p>
                  <p><strong>Time:</strong> {formatTimestamp(tx.timestamp)}</p>
                  {tx.signature && (
                    <div className="signature-badge">
                      <Shield size={14} /> Signed
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Blockchain */}
      <div className="blockchain-section">
        <h2>
          <Layers size={24} />
          Complete Blockchain - {chain.length} Blocks
        </h2>

        <div className="chain-container">
          {chain.map((block, index) => {
            const isExpanded = expandedBlocks.has(index);
            const isGenesis = block.index === 0;

            return (
              <div key={index} className={`block-card ${isGenesis ? 'genesis' : ''}`}>
                {/* Block Header */}
                <div className="block-header" onClick={() => toggleBlock(index)}>
                  <div className="block-title">
                    <Box size={24} />
                    <div>
                      <h3>
                        {isGenesis ? '🏛️ Genesis Block' : `Block #${block.index}`}
                      </h3>
                      <span className="block-tx-count">
                        {block.transactions.length} transaction{block.transactions.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>
                  <button className="expand-btn">
                    {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                  </button>
                </div>

                {/* Block Details (Always Visible) */}
                <div className="block-summary">
                  <div className="summary-item">
                    <Hash size={16} />
                    <div>
                      <span className="label">Hash</span>
                      <code className="hash">{formatHash(block.hash)}</code>
                    </div>
                  </div>
                  <div className="summary-item">
                    <LinkIcon size={16} />
                    <div>
                      <span className="label">Previous Hash</span>
                      <code className="hash">{formatHash(block.previous_hash)}</code>
                    </div>
                  </div>
                  <div className="summary-item">
                    <Clock size={16} />
                    <div>
                      <span className="label">Timestamp</span>
                      <span>{formatTimestamp(block.timestamp)}</span>
                    </div>
                  </div>
                  <div className="summary-item">
                    <Database size={16} />
                    <div>
                      <span className="label">Nonce</span>
                      <span>{block.nonce}</span>
                    </div>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="block-expanded">
                    {/* Full Hashes */}
                    <div className="full-hashes">
                      <div className="hash-item">
                        <strong>Full Hash:</strong>
                        <code className="full-hash">{block.hash}</code>
                      </div>
                      <div className="hash-item">
                        <strong>Previous Hash:</strong>
                        <code className="full-hash">{block.previous_hash}</code>
                      </div>
                    </div>

                    {/* Transactions */}
                    {block.transactions.length > 0 ? (
                      <div className="transactions-section">
                        <h4>📦 Transactions ({block.transactions.length})</h4>
                        <div className="transactions-list">
                          {block.transactions.map((tx, txIdx) => (
                            <div key={txIdx} className="transaction-card">
                              <div className="tx-header">
                                <span className="tx-number">#{txIdx + 1}</span>
                                <span className="tx-icon-large">{getActionIcon(tx.action)}</span>
                                <div className="tx-info">
                                  <h5>{tx.action}</h5>
                                  <span className="tx-batch-id">{tx.batch_id}</span>
                                </div>
                                {tx.signature && (
                                  <div className="signature-badge verified">
                                    <Shield size={14} /> Verified
                                  </div>
                                )}
                              </div>

                              <div className="tx-body">
                                <div className="tx-field">
                                  <strong>Actor:</strong>
                                  <span>{tx.actor}</span>
                                </div>
                                <div className="tx-field">
                                  <strong>Timestamp:</strong>
                                  <span>{formatTimestamp(tx.timestamp)}</span>
                                </div>
                                <div className="tx-field">
                                  <strong>Metadata:</strong>
                                  <div className="metadata">
                                    {Object.entries(tx.metadata || {}).map(([key, value]) => (
                                      <div key={key} className="metadata-item">
                                        <span className="key">{key}:</span>
                                        <span className="value">{JSON.stringify(value)}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>

                                {tx.signature && (
                                  <details className="signature-details">
                                    <summary>🔐 View Signature</summary>
                                    <div className="signature-content">
                                      <p><strong>Signature:</strong></p>
                                      <code className="signature-code">
                                        {tx.signature.substring(0, 64)}...
                                      </code>
                                      {tx.public_key && (
                                        <>
                                          <p><strong>Public Key:</strong></p>
                                          <code className="signature-code">
                                            {tx.public_key.substring(0, 64)}...
                                          </code>
                                        </>
                                      )}
                                    </div>
                                  </details>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="no-transactions">
                        <Database size={32} />
                        <p>No transactions in this block</p>
                      </div>
                    )}

                    {/* Raw Block Data */}
                    <details className="raw-data">
                      <summary>🔍 View Raw Block Data (JSON)</summary>
                      <pre className="json-viewer">
                        {JSON.stringify(block, null, 2)}
                      </pre>
                    </details>
                  </div>
                )}

                {/* Chain Link Arrow */}
                {index < chain.length - 1 && (
                  <div className="chain-link">
                    <div className="arrow-down">↓</div>
                    <span className="link-text">Linked by hash</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default BlockchainExplorer;