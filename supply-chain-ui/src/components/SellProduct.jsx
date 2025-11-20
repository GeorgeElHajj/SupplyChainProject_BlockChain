import {useEffect, useState} from 'react';
import { api } from '../api/api';
import { useActors } from '../hooks/useActors';

function SellProduct() {
  const { retailers, loading: actorsLoading } = useActors();

  const [formData, setFormData] = useState({
    BatchId: '',
    RetailerName: '',
    CustomerName: '',
    SaleDate: new Date().toISOString().split('T')[0]
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Set default retailer when loaded
  useEffect(() => {
    if (retailers.length > 0 && !formData.RetailerName) {
      setFormData(prev => ({ ...prev, RetailerName: retailers[0].value }));
    }
  }, [retailers]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.sell(formData);
      await api.mine();
      await new Promise(resolve => setTimeout(resolve, 3000));

      setMessage('✅ Sale recorded and block mined!');
      setFormData({
        BatchId: '',
        RetailerName: retailers[0]?.value || '',
        CustomerName: '',
        SaleDate: new Date().toISOString().split('T')[0]
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
      <h1>💰 Sell Product</h1>

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

        <div className="form-group">
          <label>Customer Name *</label>
          <input
            type="text"
            value={formData.CustomerName}
            onChange={(e) => setFormData({ ...formData, CustomerName: e.target.value })}
            required
            placeholder="e.g., John Doe"
          />
        </div>

        <div className="form-group">
          <label>Sale Date *</label>
          <input
            type="date"
            value={formData.SaleDate}
            onChange={(e) => setFormData({ ...formData, SaleDate: e.target.value })}
            required
          />
        </div>

        <button type="submit" disabled={loading || retailers.length === 0} className="btn-primary">
          {loading ? 'Recording...' : 'Record Sale'}
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

export default SellProduct;