export default function MotorSorting({ binId }) {
  return (
    <div className="motor-wrap">
      <div>
        <div className="motor-label" style={{ marginBottom: 8 }}>Routing to bin</div>
        <div className="motor-bin" style={{ textAlign: 'center' }}>#{binId ?? '—'}</div>
      </div>
      <div className="motor-dial">
        <div className="motor-hand" />
        <div className="motor-center" />
      </div>
      <div className="motor-label">Stepper motor active</div>
    </div>
  );
}