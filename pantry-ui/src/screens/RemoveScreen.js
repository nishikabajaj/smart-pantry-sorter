import { useState, useEffect } from 'react';
import { apiPost }      from '../api';
import InventoryGrid    from '../components/InventoryGrid';
import ItemCard         from '../components/ItemCard';
import BinNavigation    from '../components/MotorSorting';
import LoadingSpinner   from '../components/LoadingSpinner';
import ResultScreen     from '../components/ResultScreen';
import BackButton       from '../components/BackButton';

// stages: select → navigating → confirm → loading → done
export default function RemoveScreen({ onBack }) {
  const [stage, setStage]           = useState('select');
  const [selectedItem, setSelectedItem] = useState(null);
  const [result, setResult]         = useState(null);
  
  function toItemCardShape(item) {
  const qty  = item.gross_weight ?? item.liquid_quantity ?? item.count;
  const unit = item.gross_weight != null ? 'g' : item.liquid_quantity != null ? 'oz' : 'units';
  return {
    ...item,
    quantity: qty,
    unit,
    bin_id: item.bin,
    };
  }

  // ── Navigate motor to bin then proceed to confirm ─────────────────────────
  useEffect(() => {
    if (stage !== 'navigating' || !selectedItem) return;
    apiPost('/api/navigate', { bin_id: selectedItem.bin })
      .then(() => setStage('confirm'))
      .catch(() => setStage('confirm'));
  }, [stage, selectedItem]);

  async function handleRemove() {
    setStage('loading');
    try {
      await apiPost('/api/remove', { item_data: selectedItem });
      setResult({ success: true, msg: 'Item removed from pantry.' });
    } catch {
      setResult({ success: false, msg: 'Failed to remove item.' });
    }
    setStage('done');
  }

  if (stage === 'select') return (
    <div className="screen">
      <BackButton onClick={onBack} />
      <div className="section-label">Select Item to Remove</div>
      <InventoryGrid onSelect={item => { setSelectedItem(item); setStage('navigating'); }} />
    </div>
  );

  if (stage === 'navigating') return (
    <BinNavigation binId={selectedItem?.bin} />
  );

  if (stage === 'confirm') return (
    <div className="screen">
      <BackButton onClick={() => setStage('select')} />
      <div className="section-label">Remove Item</div>
      <ItemCard item={toItemCardShape(selectedItem)} />
      <div className="banner error">
        This will permanently remove the item from inventory.
      </div>
      <button className="btn btn-danger" onClick={handleRemove}>Confirm Removal</button>
      <button className="btn" onClick={onBack}>Cancel</button>
    </div>
  );

  if (stage === 'loading') return (
    <LoadingSpinner label="Removing item" sub="Updating database…" />
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