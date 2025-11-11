import { useState, useEffect } from 'react';
import { Users, Plus, Trash2, Key, Activity, BarChart } from 'lucide-react';
import axios from 'axios';

const ADMIN_API = 'http://localhost:5500/admin';

function AdminPanel() {
  const [users, setUsers] = useState([]);
  const [actors, setActors] = useState([]);
  const [stats, setStats] = useState(null);
  const [activities, setActivities] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    role: 'supplier',
    email: ''
  });
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('users'); // users, actors, stats, activity

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    try {
      if (activeTab === 'users') {
        await loadUsers();
      } else if (activeTab === 'actors') {
        await loadActors();
      } else if (activeTab === 'stats') {
        await loadStats();
      } else if (activeTab === 'activity') {
        await loadActivities();
      }
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const loadUsers = async () => {
    const response = await axios.get(`${ADMIN_API}/users`);
    setUsers(response.data.users || []);
  };

  const loadActors = async () => {
    const response = await axios.get(`${ADMIN_API}/actors`);
    setActors(response.data.actors || []);
  };

  const loadStats = async () => {
    const response = await axios.get(`${ADMIN_API}/stats`);
    setStats(response.data);
  };

  const loadActivities = async () => {
    const response = await axios.get(`${ADMIN_API}/activity?limit=50`);
    setActivities(response.data.activities || []);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setLoading(true);

    try {
      const response = await axios.post(`${ADMIN_API}/users`, formData);
      setMessage(`✅ User created successfully! Actor name: ${response.data.user.actor_name}`);
      setFormData({ username: '', role: 'supplier', email: '' });
      setShowAddForm(false);
      await loadUsers();
      await loadActors();
    } catch (error) {
      setMessage('❌ Failed to create user: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (userId, username) => {
    if (!confirm(`Are you sure you want to deactivate user: ${username}?`)) return;

    try {
      await axios.delete(`${ADMIN_API}/users/${userId}`);
      setMessage(`✅ User ${username} deactivated`);
      await loadUsers();
    } catch (error) {
      setMessage('❌ Failed to delete user: ' + (error.response?.data?.error || error.message));
    }
  };

  return (
    <div className="admin-panel">
      <div className="admin-header">
        <h1>⚙️ Admin Panel</h1>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-primary"
        >
          <Plus size={20} /> Add New User
        </button>
      </div>

      {message && (
        <div className={`message ${message.includes('✅') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}

      {showAddForm && (
        <div className="modal-overlay" onClick={() => setShowAddForm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create New User</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Username *</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  required
                  placeholder="e.g., john_smith"
                  pattern="[a-zA-Z0-9_]+"
                  title="Only letters, numbers, and underscores"
                />
                <small>Actor name will be generated as: {formData.role.charAt(0).toUpperCase() + formData.role.slice(1)}_{formData.username}</small>
              </div>

              <div className="form-group">
                <label>Role *</label>
                <select
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                  required
                >
                  <option value="supplier">Supplier</option>
                  <option value="distributor">Distributor</option>
                  <option value="retailer">Retailer</option>
                </select>
              </div>

              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  placeholder="user@example.com"
                />
              </div>

              <div className="form-actions">
                <button type="button" onClick={() => setShowAddForm(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="btn-primary">
                  {loading ? 'Creating...' : 'Create User & Generate Keys'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="admin-tabs">
        <button
          className={activeTab === 'users' ? 'active' : ''}
          onClick={() => setActiveTab('users')}
        >
          <Users size={18} /> Users
        </button>
        <button
          className={activeTab === 'actors' ? 'active' : ''}
          onClick={() => setActiveTab('actors')}
        >
          <Key size={18} /> Actors & Keys
        </button>
        <button
          className={activeTab === 'stats' ? 'active' : ''}
          onClick={() => setActiveTab('stats')}
        >
          <BarChart size={18} /> Statistics
        </button>
        <button
          className={activeTab === 'activity' ? 'active' : ''}
          onClick={() => setActiveTab('activity')}
        >
          <Activity size={18} /> Activity Log
        </button>
      </div>

      <div className="admin-content">
        {activeTab === 'users' && (
          <div className="users-section">
            <h2>👥 Active Users ({users.length})</h2>
            <div className="users-grid">
              {users.map(user => (
                <div key={user.id} className="user-card">
                  <div className="user-header">
                    <Users size={24} />
                    <div>
                      <h3>{user.username}</h3>
                      <span className={`role-badge ${user.role}`}>{user.role}</span>
                    </div>
                  </div>
                  <div className="user-details">
                    <p><strong>Actor:</strong> {user.actor_name}</p>
                    <p><strong>Email:</strong> {user.email || 'N/A'}</p>
                    <p><strong>Created:</strong> {new Date(user.created_at).toLocaleDateString()}</p>
                  </div>
                  {user.role !== 'admin' && (
                    <button
                      onClick={() => handleDelete(user.id, user.username)}
                      className="btn-danger"
                    >
                      <Trash2 size={16} /> Deactivate
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'actors' && (
          <div className="actors-section">
            <h2>🔐 Registered Actors with Crypto Keys ({actors.length})</h2>
            <div className="actors-table">
              <table>
                <thead>
                  <tr>
                    <th>Actor Name</th>
                    <th>Username</th>
                    <th>Role</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Keys</th>
                  </tr>
                </thead>
                <tbody>
                  {actors.map(actor => (
                    <tr key={actor.actor_name}>
                      <td><strong>{actor.actor_name}</strong></td>
                      <td>{actor.username}</td>
                      <td><span className={`role-badge ${actor.role}`}>{actor.role}</span></td>
                      <td>{actor.email || '-'}</td>
                      <td>
                        {actor.active ? (
                          <span className="status-badge active">Active</span>
                        ) : (
                          <span className="status-badge inactive">Inactive</span>
                        )}
                      </td>
                      <td>
                        {actor.has_keys ? (
                          <span className="keys-badge">
                            <Key size={14} /> Keys Generated
                          </span>
                        ) : (
                          <span className="keys-badge missing">No Keys</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'stats' && stats && (
          <div className="stats-section">
            <h2>📊 System Statistics</h2>
            <div className="stats-grid">
              <div className="stat-card">
                <Users size={32} />
                <h3>Total Users</h3>
                <p className="stat-value">{stats.total_users}</p>
              </div>
              <div className="stat-card">
                <Key size={32} />
                <h3>Suppliers</h3>
                <p className="stat-value">{stats.suppliers}</p>
              </div>
              <div className="stat-card">
                <Key size={32} />
                <h3>Distributors</h3>
                <p className="stat-value">{stats.distributors}</p>
              </div>
              <div className="stat-card">
                <Key size={32} />
                <h3>Retailers</h3>
                <p className="stat-value">{stats.retailers}</p>
              </div>
            </div>

            <h3>Recent Activity</h3>
            <div className="activity-list">
              {stats.recent_activity.map((activity, idx) => (
                <div key={idx} className="activity-item">
                  <Activity size={16} />
                  <div>
                    <strong>{activity.username}</strong> - {activity.action}
                    <small>{new Date(activity.timestamp).toLocaleString()}</small>
                    {activity.details && <p>{activity.details}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'activity' && (
          <div className="activity-section">
            <h2>📋 Activity Log</h2>
            <div className="activity-log">
              {activities.map((activity, idx) => (
                <div key={idx} className="log-entry">
                  <div className="log-header">
                    <span className="log-user">{activity.username} ({activity.actor_name})</span>
                    <span className="log-time">{new Date(activity.timestamp).toLocaleString()}</span>
                  </div>
                  <div className="log-body">
                    <span className="log-action">{activity.action}</span>
                    {activity.details && <span className="log-details">{activity.details}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminPanel;