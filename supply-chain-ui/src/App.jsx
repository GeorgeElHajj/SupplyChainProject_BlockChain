import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Package, CheckCircle, Truck, Warehouse, Store, Search,Settings ,Layers } from 'lucide-react';
import Dashboard from './components/Dashboard';
import AddProduct from './components/AddProduct';
import QualityCheck from './components/QualityCheck';
import ShipProduct from './components/ShipProduct';
import DistributorReceive from './components/DistributorReceive.jsx';
import StoreProduct from './components/StoreProduct';
import DeliverToRetailer from './components/DeliverToRetailer';
import RetailerReceive from './components/RetailerReceive';
import SellProduct from './components/SellProduct';
import TrackBatch from './components/TrackBatch';
import './App.css';
import AdminPanel from "./components/AdminPanel";
import BlockchainExplorer from "./components/Blockchainexplorer.jsx";

function App() {
  return (
    <Router>
      <div className="app">
        <nav className="sidebar">
          <h1>🔗 Supply Chain</h1>

          <div className="nav-section">
            <h3>📦 Supplier</h3>
            <Link to="/"><Package size={18}/> Dashboard</Link>
            <Link to="/add-product"><Package size={18}/> Add Product</Link>
            <Link to="/quality-check"><CheckCircle size={18}/> Quality Check</Link>
            <Link to="/ship"><Truck size={18}/> Ship Product</Link>
          </div>

          <div className="nav-section">
            <h3>🚚 Distributor</h3>
            <Link to="/distributor/receive"><Truck size={18}/> Receive</Link>
            <Link to="/distributor/store"><Warehouse size={18}/> Store</Link>
            <Link to="/distributor/deliver"><Truck size={18}/> Deliver</Link>
          </div>

          <div className="nav-section">
            <h3>🏪 Retailer</h3>
            <Link to="/retailer/receive"><Store size={18}/> Receive</Link>
            <Link to="/retailer/sell"><Store size={18}/> Sell</Link>
          </div>

          <div className="nav-section">
            <h3>🔍 Tracking</h3>
            <Link to="/track"><Search size={18}/> Track Batch</Link>
          </div>
        <div className="nav-section">
          <h3>⚙️ Admin</h3>
          <Link to="/admin"><Settings size={18}/> User Management</Link>
          <Link to="/blockchain"><Layers size={18}/> Blockchain Explorer</Link>
        </div>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard/>}/>
          <Route path="/add-product" element={<AddProduct/>}/>
          <Route path="/quality-check" element={<QualityCheck/>}/>
          <Route path="/ship" element={<ShipProduct/>}/>
          <Route path="/distributor/receive" element={<DistributorReceive/>}/>
          <Route path="/distributor/store" element={<StoreProduct/>}/>
          <Route path="/distributor/deliver" element={<DeliverToRetailer/>}/>
          <Route path="/retailer/receive" element={<RetailerReceive/>}/>
          <Route path="/retailer/sell" element={<SellProduct/>}/>
          <Route path="/track" element={<TrackBatch/>}/>
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/blockchain" element={<BlockchainExplorer />} />

        </Routes>
      </main>
    </div>
    </Router>
  );
}

export default App;