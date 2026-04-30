import { useState, useEffect } from 'react';
import { apiGet, apiPost } from '../api';
import InventoryGrid from '../components/InventoryGrid';
import ItemCard      from '../components/ItemCard';
import ScaleReading  from '../components/ScaleReading';
import BinNavigation from '../components/MotorSorting';
import ResultScreen  from '../components/ResultScreen';
import BackButton    from '../components/BackButton';

// stages: select → navigating → confirm → weighing → confirmWeight → done
export default function UseScreen({ onBack }) {
  const [stage, setStage]             = useState('select');
  const [selectedItem, setSelectedItem] = useState(null);
  const [weight, setWeight]           = useState(null);
  const [manualQty, setManualQty]     = useState('');
  const [result, setResult]           = useState(null);

  const isWeighed = selectedItem?.gross_weight != null;

  function toItemCardShape(item) {
    const qty  = item.gross_weight ?? item.liquid_quantity ?? item.count;
    const unit = item.gross_weight != null ? 'g' : item.liquid_quantity != null ? 'oz' : 'units';
    return { ...item, quantity: qty, unit, bin_id: item.bin };
  }

  // ── Navigate motor to bin ─────────────────────────────────────────────────
  useEffect(() => {
    if (stage !== 'navigating' || !selectedItem) return;
    apiPost('/api/navigate', { bin_id: selectedItem.bin })
      .then(() => setStage('confirm'))
      .catch(() => setStage('confirm'));
  }, [stage, selectedItem]);

  // ── One-shot scale read ───────────────────────────────────────────────────
  useEffect(() => {
    if (stage !== 'weighing') return;
    apiGet('/api/weight')
      .then(data => {
        setWeight(data.grams);
        setStage('confirmWeight');
      })
      .catch(() => {
        setResult({ success: false, msg: 'Scale read failed. Check hardware.' });
        setStage('done');
      });
  }, [stage]);

  async function onConfirmWeight() {
    try {
      await apiPost('/api/update', {
        item_data: { barcode: selectedItem.barcode },
        remaining_weight: weight,
      });
      setResult({ success: true, msg: `Usage recorded. ${weight.toFixed(1)}g remaining.` });
    } catch {
      setResult({ success: false, msg: 'Failed to update inventory.' });
    }
    setStage('done');
  }

  async function submitManual() {
    const qty = parseFloat(manualQty);
    if (isNaN(qty) || qty <= 0) return;
    try {
      await apiPost('/api/update', {
        item_data: { barcode: selectedItem.barcode },
        usage: qty,
      });
      setResult({ success: true, msg: 'Inventory updated.' });
    } catch {
      setResult({ success: false, msg: 'Failed to update inventory.' });
    }
    setStage('done');
  }

  if (stage === 'select') return (
    <div className="screen">
      <BackButton onClick={onBack} />
      <div className="section-label">Select Item to Use</div>
      <InventoryGrid onSelect={item => { setSelectedItem(item); setStage('navigating'); }} />
    </div>
  );

  if (stage === 'navigating') return (
    <BinNavigation binId={selectedItem?.bin} />
  );

  if (stage === 'confirm') return (
    <div className="screen">
      <BackButton onClick={() => setStage('select')} />
      <div className="section-label">Record Usage</div>
      <ItemCard item={toItemCardShape(selectedItem)} />
      {isWeighed ? (
        <>
          <button className="btn btn-primary" onClick={() => setStage('weighing')}>
            Weigh Remaining
          </button>
          <div className="section-label" style={{ marginTop: 16 }}>Or enter manually</div>
          <label className="input-label">Amount used (g)</label>
          <input
            className="input-field"
            type="number"
            min="0"
            placeholder="0"
            value={manualQty}
            onChange={e => setManualQty(e.target.value)}
          />
          <button className="btn" onClick={submitManual} disabled={!manualQty}>
            Record Manual Usage
          </button>
        </>
      ) : (
        <>
          <label className="input-label">
            {selectedItem?.liquid_quantity != null ? 'Amount used (oz)' : 'Units used'}
          </label>
          <input
            className="input-field"
            type="number"
            min="0"
            placeholder="0"
            value={manualQty}
            onChange={e => setManualQty(e.target.value)}
          />
          <button className="btn btn-primary" onClick={submitManual} disabled={!manualQty}>
            Record Usage
          </button>
        </>
      )}
      <button className="btn" onClick={() => setStage('select')}>Back to List</button>
    </div>
  );

  if (stage === 'weighing') return (
    <div className="screen">
      <div className="section-label">Reading Scale…</div>
      <ScaleReading weight={weight} />
    </div>
  );

  if (stage === 'confirmWeight') return (
    <div className="screen">
      <BackButton onClick={() => setStage('confirm')} />
      <div className="section-label">Confirm Weight</div>
      <ScaleReading weight={weight} />
      <button className="btn btn-primary" onClick={onConfirmWeight}>
        Confirm {weight?.toFixed(1)}g remaining
      </button>
      <button className="btn" onClick={() => { setWeight(null); setStage('weighing'); }}>
        Re-weigh
      </button>
    </div>
  );

  if (stage === 'done') return (
    <ResultScreen
      success={result?.success}
      title={result?.success ? 'Usage Recorded' : 'Error'}
      sub={result?.msg}
      onDone={onBack}
    />
  );
}