import { useState, useEffect } from 'react';
import { apiGet } from '../api';
import LoadingSpinner from './LoadingSpinner';

export default function InventoryGrid({ onSelect }) {
  const [items, setItems]     = useState([]);
  const [query, setQuery]     = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    apiGet('/api/data')
      .then(data => { setItems(data); setLoading(false); })
      .catch(() => { setError('Failed to load inventory.'); setLoading(false); });
  }, []);

  const filtered = items.filter(item =>
    item.name.toLowerCase().includes(query.toLowerCase()) ||
    item.brand?.toLowerCase().includes(query.toLowerCase()) ||
    item.category?.toLowerCase().includes(query.toLowerCase())
  );

  if (loading) return <LoadingSpinner label="Loading inventory" sub="Fetching pantry items…" />;
  if (error)   return <div className="banner error">{error}</div>;

  return (
    <div className="inventory-select-wrap">
      <input
        className="scan-input"
        type="text"
        placeholder="Search by name, brand, category…"
        value={query}
        onChange={e => setQuery(e.target.value)}
        autoFocus
      />
      {filtered.length === 0 && (
        <div className="banner info">No items match your search.</div>
      )}
      <div className="inventory-grid">
        {filtered.map(item => {
        //   const qty  = item.gross_weight ?? item.liquid_quantity ?? item.count;
        //  const unit = item.gross_weight != null ? 'g' : item.liquid_quantity != null ? 'oz' : 'units';
          return (
            <button key={item.id} className="inventory-grid-card" onClick={() => onSelect(item)}>
                <div className="igc-name">{item.name}</div>
                <div className="igc-brand">{item.brand || '—'}</div>
                <div className="igc-qty">
                    {item.gross_weight ?? item.liquid_quantity ?? item.count ?? '—'}
                    {' '}
                    {item.gross_weight != null ? 'g' : item.liquid_quantity != null ? 'oz' : 'units'}
                </div>
                <div className="igc-bin">Bin #{item.bin}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}