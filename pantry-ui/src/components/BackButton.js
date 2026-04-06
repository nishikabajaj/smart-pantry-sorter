export default function BackButton({ onClick }) {
  return (
    <button className="back-btn" onClick={onClick}>
      <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M8 2L4 6l4 4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Back
    </button>
  );
}