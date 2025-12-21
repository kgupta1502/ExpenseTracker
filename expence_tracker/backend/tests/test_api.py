import json
import unittest
from datetime import date

from werkzeug.security import generate_password_hash

from app import Expense, User, create_app, db


class ExpenseApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "SECRET_KEY": "test-secret",
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            self.user = User(
                email="demo@example.com",
                username="demo",
                password_hash=generate_password_hash("demo123"),
            )
            db.session.add(self.user)
            db.session.commit()
        self.token = self._login()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def auth_headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _login(self):
        response = self.client.post(
            "/auth/login",
            data=json.dumps({"email": "demo@example.com", "password": "demo123"}),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        return data["token"]

    def _create_expense(self, payload):
        return self.client.post(
            "/expenses",
            data=json.dumps(payload),
            headers=self.auth_headers(),
        )

    def test_create_and_list_expenses(self):
        payload = {
            "amount": 250,
            "category": "Groceries",
            "date": "2025-01-05",
            "description": "Weekly run",
        }
        response = self._create_expense(payload)
        self.assertEqual(response.status_code, 201)

        list_response = self.client.get("/expenses", headers=self.auth_headers())
        self.assertEqual(list_response.status_code, 200)
        data = list_response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["category"], "Groceries")

    def test_stats_endpoint_groups_by_category(self):
        entries = [
            {"amount": 100, "category": "Transport", "date": "2025-02-01", "description": "Bus"},
            {"amount": 200, "category": "Groceries", "date": "2025-02-02", "description": "Veg"},
            {"amount": 150, "category": "Groceries", "date": "2025-02-05", "description": "Snacks"},
        ]
        for item in entries:
            self._create_expense(item)

        response = self.client.get("/expenses/stats", headers=self.auth_headers())
        self.assertEqual(response.status_code, 200)
        stats = response.get_json()
        categories = {row["category"]: row["total"] for row in stats["categoryTotals"]}
        self.assertEqual(categories["Groceries"], 350)
        self.assertEqual(categories["Transport"], 100)

    def test_monthly_endpoint_filters_month(self):
        jan = {"amount": 90, "category": "Bills", "date": "2025-01-10"}
        feb = {"amount": 120, "category": "Bills", "date": "2025-02-10"}
        self._create_expense(jan)
        self._create_expense(feb)

        response = self.client.get("/expenses/monthly?month=2025-02", headers=self.auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["expenses"][0]["date"], "2025-02-10")

    def test_predict_endpoint_returns_payload(self):
        today = date.today()
        payloads = []
        for idx in range(1, 5):
            month = today.month - idx
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            payloads.append(
                {
                    "amount": 200 + idx * 10,
                    "category": "Groceries",
                    "date": f"{year}-{str(month).zfill(2)}-05",
                }
            )
        for payload in payloads:
            self._create_expense(payload)

        response = self.client.get("/predict", headers=self.auth_headers())
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("predictedAmount", data)
        self.assertIn("spenderType", data)
        self.assertIn("suggestion", data)


if __name__ == "__main__":
    unittest.main()
