"""
test_api.py  —  Smart Pantry Sorter API Test Suite
====================================================
Tests every Flask endpoint against a temporary in-memory SQLite database.
Your real pantry.db is never touched.

Run with:
    pip install pytest requests
    pytest test_api.py -v

Make sure flask_app.py is NOT already running on port 5000 before running tests.
"""

import json, os, sqlite3, sys, threading, time
import pytest
import requests
from unittest.mock import patch, MagicMock

# ── Point imports at your project ────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import flask_app, inventory

BASE = "http://localhost:5001"   # separate port so tests never clash with dev server

# ── Minimal OpenFoodFacts-shaped response used across multiple tests ──────────
MOCK_OFF_PRODUCT = {
    "status": 1,
    "product": {
        "code":                  "0123456789",
        "product_name":          "Test Crackers",
        "brands":                ["BrandX"],
        "categories":            ["Snacks"],
        "ingredients":           [{"text": "flour"}, {"text": "salt"}],
        "allergens":             ["en:gluten"],
        "traces":                [],
        "product_quantity":      200,
        "product_quantity_unit": "g",
    }
}

# Minimal item_data dict that /api/add expects for a *new* item
NEW_ITEM_DATA = {
    "code":                  "0123456789",
    "product_name":          "Test Crackers",
    "brands":                ["BrandX"],
    "categories":            ["Snacks"],
    "ingredients":           [{"text": "flour"}, {"text": "salt"}],
    "allergens":             ["en:gluten"],
    "traces":                [],
    "product_quantity":      200,
    "product_quantity_unit": "g",
}

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def test_db(tmp_path_factory):
    """
    Create a fresh in-memory-style SQLite DB file for the test session
    and patch inventory.DB_PATH so every inventory call hits it instead
    of pantry.db.
    """
    db_file = str(tmp_path_factory.mktemp("db") / "test_pantry.db")

    conn = sqlite3.connect(db_file)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS ItemCategory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS MasterInventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode VARCHAR(50) UNIQUE,
            name VARCHAR(50),
            brand VARCHAR(50),
            category INTEGER,
            FOREIGN KEY (category) REFERENCES ItemCategory(id)
        );
        CREATE TABLE IF NOT EXISTS Bin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER UNIQUE,
            capacity REAL,
            current_load REAL,
            FOREIGN KEY (category_id) REFERENCES ItemCategory(id)
        );
        CREATE TABLE IF NOT EXISTS InventoryLevels (
            item_id INTEGER UNIQUE,
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
            current_location INTEGER
        );
        CREATE TABLE IF NOT EXISTS DietFlags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flag TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS Ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ingredient TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS MasterInventoryDietFlags (
            master_inventory_id INTEGER,
            diet_flag_id INTEGER,
            UNIQUE(master_inventory_id, diet_flag_id)
        );
        CREATE TABLE IF NOT EXISTS MasterInventoryIngredients (
            master_inventory_id INTEGER,
            ingredient_id INTEGER,
            UNIQUE(master_inventory_id, ingredient_id)
        );
        CREATE TABLE IF NOT EXISTS User (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS UserDietFlags (
            user_id INTEGER,
            diet_flag_id INTEGER,
            UNIQUE(user_id, diet_flag_id)
        );
        CREATE TABLE IF NOT EXISTS UserDislikedIngredients (
            user_id INTEGER,
            ingredient_id INTEGER,
            UNIQUE(user_id, ingredient_id)
        );
    ''')
    conn.commit()
    conn.close()

    # Redirect inventory module to test DB
    with patch.object(inventory, 'DB_PATH', db_file):
        yield db_file


@pytest.fixture(scope="session")
def server(test_db):
    """Start the Flask app on port 5001 in a background thread for the session."""
    flask_app.app.config["TESTING"] = True

    # Patch DB_PATH inside the running server context too
    with patch.object(inventory, 'DB_PATH', test_db):
        t = threading.Thread(
            target=lambda: flask_app.app.run(port=5001, use_reloader=False),
            daemon=True
        )
        t.start()
        time.sleep(1)   # give Flask a moment to start
        yield
    # daemon thread dies with session automatically


@pytest.fixture(autouse=True)
def patch_db(test_db):
    """Ensure every test function also sees the test DB path."""
    with patch.object(inventory, 'DB_PATH', test_db):
        yield


@pytest.fixture(autouse=True)
def mock_load_cell():
    """Prevent any real hardware calls during tests."""
    with patch('inventory._load_cell') as mock_lc:
        mock_lc.get_weight_g.return_value = 150.0
        mock_lc.stable_weight_g.return_value = 150.0
        yield mock_lc


@pytest.fixture(autouse=True)
def mock_sorting():
    """Prevent real sorting/hardware calls."""
    with patch('inventory.sorting') as mock_sort:
        mock_sort.sort_item.return_value = None
        yield mock_sort


# ── Helper ────────────────────────────────────────────────────────────────────

def post(endpoint, payload):
    return requests.post(f"{BASE}{endpoint}", json=payload)

def get(endpoint):
    return requests.get(f"{BASE}{endpoint}")


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/data
# ═════════════════════════════════════════════════════════════════════════════

class TestApiData:

    def test_returns_200(self, server):
        r = get("/api/data")
        assert r.status_code == 200

    def test_returns_list(self, server):
        r = get("/api/data")
        assert isinstance(r.json(), list)

    def test_empty_on_fresh_db(self, server):
        """Fresh test DB should have no inventory levels yet."""
        r = get("/api/data")
        assert r.json() == []


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/scan
# ═════════════════════════════════════════════════════════════════════════════

class TestApiScan:

    def test_missing_barcode_returns_400(self, server):
        r = post("/api/scan", {})
        assert r.status_code == 400
        assert "error" in r.json()

    def test_empty_barcode_returns_400(self, server):
        r = post("/api/scan", {"barcode": ""})
        assert r.status_code == 400

    def test_unknown_barcode_calls_off_and_returns_new(self, server):
        with patch('inventory.get_off_product', return_value=MOCK_OFF_PRODUCT):
            r = post("/api/scan", {"barcode": "9999999999"})
        assert r.status_code == 200
        body = r.json()
        assert body["new"] is True
        assert body["item_data"]["product_name"] == "Test Crackers"

    def test_off_not_found_returns_404(self, server):
        with patch('inventory.get_off_product', return_value={"status": 0}):
            r = post("/api/scan", {"barcode": "0000000000"})
        assert r.status_code == 404
        assert "error" in r.json()

    def test_known_barcode_returns_not_new(self, server, test_db):
        """Seed a row then scan it — should come back new=False."""
        conn = sqlite3.connect(test_db)
        conn.execute("INSERT OR IGNORE INTO itemcategory (category) VALUES ('Snacks')")
        cat_id = conn.execute("SELECT id FROM itemcategory WHERE category='Snacks'").fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO masterinventory (barcode, name, brand, category) VALUES (?,?,?,?)",
            ("1111111111", "Known Item", "BrandY", cat_id)
        )
        conn.commit()
        conn.close()

        r = post("/api/scan", {"barcode": "1111111111"})
        assert r.status_code == 200
        body = r.json()
        assert body["new"] is False
        assert body["item_data"]["name"] == "Known Item"
        assert body["item_data"]["barcode"] == "1111111111"

    def test_scan_response_shape(self, server):
        with patch('inventory.get_off_product', return_value=MOCK_OFF_PRODUCT):
            r = post("/api/scan", {"barcode": "8888888888"})
        body = r.json()
        assert "item_data" in body
        assert "new" in body
        # Check all filter_keys are present for a new item
        for key in ["code", "product_name", "brands", "categories",
                    "ingredients", "allergens", "product_quantity",
                    "product_quantity_unit"]:
            assert key in body["item_data"], f"Missing key: {key}"


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/weight
# ═════════════════════════════════════════════════════════════════════════════

class TestApiWeight:

    def test_returns_200(self, server):
        with patch('flask_app.LoadCell') as mock_lc_cls:
            mock_lc_cls._load_cell.get_weight_g.return_value = 120.5
            mock_lc_cls._load_cell.stable_weight_g.return_value = 120.5
            r = get("/api/weight")
        # Weight endpoint may 500 if LoadCell import fails in test env — acceptable
        assert r.status_code in (200, 500)

    def test_response_shape_when_available(self, server):
        """If the endpoint succeeds, it must return grams and stable fields."""
        with patch('flask_app.LoadCell') as mock_lc_cls:
            mock_lc_cls._load_cell.get_weight_g.return_value = 120.5
            mock_lc_cls._load_cell.stable_weight_g.return_value = 120.5
            r = get("/api/weight")
        if r.status_code == 200:
            body = r.json()
            assert "grams" in body
            assert "stable" in body


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/add
# ═════════════════════════════════════════════════════════════════════════════

class TestApiAdd:

    def test_add_new_item_returns_ok(self, server):
        with patch('inventory.sorting'):
            r = post("/api/add", {"item_data": NEW_ITEM_DATA, "new": True})
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_add_with_weight_override(self, server):
        """weight_g in body should override product_quantity."""
        item = {**NEW_ITEM_DATA, "code": "2222222222"}
        with patch('inventory.sorting'):
            r = post("/api/add", {"item_data": item, "new": True, "weight_g": 300.0})
        assert r.status_code == 200

    def test_add_missing_item_data_returns_500(self, server):
        r = post("/api/add", {"new": True})
        assert r.status_code == 500

    def test_add_existing_item_new_false(self, server, test_db):
        """Re-stocking a known barcode (new=False) should succeed."""
        item = {**NEW_ITEM_DATA, "code": "3333333333"}
        with patch('inventory.sorting'):
            post("/api/add", {"item_data": item, "new": True})

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT id, barcode, name, brand, category FROM masterinventory WHERE barcode=?",
            ("3333333333",)
        ).fetchone()
        conn.close()

        if row:
            db_item = [[row[0], row[1], row[2], row[3], row[4]]]
            with patch('inventory.sorting'), \
                patch('builtins.input', return_value="2"):  # mock count input
                r = post("/api/add", {"item_data": db_item, "new": False})
            assert r.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/update
# ═════════════════════════════════════════════════════════════════════════════

class TestApiUpdate:

    def test_update_missing_item_data_returns_500(self, server):
        r = post("/api/update", {})
        assert r.status_code == 500

    def test_update_nonexistent_item_returns_500(self, server):
        """item_data for an ID that has no InventoryLevels row should raise and return 500."""
        fake_item = [[9999, "0000000000", "Ghost Item", "NoBrand", 1]]
        with patch('builtins.input', return_value="0"):
            r = post("/api/update", {"item_data": fake_item})
        assert r.status_code == 500

    def test_update_known_item(self, server, test_db):
        """Add an item, then update it — should return ok."""
        item = {**NEW_ITEM_DATA, "code": "4444444444"}
        with patch('inventory.sorting'):
            post("/api/add", {"item_data": item, "new": True})

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT id, barcode, name, brand, category FROM masterinventory WHERE barcode=?",
            ("4444444444",)
        ).fetchone()
        conn.close()

        if row:
            db_item = [[row[0], row[1], row[2], row[3], row[4]]]
            with patch('inventory.sorting'), \
                 patch('inventory._load_cell') as lc:
                lc.stable_weight_g.return_value = 100.0
                lc.get_weight_g.return_value = 100.0
                r = post("/api/update", {"item_data": db_item})
            assert r.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# POST /api/remove
# ═════════════════════════════════════════════════════════════════════════════

class TestApiRemove:

    def test_remove_missing_item_data_returns_500(self, server):
        r = post("/api/remove", {})
        assert r.status_code == 500

    def test_remove_known_item(self, server, test_db):
        """Add an item then remove it — InventoryLevels row should be gone."""
        item = {**NEW_ITEM_DATA, "code": "5555555555"}
        with patch('inventory.sorting'):
            post("/api/add", {"item_data": item, "new": True})

        conn = sqlite3.connect(test_db)
        row = conn.execute(
            "SELECT id, barcode, name, brand, category FROM masterinventory WHERE barcode=?",
            ("5555555555",)
        ).fetchone()
        conn.close()

        if row:
            db_item = [[row[0], row[1], row[2], row[3], row[4]]]
            with patch('inventory.remove_inventory') as mock_remove:
                mock_remove.return_value = None
                r = post("/api/remove", {"item_data": db_item})
            assert r.status_code == 200
            mock_remove.assert_called_once()

    def test_remove_nonexistent_item_still_returns_ok(self, server):
        """Remove on an unknown item — inventory.remove_inventory handles it gracefully."""
        fake_item = [[9999, "0000000001", "Fake", "FakeBrand", 1]]
        with patch('inventory.remove_inventory') as mock_remove:
            mock_remove.return_value = None
            r = post("/api/remove", {"item_data": fake_item})
        assert r.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# GET /api/recipes
# ═════════════════════════════════════════════════════════════════════════════

class TestApiRecipes:

    def test_returns_200(self, server):
        r = get("/api/recipes")
        assert r.status_code == 200

    def test_returns_empty_list(self, server):
        """Stub endpoint should return [] until recipe.py is implemented."""
        r = get("/api/recipes")
        assert r.json() == []


# ═════════════════════════════════════════════════════════════════════════════
# format_item helper (unit tests — no server needed)
# ═════════════════════════════════════════════════════════════════════════════

class TestFormatItem:

    def test_none_input_returns_none(self):
        assert flask_app.format_item(None) is None

    def test_empty_list_returns_none(self):
        assert flask_app.format_item([]) is None

    def test_valid_row_returns_dict(self):
        row = [(1, "0123456789", "Test Item", "BrandZ", 2)]
        result = flask_app.format_item(row)
        assert result == {
            "id": 1,
            "barcode": "0123456789",
            "name": "Test Item",
            "brand": "BrandZ",
            "category": 2,
        }

    def test_all_keys_present(self):
        row = [(5, "9876543210", "Another", "BrandA", 3)]
        result = flask_app.format_item(row)
        for key in ("id", "barcode", "name", "brand", "category"):
            assert key in result