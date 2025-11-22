import { useState, useEffect } from 'react';
import {
  Layers, Box, Hash, Clock, Shield,
  AlertCircle, CheckCircle, ChevronDown,
  ChevronUp, RefreshCw, Database, Link as LinkIcon,
  Package, User, MapPin, Calendar, Key, FileText
} from 'lucide-react';

import { api } from '../api/api';

function BlockchainExplorer() {
  const [chain, setChain] = useState([]);
  const [mempool, setMempool] = useState([]);
  const [chainValid, setChainValid] = useState(true);
  const [validationMessage, setValidationMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [expandedBlocks, setExpandedBlocks] = useState(new Set());
  const [expandedTxs, setExpandedTxs] = useState(new Set());

  const [stats, setStats] = useState({
    totalBlocks: 0,
    totalTransactions: 0,
    mempoolSize: 0,
    chainLength: 0
  });

  useEffect(() => {
    loadBlockchain();
    const interval = setInterval(loadBlockchain, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadBlockchain = async () => {
    setLoading(true);
    try {
      const chainData = await api.getChain();
      const mempoolData = await api.getMempool();

      setChain(chainData.chain || []);
      setChainValid(chainData.valid);
      setValidationMessage(chainData.message);

      setMempool(mempoolData.mempool || []);

      const totalTx = (chainData.chain || []).reduce(
        (sum, block) => sum + (block.transactions?.length || 0), 0
      );

      setStats({
        totalBlocks: chainData.chain.length,
        totalTransactions: totalTx,
        mempoolSize: mempoolData.mempool.length,
        chainLength: chainData.chain.length
      });

    } catch (e) {
      console.error("Failed to load blockchain:", e);
    } finally {
      setLoading(false);
    }
  };

  const toggleBlock = (index) => {
    const newSet = new Set(expandedBlocks);
    newSet.has(index) ? newSet.delete(index) : newSet.add(index);
    setExpandedBlocks(newSet);
  };

  const toggleTx = (txId) => {
    const newSet = new Set(expandedTxs);
    newSet.has(txId) ? newSet.delete(txId) : newSet.add(txId);
    setExpandedTxs(newSet);
  };

  const expandAll = () => {
    setExpandedBlocks(new Set(chain.map((_, i) => i)));
    // Also expand all transactions
    const allTxIds = [];
    chain.forEach((block, blockIdx) => {
      block.transactions.forEach((_, txIdx) => {
        allTxIds.push(`${blockIdx}-${txIdx}`);
      });
    });
    setExpandedTxs(new Set(allTxIds));
  };

  const collapseAll = () => {
    setExpandedBlocks(new Set());
    setExpandedTxs(new Set());
  };

  const formatHash = (hash) =>
    (!hash || hash === '0') ? hash : `${hash.substring(0, 12)}...${hash.substring(hash.length - 12)}`;

  const formatFullHash = (hash) => hash || 'N/A';

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return timestamp;
    }
  };

  const getActionIcon = (action) => {
    const icons = {
      registered: '📦',
      quality_checked: '✓',
      shipped: '🚚',
      received: '📥',
      stored: '🏪',
      delivered: '🚛',
      received_retail: '🏬',
      sold: '💰'
    };
    return icons[action] || '📝';
  };

  const getActionColor = (action) => {
    const colors = {
      registered: '#4CAF50',
      quality_checked: '#2196F3',
      shipped: '#FF9800',
      received: '#9C27B0',
      stored: '#00BCD4',
      delivered: '#FF5722',
      received_retail: '#E91E63',
      sold: '#FFC107'
    };
    return colors[action] || '#757575';
  };

  const renderMetadata = (metadata) => {
    if (!metadata || Object.keys(metadata).length === 0) {
      return <p className="no-metadata">No metadata</p>;
    }

    return (
      <div className="metadata-grid">
        {Object.entries(metadata).map(([key, value]) => (
          <div key={key} className="metadata-item">
            <span className="metadata-key">{key}:</span>
            <span className="metadata-value">{String(value)}</span>
          </div>
        ))}
      </div>
    );
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
            <p>Complete chain view with transaction details</p>
          </div>
        </div>
        <button onClick={loadBlockchain} className="btn-refresh">
          <RefreshCw size={18} /> Refresh
        </button>
      </div>

      {/* CHAIN STATUS */}
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

      {/* STATS */}
      <div className="stats-grid">
        <div className="stat-card">
          <Box size={28} />
          <p>Total Blocks</p>
          <b>{stats.totalBlocks}</b>
        </div>
        <div className="stat-card">
          <Database size={28} />
          <p>Total Transactions</p>
          <b>{stats.totalTransactions}</b>
        </div>
        <div className="stat-card">
          <Clock size={28} />
          <p>Pending (Mempool)</p>
          <b>{stats.mempoolSize}</b>
        </div>
        <div className="stat-card">
          <LinkIcon size={28} />
          <p>Chain Height</p>
          <b>{stats.chainLength - 1}</b>
        </div>
      </div>

      {/* CONTROLS */}
      <div className="controls">
        <button onClick={expandAll} className="btn-secondary">
          <ChevronDown size={16} /> Expand All
        </button>
        <button onClick={collapseAll} className="btn-secondary">
          <ChevronUp size={16} /> Collapse All
        </button>
      </div>

      {/* CHAIN */}
      <div className="blockchain-section">
        <h2><Layers size={24} /> Complete Blockchain</h2>

        <div className="chain-container">
          {chain.map((block, blockIdx) => (
            <div key={blockIdx} className={`block-card ${block.index === 0 ? 'genesis' : ''}`}>

              {/* Block Header */}
              <div className="block-header" onClick={() => toggleBlock(blockIdx)}>
                <Box size={24} />
                <div className="block-title">
                  <h3>{block.index === 0 ? '🌟 Genesis Block' : `Block #${block.index}`}</h3>
                  <span className="block-txcount">{block.transactions.length} transaction{block.transactions.length !== 1 ? 's' : ''}</span>
                </div>
                <button className="expand-btn">
                  {expandedBlocks.has(blockIdx) ? <ChevronUp /> : <ChevronDown />}
                </button>
              </div>

              {/* Block Summary (Always Visible) */}
              <div className="block-summary">
                <div className="summary-row">
                  <Hash size={16} />
                  <div>
                    <b>Hash:</b>
                    <code className="hash-code">{formatHash(block.hash)}</code>
                  </div>
                </div>
                <div className="summary-row">
                  <LinkIcon size={16} />
                  <div>
                    <b>Previous Hash:</b>
                    <code className="hash-code">{formatHash(block.previous_hash)}</code>
                  </div>
                </div>
                <div className="summary-row">
                  <Calendar size={16} />
                  <div>
                    <b>Timestamp:</b>
                    <span>{formatTimestamp(block.timestamp)}</span>
                  </div>
                </div>
                <div className="summary-row">
                  <Database size={16} />
                  <div>
                    <b>Nonce:</b>
                    <span>{block.nonce.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* Expanded Block Details */}
              {expandedBlocks.has(blockIdx) && (
                <div className="block-expanded">

                  {/* Full Hashes */}
                  <div className="full-hashes">
                    <h4><Hash size={18} /> Full Hashes</h4>
                    <div className="hash-section">
                      <label>Current Hash:</label>
                      <code className="full-hash">{formatFullHash(block.hash)}</code>
                    </div>
                    <div className="hash-section">
                      <label>Previous Hash:</label>
                      <code className="full-hash">{formatFullHash(block.previous_hash)}</code>
                    </div>
                  </div>

                  {/* Transactions */}
                  <h4><Database size={18} /> Transactions ({block.transactions.length})</h4>

                  {block.transactions.length === 0 ? (
                    <p className="no-transactions">No transactions in this block</p>
                  ) : (
                    <div className="transactions-list">
                      {block.transactions.map((tx, txIdx) => {
                        const txId = `${blockIdx}-${txIdx}`;
                        const isExpanded = expandedTxs.has(txId);

                        return (
                          <div
                            key={txIdx}
                            className="transaction-card"
                            style={{ borderLeftColor: getActionColor(tx.action) }}
                          >
                            {/* Transaction Header */}
                            <div className="tx-card-header" onClick={() => toggleTx(txId)}>
                              <div className="tx-title">
                                <span className="tx-icon-large">{getActionIcon(tx.action)}</span>
                                <div>
                                  <strong>{tx.action.replace(/_/g, ' ').toUpperCase()}</strong>
                                  <span className="tx-batch-id">Batch: {tx.batch_id}</span>
                                </div>
                              </div>
                              <button className="tx-expand-btn">
                                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                              </button>
                            </div>

                            {/* Transaction Summary */}
                            <div className="tx-summary">
                              <div className="tx-info-row">
                                <User size={14} />
                                <span><b>Actor:</b> {tx.actor}</span>
                              </div>
                              <div className="tx-info-row">
                                <Calendar size={14} />
                                <span><b>Time:</b> {formatTimestamp(tx.timestamp)}</span>
                              </div>
                              {tx.signature && (
                                <div className="tx-info-row">
                                  <Shield size={14} />
                                  <span><b>Cryptographically Signed:</b> ✅</span>
                                </div>
                              )}
                            </div>

                            {/* Expanded Transaction Details */}
                            {isExpanded && (
                              <div className="tx-expanded">

                                {/* Metadata */}
                                {tx.metadata && (
                                  <div className="tx-section">
                                    <h5><FileText size={16} /> Transaction Metadata</h5>
                                    {renderMetadata(tx.metadata)}
                                  </div>
                                )}

                                {/* Signature Info */}
                                {tx.signature && (
                                  <div className="tx-section">
                                    <h5><Key size={16} /> Cryptographic Signature</h5>
                                    <div className="signature-info">
                                      <div className="signature-item">
                                        <label>Signature:</label>
                                        <code className="signature-code">
                                          {tx.signature.substring(0, 40)}...
                                        </code>
                                      </div>
                                      {tx.public_key && (
                                        <div className="signature-item">
                                          <label>Public Key:</label>
                                          <code className="signature-code">
                                            {tx.public_key.substring(0, 40)}...
                                          </code>
                                        </div>
                                      )}
                                      <div className="signature-status">
                                        <Shield size={16} className="verified" />
                                        <span>Signature Verified ✅</span>
                                      </div>
                                    </div>
                                  </div>
                                )}

                                {/* Raw Transaction Data */}
                                <div className="tx-section">
                                  <h5><Database size={16} /> Raw Transaction Data</h5>
                                  <pre className="raw-json">
                                    {JSON.stringify({
                                      action: tx.action,
                                      actor: tx.actor,
                                      batch_id: tx.batch_id,
                                      timestamp: tx.timestamp,
                                      metadata: tx.metadata,
                                      has_signature: !!tx.signature
                                    }, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Chain Link Indicator */}
              {blockIdx < chain.length - 1 && (
                <div className="chain-link">
                  <div className="link-line"></div>
                  <div className="link-text">
                    <LinkIcon size={14} />
                    <span>Cryptographically Linked</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

export default BlockchainExplorer;