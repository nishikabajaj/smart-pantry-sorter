# Inventory management system for the smart pantry sorter project.

import pyodbc

# print(pyodbc.drivers()) # Confirm that the Microsoft ODBC Driver for SQL Server is installed.

# connection string for Python -> DB
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost\\SQLEXPRESS;'
    'DATABASE=FoodPantryDB;'
    'Trusted_Connection=yes;'
)

cursor = conn.cursor()
cursor.execute('SELECT @@VERSION')
print(cursor.fetchone())
conn.close()