import { useState } from 'react';
import { api } from '../api/api';

function StoreProduct() {
  const [formData, setFormData] = useState({
    BatchId: '',
    DistributorName: 'Distributor_B',
    WarehouseLocation: ''
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.store(formData);
      await api.mine(5001);

      setMessage('✅ Storage recorded and block mined!');
      setFormData({ BatchId: '', DistributorName: 'Distributor_B', WarehouseLocation: '' });
    } catch (error) {
      setMessage('❌ Failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h1>🏭 Store Product</h1>

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
          <label>Warehouse Location *</label>
          <input
            type="text"
            value={formData.WarehouseLocation}
            onChange={(e) => setFormData({ ...formData, WarehouseLocation: e.target.value })}
            required
            placeholder="e.g., WH-7"
          />
        </div>

        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? 'Recording...' : 'Record Storage'}
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

export default StoreProduct;