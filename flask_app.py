from flask import Flask, jsonify, request
from flask_cors import CORS
import load_cell
import inventory
import preferences
import recipe
import traceback


app = Flask(__name__)
CORS(app)

# ── One-time setup: ensure default user + seed diet flag options ──────────────
preferences.ensure_default_user()
preferences.seed_diet_flags()

def format_item(db_row):
    if not db_row:
        return None
    row = db_row[0]
    item_id = row[0]

    # pull current inventory level
    inv = inventory.get_inv_level_db(item_id)
    gross = inv[0][1] if inv else None
    liquid = inv[0][2] if inv else None
    count = inv[0][3] if inv else None
    qty  = gross if gross is not None else liquid if liquid is not None else count
    unit = "g" if gross is not None else "oz" if liquid is not None else "units"

    return {
        "id":                    row[0],
        "barcode":               row[1],
        "name":                  row[2],
        "brand":                 row[3],
        "category":              row[4],
        "current_quantity":      qty,
        "product_quantity_unit": unit,
    }


@app.route('/api/data', methods=['GET', 'POST'])
def api_data():
    return jsonify(inventory.view_all_inventory())

# Called when user submits a barcode from the scan screen.
# Returns item_data dict and whether it's a new item.
@app.route('/api/scan', methods=['POST'])
def api_scan():
    barcode = request.json.get("barcode")
    if not barcode:
        return jsonify({"error": "No barcode provided"}), 400
 
    item_data = inventory.get_master_db(barcode)
    if item_data:
        return jsonify({"item_data": format_item(item_data), "new": False})
 
    try:
        raw = inventory.get_off_product(barcode)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502

    if not isinstance(raw, dict) or raw.get("status") != 1:
        return jsonify({"error": "Item not found"}), 404
 
    filter_keys = [
        "code", "product_name", "brands", "categories",
        "ingredients", "allergens", "traces",
        "product_quantity", "product_quantity_unit"
    ]
    
    product = raw.get("product", {})
    item_data = {k: product.get(k) for k in filter_keys}

    display_data = {**item_data}
    display_data["name"]  = item_data.get("product_name") or "Unknown Item"
    display_data["brands"]        = [b.strip() for b in (product.get("brands") or "").split(",") if b.strip()]
    display_data["ingredients"]   = [i.get("text", "") if isinstance(i, dict) else i for i in (product.get("ingredients") or [])]
    display_data["allergens"]     = [a.split(":")[-1].strip() for a in (product.get("allergens_tags") or []) if a.strip()]
    display_data["categories"]    = [c.strip() for c in (product.get("categories") or "").split(",") if c.strip()]

    return jsonify({"item_data": display_data, "new": True})
 
 
# Polled by the UI while the scale animation is showing.
# Returns current reading and whether it has stabilised.
@app.route('/api/weight', methods=['GET'])
def api_weight():
    first  = load_cell.get_weight_g()
    second = load_cell.get_weight_g()
    stable = abs(second - first) <= 2.0 and second > 5.0
    return jsonify({"grams": round(second, 1), "stable": stable})
 
 
# Triggered after confirm (+optional weight) on the Add screen.
@app.route('/api/add', methods=['POST'])
def api_add():
    body      = request.json
    item_data = body.get("item_data")
    new       = body.get("new", True)
    weight_g  = body.get("weight_g")          # pre-measured on client side
 
    if weight_g is not None and item_data:
        item_data["product_quantity"]      = weight_g
        item_data["product_quantity_unit"] = "g"
 
    try:
        inventory.add_inventory(item_data, new)
        return jsonify({"ok": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
 
 
@app.route('/api/update', methods=['POST'])
def api_update():
    body           = request.json
    item_data      = body.get("item_data")
    remaining_weight = body.get("remaining_weight")
    usage          = body.get("usage")

    # item_data from UseScreen is a scan dict — look up the DB row by barcode
    barcode = item_data.get("barcode") or item_data.get("code")
    if not barcode:
        return jsonify({"error": "No barcode in item_data"}), 400

    db_row = inventory.get_master_db(barcode)
    if not db_row:
        return jsonify({"error": "Item not found in database"}), 404

    try:
        inventory.update_inventory(db_row, remaining_weight=remaining_weight, usage=usage)
        return jsonify({"ok": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
 
 
@app.route('/api/remove', methods=['POST'])
def api_remove():
    body      = request.json
    item_data = body.get("item_data")
    try:
        inventory.remove_inventory(item_data)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
 
 
@app.route('/api/recipes', methods=['GET'])
def api_recipes():
    try:
        suggestions = recipe.get_suggestions(user_id=1, number=5)
        return jsonify(suggestions)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/preferences', methods=['GET'])
def api_get_preferences():
    """
    Returns the full preferences state for user 1:
    {
      "all_diet_flags":         [{"id": 1, "flag": "vegan"}, ...],
      "user_diet_flags":        [{"id": 2, "flag": "vegetarian"}],
      "disliked_ingredients":   [{"id": 5, "ingredient": "cilantro"}]
    }
    """
    try:
        return jsonify({
            "all_diet_flags":       preferences.get_all_diet_flags(),
            "user_diet_flags":      preferences.get_user_diet_flags(user_id=1),
            "disliked_ingredients": preferences.get_user_disliked_ingredients(user_id=1),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
 
 
@app.route('/api/preferences/diet', methods=['POST'])
def api_set_diet_flags():
    """
    Body: { "flag_ids": [1, 3, 5] }
    Replaces the user's active diet flags.
    """
    flag_ids = request.json.get("flag_ids", [])
    try:
        preferences.set_user_diet_flags(flag_ids, user_id=1)
        return jsonify({"ok": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
 
 
@app.route('/api/preferences/disliked', methods=['POST'])
def api_add_disliked():
    """
    Body: { "ingredient": "cilantro" }
    Adds one ingredient to the disliked list.
    """
    ingredient = (request.json.get("ingredient") or "").strip()
    if not ingredient:
        return jsonify({"error": "ingredient required"}), 400
    try:
        result = preferences.add_disliked_ingredient(ingredient, user_id=1)
        return jsonify(result)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
 
 
@app.route('/api/preferences/disliked/<int:ingredient_id>', methods=['DELETE'])
def api_remove_disliked(ingredient_id):
    """Removes one ingredient from the disliked list by its ID."""
    try:
        preferences.remove_disliked_ingredient(ingredient_id, user_id=1)
        return jsonify({"ok": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
    
# Run with python flask_app.py. Test at http://localhost:5000/api/data