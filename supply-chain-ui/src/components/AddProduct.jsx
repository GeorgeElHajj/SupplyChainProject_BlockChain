import {useEffect, useState} from 'react';
import { api } from '../api/api';
import { useActors } from '../hooks/useActors';

function AddProduct() {
  const { suppliers, loading: actorsLoading } = useActors();

  const [formData, setFormData] = useState({
    BatchId: '',
    ProductName: '',
    Quantity: '',
    Supplier: ''
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
console.log(formData);
 useEffect(() => {
    if (suppliers.length > 0 && !formData.Supplier) {
      setFormData(prev => ({ ...prev, Supplier: suppliers[0].value }));
    }
  }, [suppliers]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const payload = {
        BatchId: formData.BatchId,
        ProductName: formData.ProductName,
        Quantity: parseInt(formData.Quantity),
        Supplier: formData.Supplier
      };

      await api.addProduct(payload);
      await api.mine();
      await new Promise(resolve => setTimeout(resolve, 3000));

      setMessage('✅ Product added and block mined successfully!');
      setFormData({
        BatchId: '',
        ProductName: '',
        Quantity: '',
        Supplier: suppliers[0]?.value || ''
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
      <h1>📦 Add New Product</h1>

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
          <label>Product Name *</label>
          <input
            type="text"
            value={formData.ProductName}
            onChange={(e) => setFormData({ ...formData, ProductName: e.target.value })}
            required
            placeholder="e.g., Laptops"
          />
        </div>

        <div className="form-group">
          <label>Quantity *</label>
          <input
            type="number"
            value={formData.Quantity}
            onChange={(e) => setFormData({ ...formData, Quantity: e.target.value })}
            required
            min="1"
          />
        </div>

        <div className="form-group">
          <label>Supplier *</label>
          <select
            value={formData.Supplier}
            onChange={(e) => setFormData({ ...formData, Supplier: e.target.value })}
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
          {loading ? 'Adding...' : 'Add Product'}
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

export default AddProduct;