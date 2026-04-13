# Inventory management system for the smart pantry sorter project.

from datetime import datetime
import load_cell
import sqlite3, requests, atexit, sorting, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'pantry.db')

def get_data(query, params=None, one=False):
    # connection string for Python -> DB
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # allows access to columns by name
    cursor = conn.cursor()
    cursor.execute(query, params or ()) # Use cursor.execute() to run queries
    result = cursor.fetchone() if one else cursor.fetchall()
    cursor.close()
    conn.close()
    return result


def execute_query(query, data=None):
    # connection string for Python -> DB
    conn = sqlite3.connect(DB_PATH)
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
    
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 500
        raise RuntimeError(f"OpenFoodFacts HTTP error {status}: {str(e)}")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"OpenFoodFacts request failed: {str(e)}")


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
        allergens = [a.split(delimiter)[-1] if delimiter in a else a for a in item_data["allergens"]]
        
        ingredients = [i["text"] if isinstance(i, dict) else i for i in item_data["ingredients"]]
    
        # Add category to ItemCategory if it doesn't exist already
        execute_query("INSERT OR IGNORE INTO itemcategory (category) VALUES (?)", (category,))
        category_result = get_data("SELECT id FROM itemcategory WHERE category = ?", (category,))
        category_id = category_result[0][0]
        
        execute_query("INSERT OR IGNORE INTO bin (category_id) VALUES (?)", (category_id,))
        bin_result = get_data("SELECT id FROM bin WHERE category_id = ?", (category_id,))
        bin_id = bin_result[0][0]
    
        execute_query(
            "INSERT OR IGNORE INTO masterinventory (barcode, name, brand, category) VALUES (?, ?, ?, ?)",
            (barcode, name, brand, category_id)
        )
        item_result = get_data("SELECT id FROM masterinventory WHERE barcode = ?", (barcode,))
        item_id = item_result[0][0]
        
        item_quantity_col = ""
        if product_quantity_unit == "g":
            item_quantity_col = "gross_weight"
            print(f"Using pre-measured weight: {product_quantity:.1f} g")
        
        elif product_quantity_unit == "oz":
            # Liquid/volume items: used the package stated quantity
            item_quantity_col = "liquid_quantity"
            
        else:
            # Countable item (no weight/volume tracked)
            item_quantity_col = "count"
            product_quantity = int(input("Enter count to add: "))
    
        for a in allergens:
            execute_query("INSERT OR IGNORE INTO dietflags (flag) VALUES (?)", (a,))
            diet_flag_result = get_data("SELECT id FROM dietflags WHERE flag = ?", (a,))
            diet_flag_id = diet_flag_result[0][0]
            execute_query(
                "INSERT OR IGNORE INTO masterinventorydietflags (master_inventory_id, diet_flag_id) VALUES (?, ?)",
                (item_id, diet_flag_id)
            )
 
        for i in ingredients:
            execute_query("INSERT OR IGNORE INTO ingredients (ingredient) VALUES (?)", (i,))
            ingredient_result = get_data("SELECT id FROM ingredients WHERE ingredient = ?", (i,))
            ingredient_id = ingredient_result[0][0]
            execute_query(
                "INSERT OR IGNORE INTO masterinventoryingredients (master_inventory_id, ingredient_id) VALUES (?, ?)",
                (item_id, ingredient_id)
            )
 
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
    f"INSERT OR IGNORE INTO inventorylevels (item_id, {item_quantity_col}, location_bin_id) "
    f"VALUES (?, ?, ?)"
    )
    execute_query(inv_levels_q, (item_id, product_quantity, bin_id))
 
    transaction_q = (
        f"INSERT INTO transactions (item_id, action, date, {item_quantity_col}, current_location) "
        f"VALUES (?, ?, ?, ?, ?)"
    )
    execute_query(transaction_q, (item_id, "ADD", datetime.now().isoformat(), product_quantity, bin_id))
    
    sorting.sort_item(item_id)
    
    print("Success! Item added to pantry!")
    
    
def update_inventory(item_data, remaining_weight=None, usage=None):
    item = item_data[0]
    item_id = item[0]

    inv_level_rows = get_inv_level_db(item_id)
    if not inv_level_rows:
        raise ValueError("This item needs to be added to the pantry first!")

    inv_level       = inv_level_rows[0]
    gross_weight    = inv_level[1]
    liquid_quantity = inv_level[2]
    count           = inv_level[3]

    if gross_weight is not None:
        item_quantity_col = "gross_weight"
        if remaining_weight is not None:
            new_value = remaining_weight
        elif usage is not None:
            new_value = gross_weight - usage   # manual: subtract usage from stored
        else:
            raise ValueError("No remaining_weight or usage provided for weighed item.")

    elif liquid_quantity is not None:
        item_quantity_col = "liquid_quantity"
        if usage is None:
            raise ValueError("No usage provided for liquid item.")
        new_value = (liquid_quantity or 0) - usage

    else:
        item_quantity_col = "count"
        if usage is None:
            raise ValueError("No usage provided for count item.")
        new_value = (count or 0) - int(usage)

    execute_query(
        f"UPDATE inventorylevels SET {item_quantity_col} = ? WHERE item_id = ?",
        (new_value, item_id)
    )
    sorting.sort_item(item_id)
    print("Inventory updated!")
    item = item_data[0]
    item_id = item[0]

    inv_level_rows = get_inv_level_db(item_id)
    if not inv_level_rows:
        raise ValueError("This item needs to be added to the pantry first!")

    inv_level       = inv_level_rows[0]
    gross_weight    = inv_level[1]
    liquid_quantity = inv_level[2]
    count           = inv_level[3]

    if gross_weight is not None:
        item_quantity_col = "gross_weight"
        if remaining_weight is not None:
            new_value = remaining_weight
        else:
            # fallback to scale if called from CLI
            print("Place the item back on the scale...")
            new_value = load_cell.stable_weight_g()

    elif liquid_quantity is not None:
        item_quantity_col = "liquid_quantity"
        used = usage if usage is not None else float(input("Amount used (oz): "))
        new_value = (liquid_quantity or 0) - used

    else:
        item_quantity_col = "count"
        used = int(usage) if usage is not None else int(input("Units used: "))
        new_value = (count or 0) - used

    execute_query(
        f"UPDATE inventorylevels SET {item_quantity_col} = ? WHERE item_id = ?",
        (new_value, item_id)
    )
    sorting.sort_item(item_id)
    print("Inventory updated!")


def remove_inventory(item_data):
    # Extract data from DB dictionary
    # Columns: id, barcode, name, brand, category
    item = item_data[0]
    item_id = item[0]
    name = item[2]
    
    confirmation = input(f"Confirm deletion of {name}. Input y/n")
    if confirmation.lower() == "y":
        q = "DELETE FROM inventorylevels WHERE item_id = ?"
        execute_query(q, (item_id,))
        print("Item deleted from pantry")
        
    else:
        print("Cancelled, item has not been removed from pantry")
    
    
def view_all_inventory():
    q = """
        SELECT mi.id, mi.barcode, mi.name, mi.brand, ic.category,
               il.gross_weight, il.liquid_quantity, il.count, il.location_bin_id
        FROM inventorylevels il
        JOIN masterinventory mi ON il.item_id = mi.id
        JOIN itemcategory ic    ON mi.category = ic.id
    """
    rows = get_data(q)
    result = [
        {
            "id":              row["id"],
            "barcode":         row["barcode"],
            "name":            row["name"],
            "brand":           row["brand"],
            "category":        row["category"],
            "gross_weight":    row["gross_weight"],
            "liquid_quantity": row["liquid_quantity"],
            "count":           row["count"],
            "bin":             row["location_bin_id"],
        }
        for row in rows
    ]
    return result

atexit.register(load_cell.cleanup)