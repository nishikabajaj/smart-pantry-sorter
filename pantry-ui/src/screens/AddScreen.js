import { useState } from 'react';
import { apiGet, apiPost } from '../api';
import ScanScreen   from '../components/ScanScreen';
import ItemCard     from '../components/ItemCard';
import ScaleReading from '../components/ScaleReading';
import MotorSorting from '../components/MotorSorting';
import ResultScreen from '../components/ResultScreen';
import BackButton   from '../components/BackButton';

// stages: scan → confirm → weighing → confirmWeight → sorting → done
//                        ↘ confirmCount ↗
//                        ↘ confirmLiquid ↗
export default function AddScreen({ onBack }) {
  const [stage, setStage]       = useState('scan');
  const [scanResult, setScanResult] = useState(null);
  const [weight, setWeight]     = useState(null);
  const [quantity, setQuantity] = useState('');
  const [result, setResult]     = useState(null);

  const unit = scanResult?.item_data?.product_quantity_unit;
  const needsWeighing = unit === 'g';
  const needsCount    = unit === 'units' || !unit;
  const needsLiquid   = unit === 'oz';

  // ── Confirm item ────────────────────────────────────────────────────────────
  async function onConfirm() {
    if (needsWeighing) {
      setStage('weighing');
      try {
        const data = await apiGet('/api/weight');
        setWeight(data.grams);
        setStage('confirmWeight');
      } catch {
        setResult({ success: false, msg: 'Scale read failed. Check hardware.' });
        setStage('done');
      }
    } else if (needsCount) {
      setQuantity('');
      setStage('confirmCount');
    } else if (needsLiquid) {
      setQuantity('');
      setStage('confirmLiquid');
    } else {
      await submitAdd({});
    }
  }

  // ── Shared add + sort ───────────────────────────────────────────────────────
  async function submitAdd(extras) {
    setStage('sorting');
    try {
      await apiPost('/api/add', {
        item_data: scanResult?.item_data,
        new:       scanResult?.new,
        ...extras,
      });
      setResult({ success: true, msg: extras.weight_g
        ? `Item added — ${extras.weight_g.toFixed(1)}g recorded.`
        : 'Item added and sorted.' });
    } catch {
      setResult({ success: false, msg: 'Failed to add item. Check server.' });
    }
    setStage('done');
  }

  // ── Confirm weight ──────────────────────────────────────────────────────────
  async function onConfirmWeight() {
    await submitAdd({ weight_g: weight });
  }

  // ── Confirm count ───────────────────────────────────────────────────────────
  async function onConfirmCount() {
    const qty = parseInt(quantity);
    if (!qty || qty < 1) return;
    await submitAdd({ quantity_count: qty });
  }

  // ── Confirm liquid ──────────────────────────────────────────────────────────
  async function onConfirmLiquid() {
    const qty = parseFloat(quantity);
    if (!qty || qty <= 0) return;
    await submitAdd({ quantity_oz: qty });
  }

  function onReweigh() {
    setWeight(null);
    setStage('confirm');
  }

  // ── Render ──────────────────────────────────────────────────────────────────
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
      {needsWeighing && <div className="banner info">Place item on the scale before confirming.</div>}
      {needsCount    && <div className="banner info">You'll be asked for the count next.</div>}
      {needsLiquid   && <div className="banner info">You'll be asked for the volume next.</div>}
      <button className="btn btn-primary" onClick={onConfirm}>
        Confirm &amp; {needsWeighing ? 'Weigh' : needsCount ? 'Enter Count' : needsLiquid ? 'Enter Volume' : 'Add to Pantry'}
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

  if (stage === 'confirmCount') return (
    <div className="screen">
      <BackButton onClick={() => setStage('confirm')} />
      <div className="section-label">Enter Count</div>
      <div className="banner info">How many units are you adding?</div>
      <input
        className="scan-input"
        type="number"
        inputMode="numeric"
        min="1"
        placeholder="e.g. 3"
        value={quantity}
        onChange={e => setQuantity(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && onConfirmCount()}
        autoFocus
      />
      <button className="btn btn-primary" onClick={onConfirmCount} disabled={!quantity || parseInt(quantity) < 1}>
        Confirm &amp; Sort
      </button>
    </div>
  );

  if (stage === 'confirmLiquid') return (
    <div className="screen">
      <BackButton onClick={() => setStage('confirm')} />
      <div className="section-label">Enter Volume</div>
      <div className="banner info">How many oz are you adding?</div>
      <input
        className="scan-input"
        type="number"
        inputMode="decimal"
        min="0"
        step="0.1"
        placeholder="e.g. 12.5"
        value={quantity}
        onChange={e => setQuantity(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && onConfirmLiquid()}
        autoFocus
      />
      <button className="btn btn-primary" onClick={onConfirmLiquid} disabled={!quantity || parseFloat(quantity) <= 0}>
        Confirm &amp; Sort
      </button>
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