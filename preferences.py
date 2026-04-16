"""
preferences.py
──────────────
DB helpers for reading and writing user diet flags and disliked ingredients.
All functions default to user_id=1 (single-user device assumption).

Tables used:
  User, DietFlags, Ingredients,
  UserDietFlags, UserDislikedIngredients
"""

import os
import sqlite3
import traceback

DB_PATH = os.path.join(os.path.dirname(__file__), 'pantry.db')

# ── Supported diet flags (kept in sync with the DietFlags seed below) ────────
SUPPORTED_DIET_FLAGS = [
    "vegan",
    "vegetarian",
    "gluten free",
    "ketogenic",
    "lacto-vegetarian",
    "ovo-vegetarian",
    "paleo",
    "primal",
    "low fodmap",
    "whole30",
]


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Seed helpers ─────────────────────────────────────────────────────────────

def ensure_default_user():
    """
    Inserts the default user (id=1, name='User') if it doesn't exist yet.
    Call this once at app start-up (flask_app.py does this).
    """
    conn = _get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO User (id, name) VALUES (1, 'User')"
        )
        conn.commit()
    finally:
        conn.close()


def seed_diet_flags():
    """
    Populates the DietFlags table with SUPPORTED_DIET_FLAGS if empty.
    Safe to call multiple times (uses INSERT OR IGNORE).
    """
    conn = _get_db()
    try:
        for flag in SUPPORTED_DIET_FLAGS:
            conn.execute(
                "INSERT OR IGNORE INTO DietFlags (flag) VALUES (?)", (flag,)
            )
        conn.commit()
    finally:
        conn.close()


# ── Diet flags ────────────────────────────────────────────────────────────────

def get_all_diet_flags() -> list[dict]:
    """Returns every available diet flag: [{"id": 1, "flag": "vegan"}, ...]"""
    conn = _get_db()
    try:
        rows = conn.execute("SELECT id, flag FROM DietFlags ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_user_diet_flags(user_id: int = 1) -> list[dict]:
    """Returns the diet flags currently active for this user."""
    conn = _get_db()
    try:
        rows = conn.execute("""
            SELECT df.id, df.flag
            FROM UserDietFlags udf
            JOIN DietFlags df ON df.id = udf.diet_flag_id
            WHERE udf.user_id = ?
            ORDER BY df.id
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def set_user_diet_flags(flag_ids: list[int], user_id: int = 1) -> None:
    """
    Replaces the user's diet flags with the supplied list of DietFlag IDs.
    Passing an empty list clears all flags.
    """
    conn = _get_db()
    try:
        conn.execute("DELETE FROM UserDietFlags WHERE user_id = ?", (user_id,))
        for fid in flag_ids:
            conn.execute(
                "INSERT OR IGNORE INTO UserDietFlags (user_id, diet_flag_id) VALUES (?, ?)",
                (user_id, fid),
            )
        conn.commit()
    finally:
        conn.close()


# ── Disliked ingredients ──────────────────────────────────────────────────────

def get_user_disliked_ingredients(user_id: int = 1) -> list[dict]:
    """Returns the disliked ingredients for this user."""
    conn = _get_db()
    try:
        rows = conn.execute("""
            SELECT ing.id, ing.ingredient
            FROM UserDislikedIngredients udi
            JOIN Ingredients ing ON ing.id = udi.ingredient_id
            WHERE udi.user_id = ?
            ORDER BY ing.ingredient
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_disliked_ingredient(ingredient_name: str, user_id: int = 1) -> dict:
    """
    Adds an ingredient to the user's disliked list.
    Creates the ingredient in the Ingredients table if it doesn't exist yet.
    Returns {"id": <ingredient_id>, "ingredient": <name>}.
    """
    conn = _get_db()
    try:
        # Upsert into Ingredients
        conn.execute(
            "INSERT OR IGNORE INTO Ingredients (ingredient) VALUES (?)",
            (ingredient_name.strip().lower(),),
        )
        conn.commit()

        row = conn.execute(
            "SELECT id FROM Ingredients WHERE ingredient = ?",
            (ingredient_name.strip().lower(),),
        ).fetchone()
        ingredient_id = row["id"]

        conn.execute(
            "INSERT OR IGNORE INTO UserDislikedIngredients (user_id, ingredient_id) VALUES (?, ?)",
            (user_id, ingredient_id),
        )
        conn.commit()
        return {"id": ingredient_id, "ingredient": ingredient_name.strip().lower()}
    except Exception:
        traceback.print_exc()
        raise
    finally:
        conn.close()


def remove_disliked_ingredient(ingredient_id: int, user_id: int = 1) -> None:
    """Removes one ingredient from the user's disliked list."""
    conn = _get_db()
    try:
        conn.execute(
            "DELETE FROM UserDislikedIngredients WHERE user_id = ? AND ingredient_id = ?",
            (user_id, ingredient_id),
        )
        conn.commit()
    finally:
        conn.close()