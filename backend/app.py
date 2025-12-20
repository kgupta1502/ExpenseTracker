from flask import Flask, request, jsonify
from flask_cors import CORS
from models import get_db_connection, create_table
from datetime import datetime

app = Flask(__name__)
CORS(app)

create_table()

@app.route("/expenses", methods=["POST"])
def add_expense():
    data = request.json
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO expenses (amount, category, date, description) VALUES (?, ?, ?, ?)",
        (data["amount"], data["category"], data["date"], data["description"])
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Expense added"})

@app.route("/expenses", methods=["GET"])
def get_expenses():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM expenses ORDER BY date DESC LIMIT 10"
    ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/expenses/<int:id>", methods=["DELETE"])
def delete_expense(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM expenses WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Expense deleted"})

# 🔹 Module 2 endpoints

@app.route("/expenses/stats", methods=["GET"])
def expense_stats():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        GROUP BY category
    """).fetchall()
    conn.close()
    return jsonify([
        {"category": row["category"], "total": row["total"]}
        for row in rows
    ])

@app.route("/expenses/monthly", methods=["GET"])
def monthly_expense():
    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    conn = get_db_connection()
    row = conn.execute("""
        SELECT SUM(amount) as total
        FROM expenses
        WHERE substr(date, 1, 7) = ?
    """, (current_month,)).fetchone()
    conn.close()

    return jsonify({
        "month": now.strftime("%B"),
        "total": row["total"] if row["total"] else 0
    })

if __name__ == "__main__":
    app.run(debug=True)
