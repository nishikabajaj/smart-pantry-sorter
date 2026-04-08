from flask import Flask, jsonify, request
from flask_cors import CORS
from load_cell import LoadCell
import inventory


app = Flask(__name__)
CORS(app)

def format_item(db_row):
    """Convert a MasterInventory DB row to a JSON-serialisable dict for the UI.
    Columns: id, barcode, name, brand, category_id
    """
    if not db_row:
        return None
    row = db_row[0]
    return {
        "id":       row[0],
        "barcode":  row[1],
        "name":     row[2],
        "brand":    row[3],
        "category": row[4],
    }


@app.route('/api/data', methods=['GET', 'POST'])
def api_data():
    result = inventory.view_all_inventory()
    return jsonify(result)

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
 
    # Not in local DB — call OpenFoodFacts
    raw = inventory.get_off_product(barcode)
    if not isinstance(raw, dict) or raw.get("status") != 1:
        return jsonify({"error": "Item not found"}), 404
 
    filter_keys = [
        "code", "product_name", "brands", "categories",
        "ingredients", "allergens", "traces",
        "product_quantity", "product_quantity_unit"
    ]
    item_data = {k: raw.get("product", {}).get(k) for k in filter_keys}
    return jsonify({"item_data": item_data, "new": True})
 
 
# Polled by the UI while the scale animation is showing.
# Returns current reading and whether it has stabilised.
@app.route('/api/weight', methods=['GET'])
def api_weight():
    grams  = LoadCell._load_cell.get_weight_g()
    stable = LoadCell._load_cell.stable_weight_g() is not None   # use stable_weight_g for real impl
    return jsonify({"grams": round(grams, 1), "stable": stable})
 
 
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
        return jsonify({"error": str(e)}), 500
 
 
@app.route('/api/update', methods=['POST'])
def api_update():
    body      = request.json
    item_data = body.get("item_data")
    try:
        inventory.update_inventory(item_data)
        return jsonify({"ok": True})
    except Exception as e:
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
 
 
# TODO: implement in recipe.py and call from here.
# Should query inventorylevels, pull ingredient names, and return suggestions.
@app.route('/api/recipes', methods=['GET'])
def api_recipes():
    # TODO: implement recipe.py and call it here
    # Example: return jsonify(recipe.get_suggestions())
    return jsonify([])   # returns empty list until recipe.py is built


if __name__ == '__main__':
    app.run(port=5000)
    
# Run with python flask_app.py. Test at http://localhost:5000/api/data