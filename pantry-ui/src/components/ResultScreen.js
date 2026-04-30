export default function ResultScreen({ success, title, sub, onDone }) {
  return (
    <div className="screen">
      <div className="result-wrap">
        <div className="result-icon">{success ? '✓' : '✕'}</div>
        <div className={`result-title ${success ? 'success' : 'error'}`}>{title}</div>
        {sub && <div className="result-sub">{sub}</div>}
      </div>
      <button className="btn btn-primary" onClick={onDone} style={{ marginTop: 8 }}>
        Return to Menu
      </button>
    </div>
  );
}