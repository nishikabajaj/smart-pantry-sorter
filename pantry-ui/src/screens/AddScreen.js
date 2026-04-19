import { useState } from 'react';
import { apiGet, apiPost } from '../api';
import ScanScreen   from '../components/ScanScreen';
import ItemCard     from '../components/ItemCard';
import ScaleReading from '../components/ScaleReading';
import MotorSorting from '../components/MotorSorting';
import ResultScreen from '../components/ResultScreen';
import BackButton   from '../components/BackButton';

// stages: scan → confirm → weighing → confirmWeight → sorting → done
//                        ↘ (no scale needed)         ↗
export default function AddScreen({ onBack }) {
  const [stage, setStage]           = useState('scan');
  const [scanResult, setScanResult] = useState(null);
  const [weight, setWeight]         = useState(null);
  const [result, setResult]         = useState(null);

  const needsWeighing = scanResult?.item_data?.product_quantity_unit === 'g';

  // ── Confirm item ───────────────────────────────────────────────────────────
  async function onConfirm() {
    if (needsWeighing) {
      // Show spinner, do a single scale read, then let user confirm the value
      setStage('weighing');
      try {
        const data = await apiGet('/api/weight');
        setWeight(data.grams);
        setStage('confirmWeight');
      } catch {
        setResult({ success: false, msg: 'Scale read failed. Check hardware.' });
        setStage('done');
      }
    } else {
      // No scale needed — add and sort immediately
      setStage('sorting');
      try {
        await apiPost('/api/add', {
          item_data: scanResult.item_data,
          new:       scanResult.new,
        });
        setResult({ success: true, msg: 'Item added and sorted.' });
      } catch {
        setResult({ success: false, msg: 'Failed to add item.' });
      }
      setStage('done');
    }
  }

  // ── Confirm weight reading ─────────────────────────────────────────────────
  async function onConfirmWeight() {
    setStage('sorting');
    try {
      await apiPost('/api/add', {
        item_data: scanResult?.item_data,
        new:       scanResult?.new,
        weight_g:  weight,
      });
      setResult({ success: true, msg: `Item added — ${weight.toFixed(1)}g recorded.` });
    } catch {
      setResult({ success: false, msg: 'Failed to add item. Check server.' });
    }
    setStage('done');
  }

  // ── Re-weigh: go back to confirm so onConfirm re-triggers a fresh read ────
  function onReweigh() {
    setWeight(null);
    setStage('confirm');
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  if (stage === 'scan') return (
    <ScanScreen
      actionLabel="Add Item"
      onBack={onBack}
      onScanned={r => { setScanResult(r); setStage('confirm'); }}
    />
  );

  if (stage === 'confirm') return (
    <div className="screen">
      <BackButton onClick={() => setStage('scan')} />
      <div className="section-label">Confirm Item</div>
      <ItemCard item={scanResult?.item_data} />
      {scanResult?.new && (
        <div className="banner info">New item — will be registered in the database.</div>
      )}
      {needsWeighing && (
        <div className="banner info">Place item on the scale before confirming.</div>
      )}
      <button className="btn btn-primary" onClick={onConfirm}>
        Confirm &amp; {needsWeighing ? 'Weigh' : 'Add to Pantry'}
      </button>
      <button className="btn" onClick={() => setStage('scan')}>Re-scan</button>
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
      <div className="section-label">Confirm Weight</div>
      <ScaleReading weight={weight} />
      <button className="btn btn-primary" onClick={onConfirmWeight}>
        Confirm {weight?.toFixed(1)}g &amp; Sort
      </button>
      <button className="btn" onClick={onReweigh}>Re-weigh</button>
    </div>
  );

  if (stage === 'sorting') return (
    <MotorSorting binId={scanResult?.item_data?.bin_id} />
  );

  if (stage === 'done') return (
    <ResultScreen
      success={result?.success}
      title={result?.success ? 'Item Added' : 'Error'}
      sub={result?.msg}
      onDone={onBack}
    />
  );
}