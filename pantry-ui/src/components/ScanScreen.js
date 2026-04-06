import { useState, useEffect, useRef } from 'react';
import { apiPost } from '../api';
import BackButton     from './BackButton';
import LoadingSpinner from './LoadingSpinner';

export default function ScanScreen({ actionLabel, onBack, onScanned }) {
  const [code, setCode]       = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const inputRef              = useRef(null);

  // Auto-focus so a physical USB barcode scanner (keyboard wedge) works immediately
  useEffect(() => { inputRef.current?.focus(); }, []);

  async function handleScan() {
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    try {
      // POST /api/scan → { item_data: {...}, new: bool }
      const result = await apiPost('/api/scan', { barcode: code.trim() });
      onScanned(result);
    } catch {
      setError('Could not identify barcode. Check server connection and try again.');
      setLoading(false);
    }
  }

  if (loading) return (
    <div className="screen">
      <BackButton onClick={onBack} />
      <LoadingSpinner
        label="Looking up barcode"
        sub="Checking local database and OpenFoodFacts…"
      />
    </div>
  );

  return (
    <div className="screen">
      <BackButton onClick={onBack} />
      <div className="section-label">{actionLabel}</div>

      <div className="scan-box">
        <div className="scan-label">Barcode Scanner</div>
        <input
          ref={inputRef}
          className="scan-input"
          type="text"
          inputMode="numeric"
          placeholder="000000000000"
          value={code}
          onChange={e => setCode(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleScan()}
          autoComplete="off"
        />
        <div className="scan-hint">Scan barcode or type manually → Enter</div>
      </div>

      {error && <div className="banner error">{error}</div>}

      <button className="btn btn-primary" onClick={handleScan} disabled={!code.trim()}>
        Look Up Item
      </button>
    </div>
  );
}