import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'pantry.db')

TABLES = [
    # Junction tables first (to avoid FK conflicts)
    'MasterInventoryDietFlags',
    'MasterInventoryIngredients',
    'UserDietFlags',
    'UserDislikedIngredients',
    # Dependent tables
    'InventoryLevels',
    'Transactions',
    # Core tables
    'MasterInventory',
    'Bin',
    'ItemCategory',
    'DietFlags',
    'Ingredients',
    'User',
]

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('PRAGMA foreign_keys = OFF')
for table in TABLES:
    c.execute(f'DELETE FROM {table}')
    c.execute(f'DELETE FROM sqlite_sequence WHERE name=?', (table,))
    print(f'Cleared {table}')
c.execute('PRAGMA foreign_keys = ON')

conn.commit()
conn.close()
print("\nAll tables cleared and auto-increment counters reset.")