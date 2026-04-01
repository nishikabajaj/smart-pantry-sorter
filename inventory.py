# Inventory management system for the smart pantry sorter project.

from flask import Flask, jsonify
from flask_cors import CORS
import pyodbc

# print(pyodbc.drivers()) # Confirm that the Microsoft ODBC Driver for SQL Server is installed.

app = Flask(__name__)
CORS(app)

@app.route('/api/data', methods=['GET'])

def get_data(query):
    # connection string for Python -> DB
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=FoodPantryDB;'
        'Trusted_Connection=yes;'
    )
    cursor = conn.cursor()
    cursor.execute(query) # Use cursor.execute() to run queries
    rows = [cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(rows)

# fetchone() gets next single row as a tuple; row by row processing
# fetchmany(size) returns batch of rows up to specified size
# fetchall() grabs all rows as list of tuples

### ADD ITEM

# Barcode identifies item w/ OpenFoodFacts API
# Load cell determines weight for quantity OR user indicates count
# User confirms details (item, category, expiration)
# Sends category of item to sorting.py - sort_item()
# Adds item to inventory

### UPDATE ITEM
# Check for weight change with load cell
# User confirms details (item, usage)
# Sends category of item to sorting.py - sort_item()
# Update inventory

### REMOVE ITEM
# User scans barcode of item
# User confirms details (item and decision to remove)
# Remove item from inventory

### VIEW ITEMS
# Query and display all current items in inventory

if __name__ == '__main__':
    app.run(port=5000)
    
# Run with python inventory.py. Test at http://localhost:5000/api/data