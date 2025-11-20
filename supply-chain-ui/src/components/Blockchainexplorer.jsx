import { useState, useEffect } from 'react';
import {
  Layers, Box, Hash, Clock, Shield,
  AlertCircle, CheckCircle, ChevronDown,
  ChevronUp, RefreshCw, Database, Link as LinkIcon
} from 'lucide-react';

import { api } from '../api/api';   // <-- USE FAILOVER API

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
    const interval = setInterval(loadBlockchain, 30000);
    return () => clearInterval(interval);
  }, []);

  // -------------------------------------------------
  // LOAD DATA THROUGH FAILOVER API
  // -------------------------------------------------
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

  const expandAll = () => setExpandedBlocks(new Set(chain.map((_, i) => i)));
  const collapseAll = () => setExpandedBlocks(new Set());

  const formatHash = (hash) =>
    (!hash || hash === '0') ? hash : `${hash.substring(0, 8)}...${hash.substring(hash.length - 8)}`;

  const formatTimestamp = (timestamp) => new Date(timestamp).toLocaleString();

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

  // -------------------------------------------------
  // RENDER UI
  // -------------------------------------------------
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
        <div className="stat-card"><Box size={28} /><p>Total Blocks</p><b>{stats.totalBlocks}</b></div>
        <div className="stat-card"><Database size={28} /><p>Total Tx</p><b>{stats.totalTransactions}</b></div>
        <div className="stat-card"><Clock size={28} /><p>Mempool</p><b>{stats.mempoolSize}</b></div>
        <div className="stat-card"><LinkIcon size={28} /><p>Chain Height</p><b>{stats.chainLength}</b></div>
      </div>

      {/* CONTROLS */}
      <div className="controls">
        <button onClick={expandAll} className="btn-secondary"><ChevronDown size={16} /> Expand All</button>
        <button onClick={collapseAll} className="btn-secondary"><ChevronUp size={16} /> Collapse All</button>
      </div>

      {/* MEMPOOL */}
      {mempool.length > 0 && (
        <div className="mempool-section">
          <h2><Clock size={24} /> Pending Transactions ({mempool.length})</h2>
          <div className="mempool-grid">
            {mempool.map((tx, i) => (
              <div key={i} className="mempool-tx">
                <div className="tx-header">
                  <span className="tx-icon">{getActionIcon(tx.action)}</span>
                  <strong>{tx.action}</strong>
                </div>
                <p><b>Batch:</b> {tx.batch_id}</p>
                <p><b>Actor:</b> {tx.actor}</p>
                <p><b>Time:</b> {formatTimestamp(tx.timestamp)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CHAIN */}
      <div className="blockchain-section">
        <h2><Layers size={24} /> Complete Blockchain</h2>

        <div className="chain-container">
          {chain.map((block, idx) => (
            <div key={idx} className={`block-card ${block.index === 0 ? 'genesis' : ''}`}>

              <div className="block-header" onClick={() => toggleBlock(idx)}>
                <Box size={24} />
                <h3>{block.index === 0 ? 'Genesis Block' : `Block #${block.index}`}</h3>
                <span>{block.transactions.length} tx</span>
                <button className="expand-btn">
                  {expandedBlocks.has(idx) ? <ChevronUp /> : <ChevronDown />}
                </button>
              </div>

              {/* Summary */}
              <div className="block-summary">
                <p><b>Hash:</b> {formatHash(block.hash)}</p>
                <p><b>Prev:</b> {formatHash(block.previous_hash)}</p>
                <p><b>Time:</b> {formatTimestamp(block.timestamp)}</p>
                <p><b>Nonce:</b> {block.nonce}</p>
              </div>

              {/* Expanded details */}
              {expandedBlocks.has(idx) && (
                <div className="block-expanded">
                  <h4>Transactions</h4>
                  {block.transactions.map((tx, t) => (
                    <div key={t} className="transaction-card">
                      <strong>{tx.action}</strong> — {tx.batch_id}<br />
                      <b>Actor:</b> {tx.actor}<br />
                      <b>Time:</b> {formatTimestamp(tx.timestamp)}
                    </div>
                  ))}
                </div>
              )}

              {idx < chain.length - 1 && <div className="chain-link">↓ Linked</div>}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

export default BlockchainExplorer;
