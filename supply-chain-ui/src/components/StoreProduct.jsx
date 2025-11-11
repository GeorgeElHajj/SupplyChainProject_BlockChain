import {useEffect, useState} from 'react';
import { api } from '../api/api';
import { useActors } from '../hooks/useActors';

function StoreProduct() {
  const { distributors, loading: actorsLoading } = useActors();

  const [formData, setFormData] = useState({
    BatchId: '',
    DistributorName: '',
    WarehouseLocation: ''
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Set default distributor when loaded
  useEffect(() => {
    if (distributors.length > 0 && !formData.DistributorName) {
      setFormData(prev => ({ ...prev, DistributorName: distributors[0].value }));
    }
  }, [distributors]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.store(formData);
      await api.mine(5001);
      await new Promise(resolve => setTimeout(resolve, 3000));

      setMessage('✅ Storage recorded and block mined!');
      setFormData({
        BatchId: '',
        DistributorName: distributors[0]?.value || '',
        WarehouseLocation: ''
      });
    } catch (error) {
      setMessage('❌ Failed: ' + (error.response?.data?.message || error.message));
    } finally {
      setLoading(false);
    }
  };

  if (actorsLoading) {
    return <div className="loading">Loading actors...</div>;
  }

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
            placeholder="e.g., BATCH_001"
          />
        </div>

        <div className="form-group">
          <label>Distributor *</label>
          <select
            value={formData.DistributorName}
            onChange={(e) => setFormData({ ...formData, DistributorName: e.target.value })}
            required
          >
            {distributors.length === 0 && <option value="">No distributors available</option>}
            {distributors.map(distributor => (
              <option key={distributor.value} value={distributor.value}>
                {distributor.label}
              </option>
            ))}
          </select>
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

        <button type="submit" disabled={loading || distributors.length === 0} className="btn-primary">
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