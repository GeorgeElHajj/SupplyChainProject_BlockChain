import { useState, useEffect } from 'react';
import { api } from '../api/api';

export function useActors() {
  const [suppliers, setSuppliers] = useState([]);
  const [distributors, setDistributors] = useState([]);
  const [retailers, setRetailers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadActors();
  }, []);

  const loadActors = async () => {
    try {
      const [suppliersRes, distributorsRes, retailersRes] = await Promise.all([
        api.getActorsByRole('supplier'),
        api.getActorsByRole('distributor'),
        api.getActorsByRole('retailer')
      ]);

      setSuppliers(suppliersRes.data.actors.map(a => ({
        value: a.actor_name,
        label: a.username || a.actor_name
      })));

      setDistributors(distributorsRes.data.actors.map(a => ({
        value: a.actor_name,
        label: a.username || a.actor_name
      })));

      setRetailers(retailersRes.data.actors.map(a => ({
        value: a.actor_name,
        label: a.username || a.actor_name
      })));
    } catch (error) {
      console.error('Failed to load actors:', error);
      // Fallback to default actors
      setSuppliers([{ value: 'Supplier_A', label: 'Supplier A' }]);
      setDistributors([{ value: 'Distributor_A', label: 'Distributor A' }]);
      setRetailers([{ value: 'Retailer_A', label: 'Retailer A' }]);
    } finally {
      setLoading(false);
    }
  };

  return { suppliers, distributors, retailers, loading, reload: loadActors };
}