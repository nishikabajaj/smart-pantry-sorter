import { useState, useEffect } from 'react';
import { apiGet }     from '../api';
import BackButton     from '../components/BackButton';
import LoadingSpinner from '../components/LoadingSpinner';

export default function InventoryScreen({ onBack }) {
  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    apiGet('/api/data')
      .then(data => setItems(Array.isArray(data) ? data : []))
      .catch(()   => setError('Could not load inventory. Is the server running?'))
      .finally(()  => setLoading(false));
  }, []);

  if (loading) return (
    <div className="screen">
      <BackButton onClick={onBack} />
      <LoadingSpinner label="Loading inventory" />
    </div>
  );

  return (
    <div className="screen">
      <BackButton onClick={onBack} />
      <div className="section-label">Inventory — {items.length} items</div>

      {error && <div className="banner error">{error}</div>}

      {items.length === 0 && !error ? (
        <div style={{
          textAlign: 'center', padding: '48px 0',
          color: 'var(--text-faint)', fontFamily: 'var(--mono)', fontSize: 12
        }}>
          No items in pantry
        </div>
      ) : (
        <table className="inv-table">
          <thead>
            <tr>
              <th>Item ID</th>
              <th>Bin</th>
              <th style={{ textAlign: 'right' }}>Quantity</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row, i) => {
              // row shape from /api/data:
              // [id, item_id, gross_weight, liquid_qty, count, bin_id, expiration_date]
              const [, item_id, gross, liquid, count, bin_id] = row;
              const qty  = gross ?? liquid ?? count ?? 0;
              const pct  = Math.min(100, (qty / 1000) * 100);
              const unit = gross != null ? 'g' : liquid != null ? 'oz' : '';

              return (
                <tr key={i}>
                  <td className="mono">{item_id}</td>
                  <td>
                    <span className="badge badge-amber">BIN {bin_id ?? '—'}</span>
                  </td>
                  <td>
                    <div className="qty-bar-wrap">
                      <span style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>
                        {qty}{unit}
                      </span>
                      <div className="qty-bar">
                        <div
                          className={`qty-bar-fill${pct < 20 ? ' low' : ''}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}