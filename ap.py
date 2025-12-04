from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --------------------- DB INITIAL SETUP ---------------------
def init_db():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL,
            category TEXT,
            date TEXT,
            description TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --------------------- ADD EXPENSE ---------------------
@app.route("/expenses", methods=["POST"])
def add_expense():
    data = request.json

    amount = data.get("amount")
    category = data.get("category")
    date = data.get("date")
    description = data.get("description")

    if not amount or not category or not date:
        return jsonify({"error": "Missing required fields"}), 400

    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (amount, category, date, description)
        VALUES (?, ?, ?, ?)
    """, (amount, category, date, description))
    conn.commit()
    conn.close()

    return jsonify({"message": "Expense added successfully!"}), 201

# --------------------- GET RECENT EXPENSES ---------------------
@app.route("/expenses", methods=["GET"])
def get_expenses():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM expenses ORDER BY id DESC LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()

    expenses = []
    for r in rows:
        expenses.append({
            "id": r[0],
            "amount": r[1],
            "category": r[2],
            "date": r[3],
            "description": r[4]
        })

    return jsonify(expenses)

# --------------------- DELETE EXPENSE ---------------------
@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Expense deleted"})

# --------------------- EDIT EXPENSE ---------------------
@app.route("/expenses/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id):
    data = request.json

    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE expenses 
        SET amount=?, category=?, date=?, description=?
        WHERE id=?
    """, (data["amount"], data["category"], data["date"], data["description"], expense_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Expense updated successfully"})

if __name__ == "__main__":
    app.run(debug=True)
