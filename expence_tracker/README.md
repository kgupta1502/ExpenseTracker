# ExpenseTracker — Modules 1-3

Implements all three modules of the IIT Madras DT2 ExpenseTracker project:

1. **Expense Logger** – CRUD form + recent list.
2. **Spending Analytics** – category breakdown, pie chart, monthly snapshot, date/category filters, CSV export.
3. **Spending Predictor** – lightweight regression-based forecast with saver tips.

## Project structure

```
expence_tracker/
├── backend/   # Flask API, SQLite/MySQL storage, analytics & predictor logic
├── frontend/  # Vanilla HTML/CSS/JS dashboard served by Flask
└── backend/tests/  # Basic API tests (run with unittest)
```

## Getting started (SQLite or MySQL)

1. **(Optional) create a virtual environment**
   ```bash
   cd expence_tracker/backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
2. **Install backend dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Flask server**
   ```bash
   python app.py
   ```
4. Visit `http://127.0.0.1:5000` to use the full dashboard. The login screen now talks to the backend—sign up or log in before the data loads.

SQLite persistence (`expenses.db`) is created automatically in `backend/` unless you configure MySQL (below).

## Run with Docker

Use Docker if you want an isolated runtime with MySQL pre-wired and the frontend served separately via Nginx:

1. Build + start both services:
   ```bash
   cd expence_tracker
   docker compose up --build
   ```
   This launches:
   - the Nginx-powered frontend on <http://127.0.0.1:8080>
   - the Flask backend API on <http://127.0.0.1:5000>
   - MySQL on port `3306`

   The frontend proxies API calls to the backend, so you only need to open the `8080` URL in the browser.
2. (Optional) seed demo data once the containers are up:
   ```bash
   docker compose exec backend python backend/seed_data.py --users 1 --months 6 --per-month 30 --seed 42
   ```
3. To stop everything, press `Ctrl+C` or run `docker compose down`.

Feel free to swap database credentials/secret keys by editing the `backend` service environment block in `docker-compose.yml` or by using an `.env` file that Docker Compose reads automatically. You can also change the host port exposed by the frontend service if `8080` is taken locally.

### Default login after seeding

The seeding script provisions demo accounts so you can sign in immediately. Run:

```bash
python seed_data.py --users 1 --months 6 --per-month 30 --seed 42
```

Then log in with:

- **Email:** `demo1@example.com`
- **Password:** `demo123`

Use the “Sign up” toggle on the login overlay to create additional accounts from the UI; each account sees only its own expenses/analytics/predictor output.

## Using MySQL instead of SQLite

1. Create a database (e.g. `expense_tracker`) in MySQL.
2. Provide connection details before starting Flask, either as a single URL or discrete variables:
   ```bash
   # Option A: single URL
   export DATABASE_URL="mysql+pymysql://user:password@localhost:3306/expense_tracker"

   # Option B: individual settings (a URL is generated automatically)
   export MYSQL_HOST=localhost
   export MYSQL_PORT=3306        # optional, defaults to 3306
   export MYSQL_USER=expense_app # optional, defaults to root
   export MYSQL_PASSWORD=secret  # optional
   export MYSQL_DB=expense_tracker
   ```
3. Run `python app.py` – `db.create_all()` will create the `expenses` table in MySQL. You can also bootstrap both the database and schema automatically via Docker Compose:
   ```bash
   cd expence_tracker
   docker compose up -d mysql
   ```
   This spins up MySQL 8.0 with credentials matching `.env.example` and seeds the schema from `backend/mysql_schema.sql`.

You can also set `MYSQL_URL`. Any SQLAlchemy-compatible `DATABASE_URL` works (Cloud SQL, Planetscale, etc.). For a step-by-step walkthrough (including Docker), see `backend/README.mysql.md`.

## API endpoints

| Method | Route                | Description                                           |
| ------ | -------------------- | ----------------------------------------------------- |
| POST   | `/auth/signup`       | Register a new user (returns token + profile)         |
| POST   | `/auth/login`        | Log in with email/password (returns token + profile)  |
| GET    | `/me`                | Retrieve the authenticated user                       |
| GET    | `/expenses`          | List expenses (supports optional date/category filters)|
| POST   | `/expenses`          | Add a new expense                                     |
| PUT    | `/expenses/<id>`     | Update an existing expense                            |
| DELETE | `/expenses/<id>`     | Remove an expense                                     |
| GET    | `/expenses/stats`    | Category totals + monthly trend (supports filters)    |
| GET    | `/expenses/monthly`  | Month summary + recent entries (`?month=YYYY-MM`)     |
| GET    | `/expenses/export`   | CSV export respecting the same filters                |
| GET    | `/predict`           | Forecast next month + spender profile + tip           |

### Filters & CSV export

- Use `start_date`, `end_date` (YYYY-MM-DD) and/or `category` query params on `/expenses`, `/expenses/stats`, and `/expenses/export` for focused reporting.
- The frontend exposes date pickers + category dropdown plus a one-click CSV export that honors the chosen filters.
- The monthly card has a dedicated `<input type="month">` selector that loads the desired period via `?month=YYYY-MM`.

## Sample data seeding

A helper script can populate the database with demo users and realistic expense histories:

```bash
cd expence_tracker/backend
python seed_data.py --users 2 --months 6 --per-month 30 --seed 42
```

Arguments (all optional):
- `--users` – number of demo accounts to ensure (default 1)
- `--months` – how many past months to populate (default 4)
- `--per-month` – number of entries per month (default 20)
- `--seed` – random seed for reproducibility (default: none)

> The script simply inserts additional rows; it will warn if data already exists so you can Ctrl+C if you prefer a clean slate.

## Tests

Basic API tests live under `backend/tests/`. Run them with the built-in unittest runner (uses an in-memory SQLite DB):

```bash
cd expence_tracker/backend
python -m unittest tests.test_api
```

## Manual QA checklist

- Add, edit, and delete expenses via the form; ensure the recent table updates and edit/cancel UX works.
- Exercise the analytics filters and confirm the pie chart/table totals respond; download a CSV and open it in a spreadsheet tool.
- Switch the month picker to earlier months to verify the monthly snapshot updates.
- Add at least three months of data (use the seeding script) and observe the predictor card + hero forecast updating accordingly.

Module 3 uses a simple ordinary least squares regression on rolling 3-month windows. Feel free to upgrade it to ARIMA/Prophet or hook the API to a more advanced ML service if desired.
