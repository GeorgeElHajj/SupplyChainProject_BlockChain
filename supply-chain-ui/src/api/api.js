import axios from 'axios';

// API URLs
const SUPPLIER_API = 'http://localhost:5175/api/supplier';
const DISTRIBUTOR_API = 'http://localhost:5137/api/distributor';
const RETAILER_API = 'http://localhost:5112/api/retailer';
const ADMIN_API = 'http://localhost:5500/admin';

// Blockchain node URLs (with failover)
const BLOCKCHAIN_NODES = [
  'http://localhost:5000',
  'http://localhost:5001',
  'http://localhost:5002'
];

// Current blockchain node index
let currentNodeIndex = 0;
let nodeHealthStatus = BLOCKCHAIN_NODES.map(() => true);

// Background health check
setInterval(async () => {
  for (let i = 0; i < BLOCKCHAIN_NODES.length; i++) {
    try {
      await axios.get(`${BLOCKCHAIN_NODES[i]}/status`, { timeout: 5000 });
      nodeHealthStatus[i] = true;
    } catch (error) {
      nodeHealthStatus[i] = false;
      console.warn(`Node ${i} (${BLOCKCHAIN_NODES[i]}) is down`);
    }
  }
  console.log('Node health:', nodeHealthStatus.map((h, i) => `Node${i}=${h}`).join(', '));
}, 30000); // Check every 30 seconds

// Get next healthy blockchain node
const getHealthyBlockchainNode = () => {
  // Try current node first
  if (nodeHealthStatus[currentNodeIndex]) {
    console.log(`Using primary node ${currentNodeIndex}: ${BLOCKCHAIN_NODES[currentNodeIndex]}`);
    return BLOCKCHAIN_NODES[currentNodeIndex];
  }

  // Find next healthy node
  for (let i = 0; i < BLOCKCHAIN_NODES.length; i++) {
    const nextIndex = (currentNodeIndex + i + 1) % BLOCKCHAIN_NODES.length;
    if (nodeHealthStatus[nextIndex]) {
      currentNodeIndex = nextIndex;
      console.warn(`Switched to backup node ${nextIndex}: ${BLOCKCHAIN_NODES[nextIndex]}`);
      return BLOCKCHAIN_NODES[nextIndex];
    }
  }

  // No healthy nodes, use current anyway
  console.error('No healthy nodes available! Using node', currentNodeIndex);
  return BLOCKCHAIN_NODES[currentNodeIndex];
};

// Blockchain API calls with automatic failover
const callBlockchainWithFailover = async (endpoint, method = 'GET', data = null) => {
  for (let attempt = 0; attempt < BLOCKCHAIN_NODES.length; attempt++) {
    try {
      const nodeUrl = getHealthyBlockchainNode();
      const url = `${nodeUrl}${endpoint}`;

      console.log(`Attempt ${attempt + 1}: Calling ${url}`);

      const response = method === 'GET'
        ? await axios.get(url, { timeout: 10000 })
        : await axios.post(url, data, { timeout: 10000 });

      console.log(`Success on node ${currentNodeIndex}`);
      return response.data;
    } catch (error) {
      console.error(`Attempt ${attempt + 1} failed:`, error.message);

      // Mark current node as unhealthy
      nodeHealthStatus[currentNodeIndex] = false;

      // If this was the last attempt, throw error
      if (attempt === BLOCKCHAIN_NODES.length - 1) {
        throw error;
      }

      // Wait a bit before trying next node
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
};

export const api = {
  // ==================== SUPPLIER OPERATIONS ====================

  addProduct: (data) => axios.post(`${SUPPLIER_API}/add-product`, data),

  qualityCheck: (data) => axios.post(`${SUPPLIER_API}/quality-check`, data),

  ship: (data) => axios.post(`${SUPPLIER_API}/ship`, data),

  getHistory: (batchId) => axios.get(`${SUPPLIER_API}/history/${batchId}`),

  // ==================== DISTRIBUTOR OPERATIONS ====================

  receive: (data) => axios.post(`${DISTRIBUTOR_API}/receive`, data),

  store: (data) => axios.post(`${DISTRIBUTOR_API}/store`, data),

  deliver: (data) => axios.post(`${DISTRIBUTOR_API}/deliver`, data),

  // ==================== RETAILER OPERATIONS ====================

  receiveRetail: (data) => axios.post(`${RETAILER_API}/receive`, data),

  sell: (data) => axios.post(`${RETAILER_API}/sold`, data),

  verify: (batchId) => axios.get(`${RETAILER_API}/verify/${batchId}`),

  // ==================== BLOCKCHAIN OPERATIONS (with failover) ====================

  mine: async (port) => {
    // If specific port provided, use that node
    if (port) {
      const nodeUrl = `http://localhost:${port}`;
      return axios.post(`${nodeUrl}/mine`);
    }

    // Otherwise mine on all healthy nodes
    const minePromises = BLOCKCHAIN_NODES
      .map((node, index) => ({ node, index }))
      .filter(({ index }) => nodeHealthStatus[index])
      .map(({ node }) =>
        axios.post(`${node}/mine`).catch(err => {
          console.error(`Mining failed on ${node}:`, err.message);
          return null;
        })
      );

    const results = await Promise.all(minePromises);

    // Return success if at least one mining succeeded
    if (results.some(r => r !== null)) {
      return { data: { success: true } };
    }

    throw new Error('Mining failed on all nodes');
  },

  getChain: () => callBlockchainWithFailover('/chain'),

  getMempool: () => callBlockchainWithFailover('/mempool'),

  getBlockchain: () => callBlockchainWithFailover('/blockchain'),

  getStatus: () => callBlockchainWithFailover('/status'),

  // ==================== ADMIN OPERATIONS ====================

  getActorsByRole: (role) => axios.get(`${ADMIN_API}/actors/by-role/${role}`),

  getAllActors: () => axios.get(`${ADMIN_API}/actors`),

  getActors: () => axios.get(`${ADMIN_API}/actors`),

  registerActor: (data) => axios.post(`${ADMIN_API}/register`, data),

  deleteActor: (actorName) => axios.delete(`${ADMIN_API}/actors/${actorName}`),

  getUsers: () => axios.get(`${ADMIN_API}/users`),

  createUser: (data) => axios.post(`${ADMIN_API}/users`, data),

  deleteUser: (userId) => axios.delete(`${ADMIN_API}/users/${userId}`),

  getBlockchainHistory: (batchId) => callBlockchainWithFailover(`/history/${batchId}`),

  verifyBlockchainBatch: (batchId) => callBlockchainWithFailover(`/verify/${batchId}`),

  // ==================== HEALTH CHECKS ====================

  healthCheck: async () => {
    const checks = await Promise.allSettled([
      axios.get(`${SUPPLIER_API}/health`),
      axios.get(`${DISTRIBUTOR_API}/health`),
      axios.get(`${RETAILER_API}/health`),
      axios.get(`${ADMIN_API}/health`),
      callBlockchainWithFailover('/status')
    ]);

    return {
      supplier: checks[0].status === 'fulfilled',
      distributor: checks[1].status === 'fulfilled',
      retailer: checks[2].status === 'fulfilled',
      admin: checks[3].status === 'fulfilled',
      blockchain: checks[4].status === 'fulfilled',
      blockchainNodes: nodeHealthStatus
    };
  },

  // ==================== UTILITY ====================

  // Get current blockchain node info
  getCurrentNode: () => ({
    index: currentNodeIndex,
    url: BLOCKCHAIN_NODES[currentNodeIndex],
    health: nodeHealthStatus
  })
};

export default api;