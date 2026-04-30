const TILES = [
  { id: 'add',       icon: '＋', label: 'Add Item',    desc: 'Scan & add a new item to the pantry' },
  { id: 'use',       icon: '↑',  label: 'Use Item',    desc: 'Record usage and update quantities' },
  { id: 'remove',    icon: '×',  label: 'Remove Item', desc: 'Permanently remove an item' },
  { id: 'inventory', icon: '≡',  label: 'Inventory',   desc: 'View all items and quantities' },
  { id: 'recipes',   icon: '✦',  label: 'Recipes',     desc: 'Get recommendations from pantry contents', wide: true },
];

export default function HomeScreen({ onNavigate }) {
  return (
    <div className="screen">
      <div className="section-label">Main Menu</div>
      <div className="menu-grid">
        {TILES.map(t => (
          <div
            key={t.id}
            className={`menu-tile${t.wide ? ' wide' : ''}`}
            onClick={() => onNavigate(t.id)}
          >
            <div className="tile-icon">{t.icon}</div>
            <div>
              <div className="tile-label">{t.label}</div>
              <div className="tile-desc">{t.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}