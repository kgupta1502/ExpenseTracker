from flask import Flask, request, jsonify
from flask_cors import CORS
from models import get_db_connection, create_table

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

    return jsonify({"message": "Expense added successfully"})

@app.route("/expenses", methods=["GET"])
def get_expenses():
    conn = get_db_connection()
    expenses = conn.execute(
        "SELECT * FROM expenses ORDER BY date DESC LIMIT 10"
    ).fetchall()
    conn.close()

    return jsonify([dict(row) for row in expenses])

@app.route("/expenses/<int:id>", methods=["DELETE"])
def delete_expense(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM expenses WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Expense deleted"})

if __name__ == "__main__":
    app.run(debug=True)
