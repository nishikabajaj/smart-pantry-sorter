# Inventory management system for the smart pantry sorter project.

from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
from loadcell import LoadCell
import pyodbc, requests, atexit


# Single LoadCell instance shared for lifetime of this process
_load_cell = LoadCell()

# print(pyodbc.drivers()) # Confirm that the Microsoft ODBC Driver for SQL Server is installed.

app = Flask(__name__)
CORS(app)

@app.route('/api/data', methods=['GET', 'POST'])
def api_data():
    result = view_all_inventory()
    return jsonify(result)


def get_data(query, params=None, one=False):
    # connection string for Python -> DB
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=FoodPantryDB;'
        'Trusted_Connection=yes;'
    )
    cursor = conn.cursor()
    cursor.execute(query, params or ()) # Use cursor.execute() to run queries
    result = cursor.fetchone() if one else cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def execute_query(query, data=None):
    # connection string for Python -> DB
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=FoodPantryDB;'
        'Trusted_Connection=yes;'
    )
    cursor = conn.cursor()
    cursor.execute(query, data) # Use cursor.execute() to run queries
    conn.commit()
    cursor.close()
    conn.close()

    # fetchone() gets next single row as a tuple; row by row processing
    # fetchmany(size) returns batch of rows up to specified size
    # fetchall() grabs all rows as list of tuples


def get_off_product(barcode): # Calls the OpenFoodFacts API to identify an item based on barcode
    try:
        url = f"https://world.openfoodfacts.net/api/v2/product/{barcode}.json"
        headers: dict[str, str] = {"User-Agent": "FoodPantrySorter/1.0 (nishikabajaj@tamu.edu)"}
        data = requests.get(url, headers=headers, timeout=10)
        data.raise_for_status()
        return data.json()
    
    except requests.exceptions.RequestException as e:
        # Handle connection errors, timeouts, etc.
        return jsonify({"error": str(e)}), 500


def get_master_db(barcode): # Check if an item is present in the local database's MasterInventory table; helps to avoid calling external API unecessarily
    q = "SELECT * FROM masterinventory WHERE barcode = ?"
    result = get_data(q, (barcode,))
    return result


def get_category_db(category): # Check if a category is present in the local database's ItemCategory table
    q = "SELECT * FROM itemcategory WHERE category = ?"
    result = get_data(q, (category,))
    return result


def get_inv_level_db(item_id): # Check if an item is present in the local database's InventoryLevels table
    q = "SELECT * FROM inventorylevels WHERE item_id = ?"
    result = get_data(q, (item_id,))
    return result
  
    
def get_bin_db(category_id): # Check if an item is present in the local database's Bin table
    q = "SELECT * FROM bin WHERE category_id = ?"
    result = get_data(q, (category_id,))
    
    return result


def add_inventory(item_data, new): # Add an item to the inventory and its respective diet flags, ingredients, and item category
    """
    JSON value to DB table mapping:

    MasterInventory - code, name, brand, category, diet_flags
    Ingredients - ingredients parsed from ingredient text
    DietFlags - allergen and dietary labels
    InventoryLevels - count, weight, quantity, location bin, expiration date
    
    """
    if new:
        # Extract all data from JSON dictionary
        barcode = item_data["code"]
        name = item_data["product_name"]
        brand = item_data["brands"][0]
        category = item_data["categories"][0]
        product_quantity = item_data["product_quantity"]
        product_quantity_unit = item_data["product_quantity_unit"]
        
        delimiter = ":"
        allergens = [a.split(delimiter)[-1] for a in item_data["allergens"]]
        
        ingredients = [i["text"] for i in item_data["ingredients"]]
    
        # Add category to ItemCategory if it doesn't exist already
        item_category_q = (
            "IF NOT EXISTS (SELECT 1 FROM itemcategory WHERE category = ?) "
            "BEGIN INSERT INTO itemcategory (category) VALUES (?) END "
            "SELECT id FROM itemcategory WHERE category = ?"
        )
        category_result = get_data(item_category_q, (category, category, category,))
        category_id = category_result[0][0]
    
        bin_q = (
            "IF NOT EXISTS (SELECT 1 FROM bin WHERE category_id = ?) "
            "BEGIN INSERT INTO bin (category_id) VALUES (?) END "
            "SELECT id FROM bin WHERE category_id = ?"
        )
        bin_result = get_data(bin_q, (category_id, category_id, category_id,))
        bin_id = bin_result[0][0]
    
        master_inv_q = (
            "IF NOT EXISTS (SELECT 1 FROM masterinventory WHERE barcode = ?) "
            "BEGIN INSERT INTO masterinventory (barcode, name, brand, category) VALUES (?, ?, ?, ?) END "
            "SELECT id FROM masterinventory WHERE barcode = ?"
        )
        item_result = get_data(master_inv_q, (barcode, barcode, name, brand, category_id, barcode))
        item_id = item_result[0][0]
        
        # TODO: UPDATE WITH LOAD CELL LOGIC
        item_quantity_col = ""
        if product_quantity_unit == "g":
            item_quantity_col = "gross_weight"
            print("Place the item on the platform and wait...")
            product_quantity = _load_cell.stable_weight_g()
            print(f"Measured weight: {product_quantity:.1f}")
        
        elif product_quantity_unit == "oz":
            # Liquid/volume items: used the package stated quantity
            item_quantity_col = "liquid_quantity"
            
        else:
            # Countable item (no weight/volume tracked)
            item_quantity_col = "count"
            product_quantity = int(input("Enter count to add: "))
    
        for a in allergens:
            diet_flags_q = (
                "IF NOT EXISTS (SELECT 1 FROM dietflags WHERE flag = ?) "
                "BEGIN INSERT INTO dietflags (flag) VALUES (?) END "
                "SELECT id FROM dietflags WHERE flag = ?"
            )
            diet_flag_result = get_data(diet_flags_q, (a, a, a))
            diet_flag_id = diet_flag_result[0][0]
 
            master_diet_q = (
                "IF NOT EXISTS (SELECT 1 FROM masterinventorydietflags "
                "WHERE master_inventory_id = ? AND diet_flag_id = ?) "
                "BEGIN INSERT INTO masterinventorydietflags (master_inventory_id, diet_flag_id) "
                "VALUES (?, ?) END"
            )
            execute_query(master_diet_q, (item_id, diet_flag_id, item_id, diet_flag_id))
 
        for i in ingredients:
            ingredients_q = (
                "IF NOT EXISTS (SELECT 1 FROM ingredients WHERE ingredient = ?) "
                "BEGIN INSERT INTO ingredients (ingredient) VALUES (?) END "
                "SELECT id FROM ingredients WHERE ingredient = ?"
            )
            ingredient_result = get_data(ingredients_q, (i, i, i))
            ingredient_id = ingredient_result[0][0]
 
            master_ing_q = (
                "IF NOT EXISTS (SELECT 1 FROM masterinventoryingredients "
                "WHERE master_inventory_id = ? AND ingredient_id = ?) "
                "BEGIN INSERT INTO masterinventoryingredients (master_inventory_id, ingredient_id) "
                "VALUES (?, ?) END"
            )
            execute_query(master_ing_q, (item_id, ingredient_id, item_id, ingredient_id))
    
    else: # Extract data from DB dictionary
        # Columns: id, barcode, name, brand, category
        item = item_data[0]
        item_id = item[0]
        # barcode = item[1]
        # name = item[2]
        # brand = item[3]
        category_id = item[4]
        bin_id = get_bin_db(category_id)[0][0]
        
        # For known items (re-stocking a barcode already in MasterInventory),
        # check the existing inventory level to determine the correct column,
        # then weigh the item being added.
        existing = get_inv_level_db(item_id)
        if existing and existing[0][2] is not None:
            # gross_weight column (index 2) is already populated for this item
            item_quantity_col = "gross_weight"
            print("Place the item on the scale and hold still...")
            product_quantity = _load_cell.stable_weight_g()
            print(f"Measured weight: {product_quantity:.1f} g")
            
        elif existing and existing[0][3] is not None:
            # liquid_quantity column (index 3) is populated
            item_quantity_col = "liquid_quantity"
            product_quantity = float(input("Enter liquid quantity (oz): "))
            
        else:
            # Countable item (no weight/volume tracked)
            item_quantity_col = "count"
            product_quantity = int(input("Enter count to add: "))
    
    inv_levels_q = (
        f"IF NOT EXISTS (SELECT 1 FROM inventorylevels WHERE item_id = ?) "
        f"BEGIN INSERT INTO inventorylevels (item_id, {item_quantity_col}, location_bin_id) "
        f"VALUES (?, ?, ?) END"
    )
    execute_query(inv_levels_q, (item_id, item_id, product_quantity, bin_id))
 
    transaction_q = (
        f"INSERT INTO transactions (item_id, action, date, {item_quantity_col}, current_location) "
        f"VALUES (?, ?, ?, ?, ?)"
    )
    execute_query(transaction_q, (item_id, "ADD", datetime.now(), product_quantity, bin_id))
        
    print("Success! Item added to pantry!")
    
    
def update_inventory(item_data):    
    # Extract data from DB dictionary
    # Columns: id, barcode, name, brand, category
    item = item_data[0]
    item_id = item[0]
    # barcode = item[1]
    # name = item[2]
    # brand = item[3]
    # category_id = item[4]
    # bin_id = get_bin_db(category_id)[0][0]
    
    inv_level = get_inv_level_db(item_id)[0]
    
    # First check if item is new -- avoid user error, if it is, return error for user to add new item
    if not inv_level:
        print("Error: This item needs to be added to the pantry first!")
        return
    
    inv_level = inv_level[0] # unwrap first and expected only row
    gross_weight = inv_level[1]
    liquid_quantity = inv_level[2]
    count = inv_level[3]
    location_bin_id = inv_level[5]
    expiration_date = inv_level[5]
    
    item_quantity_col = ""
    
    if gross_weight is not None:
        item_quantity_col = "gross_weight"
        
        # Weigh the item after use to compute consumption by difference.
        # Ask the user to place the item back on the scale; the load cell
        # measures the remaining weight and we diff against the DB value.
        
        print("Place the item back on the scale to measure remaining weight...")
        remaining = _load_cell.stable_weight_g()
        print(f"Remaining weight: {remaining:.1f} g  (was {gross_weight:.1f} g)")
        usage = gross_weight - remaining
        if usage < 0:
            # Remaining reads heavier than recorded -- likely a calibration drift;
            # clamp to 0 so we don't write a negative usage.
            print(f"Warning: measured remaining ({remaining:.1f} g) > stored ({gross_weight:.1f} g). "
                  "Check calibration. No update applied.")
            return
        new_value = remaining
        
    elif liquid_quantity is not None:
        item_quantity_col = "liquid_quantity"
        usage = float(input("Insert how much you used (oz): "))
        new_value = (liquid_quantity or 0) - usage
    
    else:
        # Countable item (no weight/volume tracked)
        item_quantity_col = "count"
        usage = int(input("Enter usage count: "))
        new_value = (count - usage)
        
 
    update_q = f"UPDATE inventorylevels SET {item_quantity_col} = ? WHERE item_id = ?"
    execute_query(update_q, (new_value, item_id))
 
    print("Success! Inventory updated!")

def remove_inventory(item_data):
    # Extract data from DB dictionary
    # Columns: id, barcode, name, brand, category
    item = item_data[0]
    item_id = item[0]
    name = item[2]
    
    confirmation = input(f"Confirm deletion of {name}. Input y/n")
    if confirmation.lower() == "y":
        q = "DELETE FROM inventorylevels WHERE item_id = %s"
        execute_query(q, item_id)
        print("Item deleted from pantry")
        
    else:
        print("Cancelled, item has not been removed from pantry")
    
def view_all_inventory():
    q = "SELECT * FROM inventorylevels"
    result = get_data(q)
    print(result)
    return result

atexit.register(_load_cell.cleanup)

if __name__ == '__main__':
    app.run(port=5000)
    
# Run with python inventory.py. Test at http://localhost:5000/api/data