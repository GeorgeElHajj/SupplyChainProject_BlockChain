import { useState } from 'react';
import { api } from '../api/api';

function RetailerReceive() {
  const [formData, setFormData] = useState({
    BatchId: '',
    RetailerName: 'Retailer_C',
    DistributorName: 'Distributor_B'
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.receiveRetail(formData);
      await api.mine(5002);

      setMessage('✅ Reception recorded and block mined!');
      setFormData({ BatchId: '', RetailerName: 'Retailer_C', DistributorName: 'Distributor_B' });
    } catch (error) {
      setMessage('❌ Failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h1>🏪 Retailer Receive</h1>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Batch ID *</label>
          <input
            type="text"
            value={formData.BatchId}
            onChange={(e) => setFormData({ ...formData, BatchId: e.target.value })}
            required
          />
        </div>

        <div className="form-group">
          <label>Retailer Name *</label>
          <input
            type="text"
            value={formData.RetailerName}
            onChange={(e) => setFormData({ ...formData, RetailerName: e.target.value })}
            required
          />
        </div>

        <div className="form-group">
          <label>From Distributor *</label>
          <input
            type="text"
            value={formData.DistributorName}
            onChange={(e) => setFormData({ ...formData, DistributorName: e.target.value })}
            required
          />
        </div>

        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Recording...' : 'Record Reception'}
        </button>
      </form>

      {message && (
        <div className={`message ${message.includes('✅') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}
    </div>
  );
}

export default RetailerReceive;