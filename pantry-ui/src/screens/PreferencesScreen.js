import { useState, useEffect } from 'react';
import { apiGet, apiPost } from '../api';
import BackButton     from '../components/BackButton';
import LoadingSpinner from '../components/LoadingSpinner';

export default function PreferencesScreen({ onBack }) {
  const [loading, setLoading]         = useState(true);
  const [saving, setSaving]           = useState(false);
  const [error, setError]             = useState(null);
  const [successMsg, setSuccessMsg]   = useState(null);

  const [allFlags, setAllFlags]       = useState([]);   // [{id, flag}]
  const [activeIds, setActiveIds]     = useState(new Set()); // Set<id>
  const [disliked, setDisliked]       = useState([]);   // [{id, ingredient}]
  const [newIngredient, setNewIngredient] = useState('');

  // ── Load ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    apiGet('/api/preferences')
      .then(data => {
        setAllFlags(data.all_diet_flags       ?? []);
        setActiveIds(new Set((data.user_diet_flags ?? []).map(f => f.id)));
        setDisliked(data.disliked_ingredients ?? []);
      })
      .catch(() => setError('Could not load preferences.'))
      .finally(() => setLoading(false));
  }, []);

  // ── Diet flag toggle ───────────────────────────────────────────────────────
  function toggleFlag(id) {
    setActiveIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function saveDietFlags() {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await apiPost('/api/preferences/diet', { flag_ids: [...activeIds] });
      setSuccessMsg('Diet preferences saved.');
    } catch {
      setError('Failed to save diet preferences.');
    } finally {
      setSaving(false);
    }
  }

  // ── Disliked ingredients ───────────────────────────────────────────────────
  async function addIngredient() {
    const val = newIngredient.trim();
    if (!val) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const result = await apiPost('/api/preferences/disliked', { ingredient: val });
      // Avoid duplicates in local state
      setDisliked(prev =>
        prev.some(d => d.id === result.id) ? prev : [...prev, result]
      );
      setNewIngredient('');
      setSuccessMsg(`"${result.ingredient}" added to disliked list.`);
    } catch {
      setError('Failed to add ingredient.');
    } finally {
      setSaving(false);
    }
  }

  async function removeIngredient(ingredient_id) {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);
    try {
      // Use fetch directly for DELETE — extend api.js if you prefer
      await fetch(`/api/preferences/disliked/${ingredient_id}`, { method: 'DELETE' });
      setDisliked(prev => prev.filter(d => d.id !== ingredient_id));
      setSuccessMsg('Ingredient removed.');
    } catch {
      setError('Failed to remove ingredient.');
    } finally {
      setSaving(false);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  if (loading) return (
    <div className="screen">
      <BackButton onClick={onBack} />
      <LoadingSpinner label="Loading preferences" />
    </div>
  );

  return (
    <div className="screen">
      <BackButton onClick={onBack} />
      <div className="section-label">Dietary Preferences</div>

      {error      && <div className="banner error">{error}</div>}
      {successMsg && <div className="banner info">{successMsg}</div>}

      {/* ── Diet flags ─────────────────────────────────────────────────────── */}
      <div className="section-label" style={{ marginTop: 8 }}>Diet Flags</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        {allFlags.map(f => (
          <button
            key={f.id}
            onClick={() => toggleFlag(f.id)}
            className={`btn${activeIds.has(f.id) ? ' btn-primary' : ''}`}
            style={{ padding: '6px 14px', fontSize: 12, textTransform: 'capitalize' }}
          >
            {activeIds.has(f.id) ? '✓ ' : ''}{f.flag}
          </button>
        ))}
      </div>
      <button
        className="btn btn-primary"
        onClick={saveDietFlags}
        disabled={saving}
        style={{ marginBottom: 24 }}
      >
        {saving ? 'Saving…' : 'Save Diet Flags'}
      </button>

      {/* ── Disliked ingredients ────────────────────────────────────────────── */}
      <div className="section-label">Disliked Ingredients</div>
      <div style={{ marginBottom: 8 }}>
        {disliked.length === 0 ? (
          <div style={{ color: 'var(--text-faint)', fontFamily: 'var(--mono)', fontSize: 12 }}>
            None added yet
          </div>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {disliked.map(d => (
              <div
                key={d.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  background: 'var(--surface)', border: '1px solid var(--border)',
                  borderRadius: 6, padding: '4px 10px',
                  fontFamily: 'var(--mono)', fontSize: 12,
                }}
              >
                {d.ingredient}
                <button
                  onClick={() => removeIngredient(d.id)}
                  disabled={saving}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-faint)', fontSize: 14, lineHeight: 1,
                    padding: '0 0 0 4px',
                  }}
                  aria-label={`Remove ${d.ingredient}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <label className="input-label">Add ingredient to avoid</label>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          className="input-field"
          type="text"
          placeholder="e.g. cilantro"
          value={newIngredient}
          onChange={e => setNewIngredient(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addIngredient()}
          style={{ flex: 1 }}
        />
        <button
          className="btn btn-primary"
          onClick={addIngredient}
          disabled={saving || !newIngredient.trim()}
        >
          Add
        </button>
      </div>
    </div>
  );
}