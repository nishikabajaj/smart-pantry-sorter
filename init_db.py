import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'pantry.db')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.executescript('''
    CREATE TABLE IF NOT EXISTS ItemCategory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS MasterInventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode VARCHAR(50),
        name VARCHAR(50),
        brand VARCHAR(50),
        category INTEGER,
        FOREIGN KEY (category) REFERENCES ItemCategory(id)
    );
    CREATE TABLE IF NOT EXISTS Bin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER,
        capacity REAL,
        current_load REAL,
        FOREIGN KEY (category_id) REFERENCES ItemCategory(id)
    );
    CREATE TABLE IF NOT EXISTS InventoryLevels (
        item_id INTEGER,
        gross_weight REAL,
        liquid_quantity REAL,
        count INTEGER,
        location_bin_id INTEGER,
        expiration_date TEXT,
        FOREIGN KEY (item_id) REFERENCES MasterInventory(id),
        FOREIGN KEY (location_bin_id) REFERENCES Bin(id)
    );
    CREATE TABLE IF NOT EXISTS Transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        action TEXT,
        date TEXT,
        liquid_quantity REAL,
        gross_weight REAL,
        count INTEGER,
        expiration_date TEXT,
        current_location INTEGER,
        FOREIGN KEY (item_id) REFERENCES MasterInventory(id),
        FOREIGN KEY (current_location) REFERENCES Bin(id)
    );
    CREATE TABLE IF NOT EXISTS DietFlags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flag TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS Ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingredient TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS User (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS MasterInventoryDietFlags (
        master_inventory_id INTEGER,
        diet_flag_id INTEGER,
        UNIQUE(master_inventory_id, diet_flag_id),
        FOREIGN KEY (master_inventory_id) REFERENCES MasterInventory(id),
        FOREIGN KEY (diet_flag_id) REFERENCES DietFlags(id)
    );
    CREATE TABLE IF NOT EXISTS MasterInventoryIngredients (
        master_inventory_id INTEGER,
        ingredient_id INTEGER,
        UNIQUE(master_inventory_id, ingredient_id),
        FOREIGN KEY (master_inventory_id) REFERENCES MasterInventory(id),
        FOREIGN KEY (ingredient_id) REFERENCES Ingredients(id)
    );
    CREATE TABLE IF NOT EXISTS UserDietFlags (
        user_id INTEGER,
        diet_flag_id INTEGER,
        UNIQUE(user_id, diet_flag_id),
        FOREIGN KEY (user_id) REFERENCES User(id),
        FOREIGN KEY (diet_flag_id) REFERENCES DietFlags(id)
    );
    CREATE TABLE IF NOT EXISTS UserDislikedIngredients (
        user_id INTEGER,
        ingredient_id INTEGER,
        UNIQUE(user_id, ingredient_id),
        FOREIGN KEY (user_id) REFERENCES User(id),
        FOREIGN KEY (ingredient_id) REFERENCES Ingredients(id)
    );
''')

conn.commit()
conn.close()
print("pantry.db created successfully.")