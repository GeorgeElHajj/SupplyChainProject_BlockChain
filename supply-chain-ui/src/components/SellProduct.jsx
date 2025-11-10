import { useState } from 'react';
import { api } from '../api/api';

function SellProduct() {
  const [formData, setFormData] = useState({
    BatchId: '',
    RetailerName: 'Retailer_C',
    CustomerName: '',
    SaleDate: new Date().toISOString().split('T')[0]
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.sell(formData);
      await api.mine(5002);

      setMessage('✅ Sale recorded and block mined!');
      setFormData({
        BatchId: '',
        RetailerName: 'Retailer_C',
        CustomerName: '',
        SaleDate: new Date().toISOString().split('T')[0]
      });
    } catch (error) {
      setMessage('❌ Failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

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

        <button type="submit" disabled={loading} className="btn-primary">
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