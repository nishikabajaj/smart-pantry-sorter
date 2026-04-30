export default function ScaleReading({ weight }) {
  return (
    <div className="scale-wrap">
      <div className="scale-bars">
        {[...Array(7)].map((_, i) => (
          <div key={i} className="scale-bar" />
        ))}
      </div>
      <div className="scale-display">
        <div className="scale-value">
          {weight !== null ? weight.toFixed(1) : '—'}
        </div>
        <div className="scale-unit">GRAMS</div>
      </div>
      <div className="loader-text">Waiting for stable reading</div>
    </div>
  );
}