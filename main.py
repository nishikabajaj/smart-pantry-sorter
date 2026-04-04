
import inventory, json

def identify_item():
    print("Ready for scan. Scan a barcode (Ctrl+C to quit).")

    # Barcode scanner grabs item barcode
    try:
        code = input("Scan now: ")   # scanner types digits + Enter
        code = code.strip()
        print(f"Got barcode: [{code}]")
        
    except KeyboardInterrupt:
        print("\nExiting.")
    
    item_data = inventory.get_master_db(code)
    if item_data:
        new = False
        return item_data, new

    new = True
    # Call OpenFoodFacts with code
    data = json.loads(inventory.get_off_product(code))
    if data.get("status") != 1:
        return None
    
    """
    Important fields to us are:

    status - 1 for found, !1 for not found in API
    code - for barcode
    product_name - item name
    brands - for brand
    categories - for category assigment
    ingredients - for ingredients
    allergens, traces - for diet/allergy flags
    product_quantity, product_quantity_unit - for inventory quantity
    nutriscoregrade (optional) - for nutrition scoring
    
    """
    
    # Parse JSON to extract all item information
    filter_keys = ["code", "product_name", "brands", "categories", "ingredients" "allergens", "traces", "product_quantity", "product_quantity_unit"]
    item_data = {k: data[k] for k in filter_keys if k in data}
    
    # Return dictionary of item information
    return item_data, new
    


# MAIN LOGIC
# 3 actions: (1) Add item, (2) Remove item, (3) Recommend recipe

# For 1 and 2
# User scans barcode of item
# User places item on platform

# For 1
# If item existed in inventory, send to inventory.py - update_item()
# else, send to inventory.py - add_item()

# For 2
# If item existed in inventory, send to inventory.py - remove_item()


# For 3
# Navigate to recipe.py