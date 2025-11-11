import {useEffect, useState} from 'react';
import { api } from '../api/api';
import { useActors } from '../hooks/useActors';

function DeliverToRetailer() {
  const { distributors, retailers, loading: actorsLoading } = useActors();

  const [formData, setFormData] = useState({
    BatchId: '',
    DistributorName: '',
    RetailerName: ''
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Set defaults when loaded
  useEffect(() => {
    if (distributors.length > 0 && retailers.length > 0) {
      if (!formData.DistributorName || !formData.RetailerName) {
        setFormData(prev => ({
          ...prev,
          DistributorName: distributors[0].value,
          RetailerName: retailers[0].value
        }));
      }
    }
  }, [distributors, retailers]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.deliver(formData);
      await api.mine(5001);
      await new Promise(resolve => setTimeout(resolve, 3000));

      setMessage('✅ Delivery recorded and block mined!');
      setFormData({
        BatchId: '',
        DistributorName: distributors[0]?.value || '',
        RetailerName: retailers[0]?.value || ''
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
      <h1>🚚 Deliver to Retailer</h1>

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
          <label>Retailer *</label>
          <select
            value={formData.RetailerName}
            onChange={(e) => setFormData({ ...formData, RetailerName: e.target.value })}
            required
          >
            {retailers.length === 0 && <option value="">No retailers available</option>}
            {retailers.map(retailer => (
              <option key={retailer.value} value={retailer.value}>
                {retailer.label}
              </option>
            ))}
          </select>
        </div>

        <button type="submit" disabled={loading || distributors.length === 0 || retailers.length === 0} className="btn-primary">
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