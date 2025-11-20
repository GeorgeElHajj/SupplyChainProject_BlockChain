import {useEffect, useState} from 'react';
import { api } from '../api/api';
import { useActors } from '../hooks/useActors';

function DistributorReceive() {
  const { suppliers, distributors, loading: actorsLoading } = useActors();

  const [formData, setFormData] = useState({
    BatchId: '',
    SupplierName: '',
    DistributorName: ''
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
console.log(formData);
  // Set defaults when loaded
  useEffect(() => {
    if (suppliers.length > 0 && distributors.length > 0) {
      if (!formData.SupplierName || !formData.DistributorName) {
        setFormData(prev => ({
          ...prev,
          SupplierName: suppliers[0].value,
          DistributorName: distributors[0].value
        }));
      }
    }
  }, [suppliers, distributors]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.receive(formData);
      await api.mine();
      await new Promise(resolve => setTimeout(resolve, 3000));

      setMessage('✅ Reception recorded and block mined!');
      setFormData({
        BatchId: '',
        SupplierName: suppliers[0]?.value || '',
        DistributorName: distributors[0]?.value || ''
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
      <h1>📦 Distributor Receive</h1>

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
          <label>From Supplier *</label>
          <select
            value={formData.SupplierName}
            onChange={(e) => setFormData({ ...formData, SupplierName: e.target.value })}
            required
          >
            {suppliers.length === 0 && <option value="">No suppliers available</option>}
            {suppliers.map(supplier => (
              <option key={supplier.value} value={supplier.value}>
                {supplier.label}
              </option>
            ))}
          </select>
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

        <button type="submit" disabled={loading || suppliers.length === 0 || distributors.length === 0} className="btn-primary">
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