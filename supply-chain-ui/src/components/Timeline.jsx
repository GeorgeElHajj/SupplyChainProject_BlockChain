import { Package, CheckCircle, Truck, Warehouse, Store, ShoppingCart } from 'lucide-react';

function Timeline({ events }) {
  const getIcon = (action) => {
    switch (action) {
      case 'registered':
        return <Package size={24} />;
      case 'quality_checked':
        return <CheckCircle size={24} />;
      case 'shipped':
        return <Truck size={24} />;
      case 'received':
        return <Warehouse size={24} />;
      case 'stored':
        return <Warehouse size={24} />;
      case 'delivered':
        return <Truck size={24} />;
      case 'received_retail':
        return <Store size={24} />;
      case 'sold':
        return <ShoppingCart size={24} />;
      default:
        return <Package size={24} />;
    }
  };

  const getStepName = (action) => {
    const names = {
      registered: 'Product Registered',
      quality_checked: 'Quality Check',
      shipped: 'Shipped to Distributor',
      received: 'Received by Distributor',
      stored: 'Stored in Warehouse',
      delivered: 'Delivered to Retailer',
      received_retail: 'Received by Retailer',
      sold: 'Sold to Customer'
    };
    return names[action] || action;
  };

  return (
    <div className="timeline">
      {events.map((event, idx) => (
        <div key={idx} className="timeline-item">
          <div className="timeline-marker">
            <div className="timeline-icon">
              {getIcon(event.action)}
            </div>
            {idx < events.length - 1 && <div className="timeline-line"></div>}
          </div>

          <div className="timeline-content">
            <h4>{getStepName(event.action)}</h4>
            <p className="timeline-actor">{event.actor}</p>
            <p className="timeline-time">
              {new Date(event.timestamp).toLocaleString()}
            </p>
            {event.signature_valid !== undefined && (
              <span className={`signature-indicator ${event.signature_valid ? 'valid' : 'invalid'}`}>
                {event.signature_valid ? '🔒 Verified' : '⚠️ Unverified'}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default Timeline;