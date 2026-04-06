export default function ItemCard({ item }) {
  if (!item) return null;

  const fields = [
    ['Category',    item.category],
    ['Quantity',    item.quantity ? `${item.quantity} ${item.unit || ''}`.trim() : null],
    ['Bin',         item.bin_id   ? `Bin ${item.bin_id}` : null],
    ['Allergens',   item.allergens?.length   ? item.allergens : null],
    ['Ingredients', item.ingredients?.length ? item.ingredients.slice(0, 5) : null],
  ].filter(([, v]) => v);

  return (
    <div className="item-card">
      <div className="item-card-header">
        <div className="item-card-name">{item.name || 'Unknown Item'}</div>
        <div className="item-card-brand">{item.brand || '—'}</div>
      </div>
      <div className="item-card-body">
        {fields.map(([key, val]) => (
          <div className="item-row" key={key}>
            <span className="item-row-key">{key}</span>
            <span className="item-row-val">
              {Array.isArray(val) ? (
                <div className="tags">
                  {val.map((v, i) => (
                    <span key={i} className="badge">{v}</span>
                  ))}
                </div>
              ) : val}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}