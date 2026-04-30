export default function LoadingSpinner({ label, sub }) {
  return (
    <div className="loading-wrap">
      <div className="loader-ring" />
      <div>
        <div className="loader-text">{label || 'Processing'}</div>
        {sub && <div className="loader-sub">{sub}</div>}
      </div>
    </div>
  );
}