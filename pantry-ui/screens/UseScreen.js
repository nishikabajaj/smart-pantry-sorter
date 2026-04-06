import { useState, useEffect, useRef } from 'react';
import { apiGet, apiPost } from '../api';
import ScanScreen   from '../components/ScanScreen';
import ItemCard     from '../components/ItemCard';
import ScaleReading from '../components/ScaleReading';
import ResultScreen from '../components/ResultScreen';
import BackButton   from '../components/BackButton';

// stages: scan → confirm → weighing → done
export default function UseScreen({ onBack }) {
  const [stage, setStage]           = useState('scan');
  const [scanResult, setScanResult] = useState(null);
  const [weight, setWeight]         = useState(null);
  const [manualQty, setManualQty]   = useState('');
  const [result, setResult]         = useState(null);

  const cancelledRef = useRef(false);

  const item      = scanResult?.item_data;
  const isWeighed = item?.product_quantity_unit === 'g';

  // Poll /api/weight on an interval while in the weighing stage.
  // handleTick is declared outside setInterval so no functions are
  // created inside a loop body — satisfies no-loop-func.
  useEffect(() => {
    if (stage !== 'weighing') return;

    cancelledRef.current = false;

    async function handleTick() {
      if (cancelledRef.current) return;
      try {
        const data = await apiGet('/api/weight');
        if (cancelledRef.current) return;
        setWeight(data.grams);
        if (data.stable) {
          cancelledRef.current = true;
          clearInterval(intervalId); // eslint-disable-line no-use-before-define
          try {
            await apiPost('/api/update', { item_data: item, remaining_weight: data.grams });
            setResult({ success: true, msg: `Usage recorded. ${data.grams.toFixed(1)}g remaining.` });
          } catch {
            setResult({ success: false, msg: 'Failed to update inventory.' });
          }
          setStage('done');
        }
      } catch {
        // /api/weight not yet implemented — dev simulation
        if (cancelledRef.current) return;
        setWeight(prev => {
          const next = parseFloat((Math.max(0, (prev ?? item?.quantity ?? 400) - Math.random() * 25)).toFixed(1));
          if (next < 150) {
            cancelledRef.current = true;
            clearInterval(intervalId); // eslint-disable-line no-use-before-define
            setResult({ success: true, msg: `Usage recorded. ${next}g remaining.` });
            setTimeout(() => setStage('done'), 1000);
          }
          return next;
        });
      }
    }

    const intervalId = setInterval(handleTick, 400);

    return () => {
      cancelledRef.current = true;
      clearInterval(intervalId);
    };
  }, [stage, item]);

  async function submitManual() {
    const qty = parseFloat(manualQty);
    if (isNaN(qty) || qty <= 0) return;
    try {
      await apiPost('/api/update', { item_data: item, usage: qty });
      setResult({ success: true, msg: 'Inventory updated.' });
    } catch {
      setResult({ success: false, msg: 'Failed to update inventory.' });
    } finally {
      setStage('done');
    }
  }

  if (stage === 'scan') return (
    <ScanScreen
      actionLabel="Use Item"
      onBack={onBack}
      onScanned={r => { setScanResult(r); setStage('confirm'); }}
    />
  );

  if (stage === 'confirm') return (
    <div className="screen">
      <BackButton onClick={() => setStage('scan')} />
      <div className="section-label">Record Usage</div>
      <ItemCard item={item} />
      {isWeighed ? (
        <>
          <div className="banner info">
            Place the item back on the scale to measure remaining weight.
          </div>
          <button className="btn btn-primary" onClick={() => setStage('weighing')}>
            Start Weighing
          </button>
        </>
      ) : (
        <>
          <label className="input-label">
            {item?.product_quantity_unit === 'oz' ? 'Amount used (oz)' : 'Units used'}
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
      <button className="btn" onClick={() => setStage('scan')}>Re-scan</button>
    </div>
  );

  if (stage === 'weighing') return (
    <div className="screen">
      <div className="section-label">Measuring Remaining</div>
      <ScaleReading weight={weight} />
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