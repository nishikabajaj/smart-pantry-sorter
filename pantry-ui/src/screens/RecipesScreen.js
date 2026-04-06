import { useState } from 'react';
import { apiGet }     from '../api';
import BackButton     from '../components/BackButton';
import LoadingSpinner from '../components/LoadingSpinner';

export default function RecipesScreen({ onBack }) {
  const [loading, setLoading] = useState(false);
  const [recipes, setRecipes] = useState(null);
  const [error, setError]     = useState(null);

  async function fetchRecipes() {
    setLoading(true);
    setError(null);
    try {
      // GET /api/recipes → list of { name, ingredients[] } objects
      const data = await apiGet('/api/recipes');
      setRecipes(data);
    } catch {
      setError('Recipe service unavailable. Ensure /api/recipes is implemented in inventory.py.');
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
      <div className="section-label">Recipe Recommendations</div>

      {error && <div className="banner error">{error}</div>}

      {!recipes ? (
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
        <div className="recipe-empty">
          <div className="recipe-empty-icon">∅</div>
          <div className="recipe-empty-title">No recipes found</div>
          <div className="recipe-empty-sub">
            Add more items to the pantry to unlock suggestions.
          </div>
        </div>
      ) : (
        <>
          {recipes.map((r, i) => (
            <div className="recipe-card" key={i}>
              <div className="recipe-title">{r.name || r.title || `Recipe ${i + 1}`}</div>
              <div className="recipe-meta">
                {r.ingredients?.length
                  ? `Uses: ${r.ingredients.slice(0, 3).join(', ')}`
                  : ''}
              </div>
            </div>
          ))}
          <button className="btn" onClick={fetchRecipes} style={{ marginTop: 8 }}>
            Regenerate
          </button>
        </>
      )}
    </div>
  );
}