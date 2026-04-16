import { useState } from 'react';
import { apiGet }     from '../api';
import BackButton     from '../components/BackButton';
import LoadingSpinner from '../components/LoadingSpinner';

export default function RecipesScreen({ onBack, onNavigate }) {
  const [loading, setLoading] = useState(false);
  const [recipes, setRecipes] = useState(null);
  const [error, setError]     = useState(null);

  async function fetchRecipes() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet('/api/recipes');
      setRecipes(Array.isArray(data) ? data : []);
    } catch {
      setError('Recipe service unavailable. Check that SPOONACULAR_API_KEY is set and the server is running.');
    } finally {
      setLoading(false);
    }
  }

  if (loading) return (
    <div className="screen">
      <BackButton onClick={onBack} />
      <LoadingSpinner label="Finding recipes" sub="Scanning pantry contents…" />
    </div>
  );

  return (
    <div className="screen">
      <BackButton onClick={onBack} />

      {/* Header row with preferences shortcut */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <div className="section-label" style={{ marginBottom: 0 }}>Recipe Recommendations</div>
        {onNavigate && (
          <button
            className="btn"
            style={{ fontSize: 11, padding: '4px 10px' }}
            onClick={() => onNavigate('preferences')}
          >
            ⚙ Diet Prefs
          </button>
        )}
      </div>

      {error && <div className="banner error">{error}</div>}

      {!recipes ? (
        /* ── Empty state ─────────────────────────────────────────────────── */
        <div className="recipe-empty">
          <div className="recipe-empty-icon">✦</div>
          <div className="recipe-empty-title">What can I make?</div>
          <div className="recipe-empty-sub" style={{ marginBottom: 28 }}>
            Generate recipe ideas based on what's currently in your pantry.
          </div>
          <button className="btn btn-primary" onClick={fetchRecipes}>
            Generate Recipes
          </button>
        </div>
      ) : recipes.length === 0 ? (
        /* ── No results ──────────────────────────────────────────────────── */
        <div className="recipe-empty">
          <div className="recipe-empty-icon">∅</div>
          <div className="recipe-empty-title">No recipes found</div>
          <div className="recipe-empty-sub">
            Add more items to the pantry or adjust your dietary preferences.
          </div>
          {onNavigate && (
            <button className="btn" onClick={() => onNavigate('preferences')}>
              Edit Preferences
            </button>
          )}
        </div>
      ) : (
        /* ── Results ─────────────────────────────────────────────────────── */
        <>
          {/* Active diet flags badge strip */}
          {recipes[0]?.diet_flags?.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
              {recipes[0].diet_flags.map(f => (
                <span
                  key={f}
                  style={{
                    fontFamily: 'var(--mono)', fontSize: 10,
                    background: 'var(--surface)', border: '1px solid var(--border)',
                    borderRadius: 4, padding: '2px 8px',
                    textTransform: 'capitalize', color: 'var(--text-faint)',
                  }}
                >
                  {f}
                </span>
              ))}
            </div>
          )}

          {recipes.map((r, i) => (
            <RecipeCard key={r.id ?? i} recipe={r} />
          ))}

          <button className="btn" onClick={fetchRecipes} style={{ marginTop: 8 }}>
            Regenerate
          </button>
        </>
      )}
    </div>
  );
}


function RecipeCard({ recipe: r }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="recipe-card" style={{ cursor: 'pointer' }} onClick={() => setExpanded(e => !e)}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        {r.image && (
          <img
            src={r.image}
            alt={r.title}
            style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 6, flexShrink: 0 }}
          />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="recipe-title">{r.title}</div>

          {/* Meta row */}
          <div className="recipe-meta" style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {r.ready_in_minutes && (
              <span>⏱ {r.ready_in_minutes} min</span>
            )}
            {r.servings && (
              <span>🍽 {r.servings} servings</span>
            )}
            <span style={{ color: 'var(--success, #4caf50)' }}>
              ✓ {r.used_count} from pantry
            </span>
            {r.missed_count > 0 && (
              <span style={{ color: 'var(--text-faint)' }}>
                + {r.missed_count} needed
              </span>
            )}
          </div>
        </div>
        <span style={{ color: 'var(--text-faint)', fontSize: 12 }}>{expanded ? '▲' : '▼'}</span>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ marginTop: 12 }} onClick={e => e.stopPropagation()}>
          {r.used_ingredients?.length > 0 && (
            <>
              <div className="input-label">From your pantry</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--success, #4caf50)', marginBottom: 6 }}>
                {r.used_ingredients.join(' · ')}
              </div>
            </>
          )}
          {r.missed_ingredients?.length > 0 && (
            <>
              <div className="input-label">Still needed</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text-faint)', marginBottom: 6 }}>
                {r.missed_ingredients.join(' · ')}
              </div>
            </>
          )}
          {r.summary && (
            <div style={{ fontSize: 12, lineHeight: 1.5, color: 'var(--text-secondary)', marginBottom: 8 }}>
              {r.summary.length > 300 ? r.summary.slice(0, 300) + '…' : r.summary}
            </div>
          )}
          {r.source_url && (
            <a
              href={r.source_url}
              target="_blank"
              rel="noreferrer"
              className="btn"
              style={{ fontSize: 11, padding: '6px 12px', display: 'inline-block' }}
            >
              View Full Recipe ↗
            </a>
          )}
        </div>
      )}
    </div>
  );
}