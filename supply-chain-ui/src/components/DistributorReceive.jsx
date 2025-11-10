import { useState } from 'react';
import { api } from '../api/api';

function DistributorReceive() {
  const [formData, setFormData] = useState({
    BatchId: '',
    SupplierName: 'Supplier_A',
    DistributorName: 'Distributor_B'
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.receive(formData);
      await api.mine(5001);

      setMessage('✅ Reception recorded and block mined!');
      setFormData({ BatchId: '', SupplierName: 'Supplier_A', DistributorName: 'Distributor_B' });
    } catch (error) {
      setMessage('❌ Failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="form-container">
      <h1>📦 Distributor Receive</h1>

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
          <label>From Supplier *</label>
          <input
            type="text"
            value={formData.SupplierName}
            onChange={(e) => setFormData({ ...formData, SupplierName: e.target.value })}
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

export default DistributorReceive;