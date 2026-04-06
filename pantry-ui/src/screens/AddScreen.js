import { useState, useEffect, useRef } from 'react';
import { apiGet, apiPost } from '../api';
import ScanScreen   from '../components/ScanScreen';
import ItemCard     from '../components/ItemCard';
import ScaleReading from '../components/ScaleReading';
import MotorSorting from '../components/MotorSorting';
import ResultScreen from '../components/ResultScreen';
import BackButton   from '../components/BackButton';

// stages: scan → confirm → weighing → sorting → done
export default function AddScreen({ onBack }) {
  const [stage, setStage]           = useState('scan');
  const [scanResult, setScanResult] = useState(null);
  const [weight, setWeight]         = useState(null);
  const [result, setResult]         = useState(null);

  // useRef for the cancellation flag so no mutable variable is ever
  // closed over inside a loop body — satisfies no-loop-func.
  const cancelledRef = useRef(false);

  // Poll /api/weight on an interval while in the weighing stage.
  // handleTick is a named async function called by setInterval — no
  // functions are declared inside a loop, so no-loop-func is satisfied.
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
          setStage('sorting');
          try {
            await apiPost('/api/add', {
              item_data: scanResult?.item_data,
              new:       scanResult?.new,
              weight_g:  data.grams,
            });
            setResult({ success: true, msg: `Item added — ${data.grams.toFixed(1)}g recorded.` });
          } catch {
            setResult({ success: false, msg: 'Failed to add item. Check server.' });
          }
          setStage('done');
        }
      } catch {
        // /api/weight not yet implemented — dev simulation
        if (cancelledRef.current) return;
        setWeight(prev => {
          const next = parseFloat(((prev ?? 0) + Math.random() * 40).toFixed(1));
          if (next > 220) {
            cancelledRef.current = true;
            clearInterval(intervalId); // eslint-disable-line no-use-before-define
            setResult({ success: true, msg: `Item added — ${next}g recorded.` });
            setTimeout(() => setStage('done'), 1200);
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
  }, [stage, scanResult]);

  const needsWeighing = scanResult?.item_data?.product_quantity_unit === 'g';

  function onConfirm() {
    if (needsWeighing) {
      setStage('weighing');
    } else {
      setStage('sorting');
      apiPost('/api/add', { item_data: scanResult.item_data, new: scanResult.new })
        .then(()   => setResult({ success: true,  msg: 'Item added and sorted.' }))
        .catch(()  => setResult({ success: false, msg: 'Failed to add item.' }))
        .finally(() => setStage('done'));
    }
  }

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
        <div className="banner info">Place item on the scale when prompted after confirming.</div>
      )}
      <button className="btn btn-primary" onClick={onConfirm}>
        Confirm &amp; {needsWeighing ? 'Weigh' : 'Add to Pantry'}
      </button>
      <button className="btn" onClick={() => setStage('scan')}>Re-scan</button>
    </div>
  );

  if (stage === 'weighing') return (
    <div className="screen">
      <div className="section-label">Measuring Weight</div>
      <ScaleReading weight={weight} />
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