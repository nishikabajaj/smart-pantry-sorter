# Recipe recommender system for the smart pantry sorter project.

# System queries recipe API with "current inventory + dietary prefs"
# Return ranked list

import os, sqlite3, requests, traceback
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), 'pantry.db')

# Set your Spoonacular API key as an environment variable:
#   export SPOONACULAR_API_KEY="your_key_here"
# Or replace the fallback string with your key directly.
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")
 
SPOONACULAR_FIND_BY_INGREDIENTS = "https://api.spoonacular.com/recipes/findByIngredients"
SPOONACULAR_RECIPE_INFO         = "https://api.spoonacular.com/recipes/{id}/information"
 
def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _get_pantry_ingredients() -> list[str]:
    """
    Returns a list of item names currently in the pantry with positive inventory.
    Uses item names rather than ingredient lists so Spoonacular searches by
    product (e.g. 'nutella') rather than sub-ingredients (e.g. 'hazelnuts').
    """
    conn = _get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT mi.name
            FROM InventoryLevels il
            JOIN MasterInventory mi ON mi.id = il.item_id
            WHERE
                COALESCE(il.gross_weight, 0)    > 0
             OR COALESCE(il.liquid_quantity, 0) > 0
             OR COALESCE(il.count, 0)           > 0
        """)
        return [r["name"] for r in cur.fetchall() if r["name"]]
    finally:
        conn.close()
 
 
def _get_user_preferences(user_id: int = 1) -> dict:
    """
    Returns {"diet_flags": [...], "disliked_ingredients": [...]} for user_id.
    Defaults to user 1 (the single-user assumption for this project).
    """
    conn = _get_db()
    try:
        cur = conn.cursor()
 
        cur.execute("""
            SELECT df.flag
            FROM UserDietFlags udf
            JOIN DietFlags df ON df.id = udf.diet_flag_id
            WHERE udf.user_id = ?
        """, (user_id,))
        diet_flags = [r["flag"] for r in cur.fetchall()]
 
        cur.execute("""
            SELECT ing.ingredient
            FROM UserDislikedIngredients udi
            JOIN Ingredients ing ON ing.id = udi.ingredient_id
            WHERE udi.user_id = ?
        """, (user_id,))
        disliked = [r["ingredient"] for r in cur.fetchall()]
 
        return {"diet_flags": diet_flags, "disliked_ingredients": disliked}
    finally:
        conn.close()
 
 
def _spoonacular_diet_param(flags: list[str]) -> str | None:
    """
    Maps our DietFlags values to Spoonacular's accepted diet strings.
    Spoonacular accepts a single diet param; we pick the most restrictive match.
    https://spoonacular.com/food-api/docs#Diets
    """
    PRIORITY = [
        "vegan", "vegetarian", "gluten free", "ketogenic",
        "lacto-vegetarian", "ovo-vegetarian", "paleo",
        "primal", "low fodmap", "whole30",
    ]
    lower_flags = {f.lower() for f in flags}
    for diet in PRIORITY:
        if diet in lower_flags:
            return diet
    return None
 
 
def get_suggestions(user_id: int = 1, number: int = 5) -> list[dict]:
    """
    Main entry point called from flask_app.py.
 
    1. Reads pantry ingredients + user preferences from SQLite.
    2. Calls Spoonacular /recipes/findByIngredients.
    3. For each result fetches /recipes/{id}/information to get full details.
    4. Returns a list of recipe dicts ready to be JSON-serialised.
    """
    ingredients = _get_pantry_ingredients()
    if not ingredients:
        return []
 
    prefs    = _get_user_preferences(user_id)
    diet     = _spoonacular_diet_param(prefs["diet_flags"])
    disliked = prefs["disliked_ingredients"]
 
    # ── Step 1: find recipes by ingredients ──────────────────────────────────
    params = {
        "apiKey":        SPOONACULAR_API_KEY,
        "ingredients":   ",".join(ingredients),
        "number":        number * 2,   # over-fetch so we can filter disliked
        "ranking":       1,            # 1 = maximise used ingredients
        "ignorePantry":  True,
    }
    if diet:
        params["diet"] = diet
 
    try:
        resp = requests.get(SPOONACULAR_FIND_BY_INGREDIENTS, params=params, timeout=10)
        resp.raise_for_status()
        candidates = resp.json()
    except Exception:
        traceback.print_exc()
        return []
 
    if not candidates:
        return []
 
    # ── Step 2: filter out recipes that use disliked ingredients ─────────────
    disliked_lower = {d.lower() for d in disliked}
 
    def _uses_disliked(recipe: dict) -> bool:
        all_used = (recipe.get("usedIngredients") or []) + (recipe.get("missedIngredients") or [])
        for ing in all_used:
            name = (ing.get("name") or "").lower()
            if any(d in name for d in disliked_lower):
                return True
        return False
 
    filtered = [r for r in candidates if not _uses_disliked(r)][:number]
 
    # ── Step 3: fetch full information for each recipe ────────────────────────
    results = []
    for item in filtered:
        recipe_id = item.get("id")
        try:
            info_resp = requests.get(
                SPOONACULAR_RECIPE_INFO.format(id=recipe_id),
                params={"apiKey": SPOONACULAR_API_KEY},
                timeout=10,
            )
            info_resp.raise_for_status()
            info = info_resp.json()
        except Exception:
            traceback.print_exc()
            # Fall back to the partial data from findByIngredients
            info = item
 
        used_names   = [i["name"] for i in (item.get("usedIngredients")  or [])]
        missed_names = [i["name"] for i in (item.get("missedIngredients") or [])]
 
        results.append({
            "id":                  recipe_id,
            "title":               info.get("title") or item.get("title"),
            "image":               info.get("image") or item.get("image"),
            "source_url":          info.get("sourceUrl"),
            "ready_in_minutes":    info.get("readyInMinutes"),
            "servings":            info.get("servings"),
            "summary":             _strip_html(info.get("summary") or ""),
            "used_ingredients":    used_names,
            "missed_ingredients":  missed_names,
            "used_count":          item.get("usedIngredientCount", len(used_names)),
            "missed_count":        item.get("missedIngredientCount", len(missed_names)),
            "diet_flags":          prefs["diet_flags"],
        })
 
    return results
 
 
def _strip_html(text: str) -> str:
    """Remove HTML tags from Spoonacular summary strings."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()