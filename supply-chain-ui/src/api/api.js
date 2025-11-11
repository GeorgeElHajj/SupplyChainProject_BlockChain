import axios from 'axios';

const SUPPLIER_API = 'http://localhost:5175/api/supplier';
const DISTRIBUTOR_API = 'http://localhost:5137/api/distributor';
const RETAILER_API = 'http://localhost:5112/api/retailer';
const BLOCKCHAIN_API = 'http://localhost:5000';
const ADMIN_API = 'http://localhost:5500/admin';

export const api = {
  // Supplier operations
  addProduct: (data) => axios.post(`${SUPPLIER_API}/add-product`, data),
  qualityCheck: (data) => axios.post(`${SUPPLIER_API}/quality-check`, data),
  ship: (data) => axios.post(`${SUPPLIER_API}/ship`, data),
  getHistory: (batchId) => axios.get(`${SUPPLIER_API}/history/${batchId}`),

  // Distributor operations
  receive: (data) => axios.post(`${DISTRIBUTOR_API}/receive`, data),
  store: (data) => axios.post(`${DISTRIBUTOR_API}/store`, data),
  deliver: (data) => axios.post(`${DISTRIBUTOR_API}/deliver`, data),

  // Retailer operations
  receiveRetail: (data) => axios.post(`${RETAILER_API}/receive`, data),
  sell: (data) => axios.post(`${RETAILER_API}/sold`, data),
  verify: (batchId) => axios.get(`${RETAILER_API}/verify/${batchId}`),

  // Blockchain operations
  mine: (port) => axios.post(`http://localhost:${port}/mine`),
  getChain: () => axios.get(`${BLOCKCHAIN_API}/chain`),

    // Admin operations (NEW)
  getActorsByRole: (role) => axios.get(`${ADMIN_API}/actors/by-role/${role}`),
  getAllActors: () => axios.get(`${ADMIN_API}/actors`),
};