
import inventory, json, sorting, recipe, flask_app, load_cell

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
def main():
    print("Welcome to the Smart Pantry Sorter!\n "
          "Pick a user action from the menu below:\n" 
          "--------------------------------------\n"
          "1. Add an item to inventory\n 2. Use an item\n 3. Remove an item\n 4. Recipe recommendations\nEnter 'Q' to quit.")
    
    menu_choice = ""
    # 3 actions: (1) Add item, (2) Use item, (3) Remove item, (4) Recommend recipe
    while (menu_choice.lower() != "q"):
        menu_choice = input("Select your menu choice: ")
        # For 1 and 2
        # User scans barcode of item
        # User places item on platform
        item_data, new = identify_item()
        match menu_choice:
            case "1":
                inventory.add_inventory(item_data, new)
            case "2":
                inventory.update_inventory(item_data)
            case "3":
                inventory.remove_inventory(item_data)
            case "4":
                break
            case "q":
                break

    # For 3
    # Navigate to recipe.py