import { useState } from 'react';
import { api } from '../api/api';

function DeliverToRetailer() {
  const [formData, setFormData] = useState({
    BatchId: '',
    DistributorName: 'Distributor_B',
    RetailerName: 'Retailer_C'
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.deliver(formData);
      await api.mine(5001);

      setMessage('✅ Delivery recorded and block mined!');
      setFormData({ BatchId: '', DistributorName: 'Distributor_B', RetailerName: 'Retailer_C' });
    } catch (error) {
      setMessage('❌ Failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h1>🚚 Deliver to Retailer</h1>

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
          <label>Distributor Name *</label>
          <input
            type="text"
            value={formData.DistributorName}
            onChange={(e) => setFormData({ ...formData, DistributorName: e.target.value })}
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

        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Recording...' : 'Record Delivery'}
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

export default DeliverToRetailer;