import csv
import io
import os
from collections import defaultdict
from datetime import date, datetime
from functools import wraps
from statistics import mean
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus

from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import extract, inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "../frontend"))
DATABASE_PATH = os.path.join(BASE_DIR, "expenses.db")
DEFAULT_SECRET = os.getenv("SECRET_KEY", "dev-secret-key")
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(255))
    date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship(User, backref=db.backref("expenses", lazy=True))

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": self.amount,
            "category": self.category,
            "description": self.description or "",
            "date": self.date.isoformat(),
        }


def build_database_uri() -> str:
    direct_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
    if direct_url:
        return direct_url

    mysql_host = os.getenv("MYSQL_HOST")
    if mysql_host:
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_user = os.getenv("MYSQL_USER", "root")
        mysql_password = os.getenv("MYSQL_PASSWORD", "")
        mysql_db = os.getenv("MYSQL_DB", "expense_tracker")
        password_part = f":{quote_plus(mysql_password)}" if mysql_password else ""
        return f"mysql+pymysql://{mysql_user}{password_part}@{mysql_host}:{mysql_port}/{mysql_db}"

    return f"sqlite:///{DATABASE_PATH}"


def parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_filters(args) -> Tuple[Optional[date], Optional[date], Optional[str]]:
    start = parse_iso_date(args.get("start_date"))
    end = parse_iso_date(args.get("end_date"))
    category = args.get("category")
    category = category.strip() if category else None
    return start, end, category or None


def apply_filters(query, user_id: int, start_date: Optional[date], end_date: Optional[date], category: Optional[str]):
    query = query.filter(Expense.user_id == user_id)
    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)
    if category:
        query = query.filter(Expense.category == category)
    return query


def aggregate_monthly_expenses(expenses: Sequence[Expense]) -> List[Tuple[str, float]]:
    monthly_totals: Dict[str, float] = defaultdict(float)
    for exp in expenses:
        key = exp.date.strftime("%Y-%m")
        monthly_totals[key] += exp.amount
    return sorted(monthly_totals.items())


def create_app(config: Optional[Dict] = None):
    app = Flask(
        __name__,
        static_folder=FRONTEND_DIR,
        static_url_path="",
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = build_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = DEFAULT_SECRET
    app.config.setdefault("TOKEN_TTL_SECONDS", TOKEN_TTL_SECONDS)
    if config:
        app.config.update(config)

    CORS(app)
    db.init_app(app)

    def bootstrap_schema():
        inspector = inspect(db.engine)
        expense_columns = {column["name"] for column in inspector.get_columns("expenses")}
        if "user_id" not in expense_columns:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE expenses ADD COLUMN user_id INTEGER"))
            default_user = User.query.filter_by(email="legacy@example.com").first()
            if not default_user:
                default_user = User(
                    email="legacy@example.com",
                    username="legacy_user",
                    password_hash=generate_password_hash("legacy123"),
                )
                db.session.add(default_user)
                db.session.commit()
            with db.engine.begin() as conn:
                conn.execute(
                    text("UPDATE expenses SET user_id = :uid WHERE user_id IS NULL OR user_id = 0"),
                    {"uid": default_user.id},
                )

    with app.app_context():
        db.create_all()
        bootstrap_schema()

    token_serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

    def generate_token(user_id: int) -> str:
        return token_serializer.dumps({"user_id": user_id})

    def decode_token(token: str) -> Optional[User]:
        try:
            payload = token_serializer.loads(token, max_age=app.config["TOKEN_TTL_SECONDS"])
            user_id = payload.get("user_id")
            if not user_id:
                return None
            return User.query.get(user_id)
        except (BadSignature, SignatureExpired):
            return None

    def extract_token() -> Optional[str]:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()
        return request.cookies.get("auth_token")

    def auth_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = extract_token()
            if not token:
                return jsonify({"error": "Authentication required"}), 401
            user = decode_token(token)
            if not user:
                return jsonify({"error": "Invalid or expired token"}), 401
            g.current_user = user
            g.auth_token = token
            return fn(*args, **kwargs)

        return wrapper

    def serialize_user(user: User) -> Dict:
        return user.to_dict()

    def auth_response(user: User):
        token = generate_token(user.id)
        return {
            "token": token,
            "user": serialize_user(user),
        }

    def parse_expense_payload(payload: Dict) -> Tuple[float, str, date, str]:
        try:
            amount = float(payload.get("amount", 0))
        except (TypeError, ValueError):
            amount = 0.0
        category = (payload.get("category") or "").strip()
        description = (payload.get("description") or "").strip()
        date_str = payload.get("date")
        try:
            expense_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            expense_date = None
        return amount, category, expense_date, description

    def validate_expense(amount: float, category: str, expense_date: date) -> Tuple[bool, str]:
        if amount <= 0:
            return False, "Amount must be greater than zero."
        if not category:
            return False, "Category is required."
        if expense_date is None:
            return False, "A valid date (YYYY-MM-DD) is required."
        return True, ""

    def build_expense_query(user_id: int):
        return Expense.query.filter(Expense.user_id == user_id)

    @app.route("/")
    def serve_index():
        return app.send_static_file("index.html")

    @app.post("/auth/signup")
    def signup():
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not email or not username or not password:
            return jsonify({"error": "Email, username, and password are required."}), 400
        if User.query.filter((User.email == email) | (User.username == username)).first():
            return jsonify({"error": "Email or username already registered."}), 400
        user = User(
            email=email,
            username=username,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()
        return jsonify(auth_response(user)), 201

    @app.post("/auth/login")
    def login():
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({"error": "Invalid credentials."}), 401
        return jsonify(auth_response(user))

    @app.get("/me")
    @auth_required
    def me():
        return jsonify({"user": serialize_user(g.current_user)})

    @app.get("/expenses")
    @auth_required
    def list_expenses():
        start_date, end_date, category = parse_filters(request.args)
        query = apply_filters(build_expense_query(g.current_user.id), g.current_user.id, start_date, end_date, category)
        expenses = query.order_by(Expense.date.desc(), Expense.id.desc()).all()
        return jsonify([exp.to_dict() for exp in expenses])

    @app.post("/expenses")
    @auth_required
    def create_expense():
        payload = request.get_json() or {}
        amount, category, expense_date, description = parse_expense_payload(payload)
        is_valid, message = validate_expense(amount, category, expense_date)
        if not is_valid:
            return jsonify({"error": message}), 400
        expense = Expense(
            user_id=g.current_user.id,
            amount=round(amount, 2),
            category=category,
            description=description,
            date=expense_date,
        )
        db.session.add(expense)
        db.session.commit()
        return jsonify(expense.to_dict()), 201

    @app.put("/expenses/<int:expense_id>")
    @auth_required
    def update_expense(expense_id: int):
        payload = request.get_json() or {}
        amount, category, expense_date, description = parse_expense_payload(payload)
        is_valid, message = validate_expense(amount, category, expense_date)
        if not is_valid:
            return jsonify({"error": message}), 400
        expense = build_expense_query(g.current_user.id).filter_by(id=expense_id).first_or_404()
        expense.amount = round(amount, 2)
        expense.category = category
        expense.description = description
        expense.date = expense_date
        db.session.commit()
        return jsonify(expense.to_dict())

    @app.delete("/expenses/<int:expense_id>")
    @auth_required
    def delete_expense(expense_id: int):
        expense = build_expense_query(g.current_user.id).filter_by(id=expense_id).first_or_404()
        db.session.delete(expense)
        db.session.commit()
        return jsonify({"status": "deleted"})

    @app.get("/expenses/stats")
    @auth_required
    def expense_stats():
        start_date, end_date, category = parse_filters(request.args)
        query = apply_filters(build_expense_query(g.current_user.id), g.current_user.id, start_date, end_date, category)
        expenses = query.all()
        totals_by_category: Dict[str, float] = defaultdict(float)
        for expense in expenses:
            totals_by_category[expense.category] += expense.amount
        monthly_trend = [
            {"month": key, "total": round(total, 2)}
            for key, total in aggregate_monthly_expenses(expenses)
        ]
        response = {
            "totalSpent": round(sum(totals_by_category.values()), 2),
            "categoryTotals": [
                {"category": cat, "total": round(total, 2)}
                for cat, total in sorted(
                    totals_by_category.items(), key=lambda item: item[1], reverse=True
                )
            ],
            "monthlyTrend": monthly_trend,
        }
        return jsonify(response)

    @app.get("/expenses/monthly")
    @auth_required
    def current_month_expenses():
        month_param = request.args.get("month")
        today = date.today()
        if month_param:
            try:
                parsed = datetime.strptime(month_param, "%Y-%m")
                year, month = parsed.year, parsed.month
            except ValueError:
                year, month = today.year, today.month
        else:
            year, month = today.year, today.month
        expenses = (
            build_expense_query(g.current_user.id)
            .filter(
                extract("year", Expense.date) == year,
                extract("month", Expense.date) == month,
            )
            .order_by(Expense.date.desc())
            .all()
        )
        total = round(sum(exp.amount for exp in expenses), 2)
        month_label = date(year, month, 1).strftime("%B %Y")
        return jsonify(
            {
                "month": month_label,
                "total": total,
                "count": len(expenses),
                "expenses": [exp.to_dict() for exp in expenses],
            }
        )

    @app.get("/expenses/export")
    @auth_required
    def export_expenses():
        start_date, end_date, category = parse_filters(request.args)
        query = apply_filters(build_expense_query(g.current_user.id), g.current_user.id, start_date, end_date, category)
        expenses = query.order_by(Expense.date.desc()).all()

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "date", "category", "description", "amount"])
        for expense in expenses:
            writer.writerow(
                [
                    expense.id,
                    expense.date.isoformat(),
                    expense.category,
                    expense.description or "",
                    f"{expense.amount:.2f}",
                ]
            )
        buffer.seek(0)
        filename = f"expenses_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        response = Response(buffer.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response

    def train_linear_regression(features: List[List[float]], targets: List[float]):
        if not features:
            return None
        cols = len(features[0])
        xtx = [[0.0 for _ in range(cols)] for _ in range(cols)]
        xty = [0.0 for _ in range(cols)]
        for row, target in zip(features, targets):
            for i in range(cols):
                value_i = row[i]
                xty[i] += value_i * target
                for j in range(cols):
                    xtx[i][j] += value_i * row[j]
        try:
            return solve_symmetric_system(xtx, xty)
        except ValueError:
            return None

    def solve_symmetric_system(matrix: List[List[float]], vector: List[float]) -> List[float]:
        n = len(vector)
        a = [row[:] for row in matrix]
        b = vector[:]
        for i in range(n):
            pivot_row = max(range(i, n), key=lambda r: abs(a[r][i]))
            if abs(a[pivot_row][i]) < 1e-9:
                raise ValueError("Matrix is singular")
            if pivot_row != i:
                a[i], a[pivot_row] = a[pivot_row], a[i]
                b[i], b[pivot_row] = b[pivot_row], b[i]
            pivot = a[i][i]
            for col in range(i, n):
                a[i][col] /= pivot
            b[i] /= pivot
            for row in range(n):
                if row == i:
                    continue
                factor = a[row][i]
                for col in range(i, n):
                    a[row][col] -= factor * a[i][col]
                b[row] -= factor * b[i]
        return b

    def predict_next_month(monthly: List[Tuple[str, float]]) -> float:
        totals = [total for _, total in monthly]
        if not totals:
            return 0.0
        if len(totals) < 4:
            return mean(totals[-3:])
        feature_rows: List[List[float]] = []
        targets: List[float] = []
        for idx in range(3, len(totals)):
            feature_rows.append([totals[idx - 3], totals[idx - 2], totals[idx - 1], 1.0])
            targets.append(totals[idx])
        coefficients = train_linear_regression(feature_rows, targets)
        if not coefficients:
            return mean(totals[-3:])
        next_features = [totals[-3], totals[-2], totals[-1], 1.0]
        prediction = sum(coef * feat for coef, feat in zip(coefficients, next_features))
        return max(prediction, 0.0)

    def categorize_spender(amount: float) -> Tuple[str, str]:
        if amount < 500:
            return (
                "Budget-Conscious",
                "Great discipline! Direct the surplus to savings or investments.",
            )
        if amount < 1500:
            return (
                "Average",
                "You're on track. Review discretionary categories to free 5-10% for savings.",
            )
        return (
            "High-Spender",
            "Spending is trending high. Set weekly limits and automate savings transfers.",
        )

    @app.get("/predict")
    @auth_required
    def predict_spending():
        expenses = build_expense_query(g.current_user.id).all()
        monthly = aggregate_monthly_expenses(expenses)
        prediction = round(predict_next_month(monthly), 2)
        label, suggestion = categorize_spender(prediction)
        trailing_average = round(mean([total for _, total in monthly[-3:]]) if monthly else 0.0, 2)
        return jsonify(
            {
                "predictedAmount": prediction,
                "spenderType": label,
                "suggestion": suggestion,
                "recentAverage": trailing_average,
                "dataPoints": monthly,
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
