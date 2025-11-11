import {useEffect, useState} from 'react';
import { api } from '../api/api';
import { useActors } from '../hooks/useActors';

function QualityCheck() {
  const { suppliers, loading: actorsLoading } = useActors();

  const [formData, setFormData] = useState({
    BatchId: '',
    Result: 'passed',
    Inspector: '',
    SupplierName: ''
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  // Set default supplier when loaded
  useEffect(() => {
    if (suppliers.length > 0 && !formData.SupplierName) {
      setFormData(prev => ({ ...prev, SupplierName: suppliers[0].value }));
    }
  }, [suppliers]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.qualityCheck(formData);
      await api.mine(5000);
      await new Promise(resolve => setTimeout(resolve, 3000));

      setMessage('✅ Quality check recorded and block mined!');
      setFormData({
        BatchId: '',
        Result: 'passed',
        Inspector: '',
        SupplierName: suppliers[0]?.value || ''
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
      <h1>✅ Quality Check</h1>

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
          <label>Result *</label>
          <select
            value={formData.Result}
            onChange={(e) => setFormData({ ...formData, Result: e.target.value })}
            required
          >
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        <div className="form-group">
          <label>Inspector *</label>
          <input
            type="text"
            value={formData.Inspector}
            onChange={(e) => setFormData({ ...formData, Inspector: e.target.value })}
            required
            placeholder="e.g., QA Team"
          />
        </div>

        <div className="form-group">
          <label>Supplier *</label>
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

        <button type="submit" disabled={loading || suppliers.length === 0} className="btn-primary">
          {loading ? 'Recording...' : 'Record Quality Check'}
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

export default QualityCheck;