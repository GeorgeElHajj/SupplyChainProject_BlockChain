import { useState } from 'react';
import { api } from '../api/api';

function QualityCheck() {
  const [formData, setFormData] = useState({
    BatchId: '',
    Result: 'passed',
    Inspector: '',
    SupplierName: 'Supplier_A'
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.qualityCheck(formData);
      await api.mine(5000);

      setMessage('✅ Quality check recorded and block mined!');
      setFormData({ BatchId: '', Result: 'passed', Inspector: '', SupplierName: 'Supplier_A' });
    } catch (error) {
      setMessage('❌ Failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

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
          <label>Supplier Name</label>
          <input
            type="text"
            value={formData.SupplierName}
            onChange={(e) => setFormData({ ...formData, SupplierName: e.target.value })}
            required
          />
        </div>

        <button type="submit" disabled={loading} className="btn-primary">
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