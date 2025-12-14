from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
# Fix CORS - allow all origins during development
CORS(app, resources={r"/*": {"origins": "*"}})

def get_db():
    conn = sqlite3.connect("expenses.db")
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database on startup
with app.app_context():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            category TEXT,
            date TEXT,
            description TEXT
        )
    """)
    conn.commit()

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    return jsonify([dict(row) for row in rows])

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    try:
        data = request.get_json()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (amount, category, date, description) VALUES (?, ?, ?, ?)",
            (data['amount'], data['category'], data['date'], data.get('description', ''))
        )
        conn.commit()
        return jsonify({"message": "Expense added successfully", "id": cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/expenses/<int:id>', methods=['DELETE'])
def delete_expense(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (id,))
    conn.commit()
    return jsonify({"message": "Expense deleted"})

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "service": "Expense Tracker API"})

if __name__ == '__main__':
    print("🚀 Starting Flask server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)