import { useState } from 'react';
import { api } from '../api/api';
import Timeline from './Timeline';
import { Search, CheckCircle, XCircle, Package } from 'lucide-react';

function TrackBatch() {
  const [batchId, setBatchId] = useState('');
  const [history, setHistory] = useState(null);
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!batchId.trim()) return;

    setLoading(true);
    setError('');
    setHistory(null);
    setVerification(null);

    try {
      // Get history
     const historyResponse = await api.getBlockchainHistory(batchId);
setHistory(historyResponse);

const verifyResponse = await api.verifyBlockchainBatch(batchId);
setVerification(verifyResponse);

    } catch (err) {
      setError('Batch not found or error occurred');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="track-container">
      <h1>🔍 Track Batch</h1>

      <form onSubmit={handleSearch} className="search-form">
        <div className="search-input-group">
          <Search size={20} />
          <input
            type="text"
            value={batchId}
            onChange={(e) => setBatchId(e.target.value)}
            placeholder="Enter Batch ID (e.g., BATCH_001)"
            required
          />
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? 'Searching...' : 'Track'}
          </button>
        </div>
      </form>

      {error && (
        <div className="message error">
          <XCircle size={20} />
          {error}
        </div>
      )}

      {verification && (
        <div className="verification-card">
          <div className={`verification-status ${verification.verified ? 'verified' : 'unverified'}`}>
            {verification.verified ? (
              <>
                <CheckCircle size={32} />
                <h2>✅ Verified</h2>
                <p>This batch is authentic and verified on the blockchain</p>
              </>
            ) : (
              <>
                <XCircle size={32} />
                <h2>❌ Not Verified</h2>
                <p>This batch could not be verified or has no transactions</p>
              </>
            )}
          </div>

          <div className="batch-info">
            <h3>Batch Information</h3>
            <p><strong>Batch ID:</strong> {verification.batch_id}</p>
            <p><strong>Chain Status:</strong> {verification.message}</p>
            <p><strong>Total Events:</strong> {verification.events?.length || 0}</p>
          </div>
        </div>
      )}

      {history && history.history && history.history.length > 0 && (
        <div className="history-section">
          <h2>📋 Transaction History</h2>
          <Timeline events={history.history} />

          <div className="transactions-list">
            <h3>Detailed Transactions</h3>
            {history.history.map((event, idx) => (
              <div key={idx} className="transaction-card">
                <div className="transaction-header">
                  <Package size={20} />
                  <h4>{event.action.replace(/_/g, ' ').toUpperCase()}</h4>
                  {event.has_signature && (
                    <span className={`signature-badge ${event.signature_valid ? 'valid' : 'invalid'}`}>
                      {event.signature_valid ? '🔒 Signed' : '⚠️ Invalid Signature'}
                    </span>
                  )}
                </div>

                <div className="transaction-body">
                  <p><strong>Actor:</strong> {event.actor}</p>
                  <p><strong>Timestamp:</strong> {new Date(event.timestamp).toLocaleString()}</p>
                  <p><strong>Block Timestamp:</strong> {new Date(event.block_timestamp).toLocaleString()}</p>
                  <p><strong>Batch ID:</strong> {event.batch_id}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {history && (!history.history || history.history.length === 0) && (
        <div className="empty-state">
          <Package size={64} />
          <h3>No transactions found</h3>
          <p>This batch ID has no recorded transactions yet.</p>
        </div>
      )}
    </div>
  );
}

export default TrackBatch;