import { useState } from 'react';
import { apiPost }   from '../api';
import ScanScreen     from '../components/ScanScreen';
import ItemCard       from '../components/ItemCard';
import LoadingSpinner from '../components/LoadingSpinner';
import ResultScreen   from '../components/ResultScreen';
import BackButton     from '../components/BackButton';

// stages: scan → confirm → loading → done
export default function RemoveScreen({ onBack }) {
  const [stage, setStage]           = useState('scan');
  const [scanResult, setScanResult] = useState(null);
  const [result, setResult]         = useState(null);

  async function handleRemove() {
    setStage('loading');
    try {
      await apiPost('/api/remove', { item_data: scanResult.item_data });
      setResult({ success: true, msg: 'Item removed from pantry.' });
    } catch {
      setResult({ success: false, msg: 'Failed to remove item.' });
    } finally {
      setStage('done');
    }
  }

  if (stage === 'scan') return (
    <ScanScreen
      actionLabel="Remove Item"
      onBack={onBack}
      onScanned={r => { setScanResult(r); setStage('confirm'); }}
    />
  );

  if (stage === 'confirm') return (
    <div className="screen">
      <BackButton onClick={() => setStage('scan')} />
      <div className="section-label">Remove Item</div>
      <ItemCard item={scanResult?.item_data} />
      <div className="banner error">
        This will permanently remove the item from inventory.
      </div>
      <button className="btn btn-danger" onClick={handleRemove}>Confirm Removal</button>
      <button className="btn" onClick={onBack}>Cancel</button>
    </div>
  );

  if (stage === 'loading') return (
    <div className="screen">
      <LoadingSpinner label="Removing item" sub="Updating database…" />
    </div>
  );

  if (stage === 'done') return (
    <ResultScreen
      success={result?.success}
      title={result?.success ? 'Item Removed' : 'Error'}
      sub={result?.msg}
      onDone={onBack}
    />
  );
}