import { useState } from 'react';
import { api } from '../api/api';

function AddProduct() {
  const [formData, setFormData] = useState({
    BatchId: '',
    ProductName: '',
    Quantity: '',
    Supplier: 'Supplier_A'
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      await api.addProduct({
        ...formData,
        Quantity: parseInt(formData.Quantity)
      });

      // Mine block
      await api.mine(5000);

      setMessage('✅ Product added and block mined successfully!');
      setFormData({ BatchId: '', ProductName: '', Quantity: '', Supplier: 'Supplier_A' });
    } catch (error) {
      setMessage('❌ Failed to add product: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

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
          <label>Supplier</label>
          <input
            type="text"
            value={formData.Supplier}
            onChange={(e) => setFormData({ ...formData, Supplier: e.target.value })}
            required
          />
        </div>

        <button type="submit" disabled={loading} className="btn-primary">
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