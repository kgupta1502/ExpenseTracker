# Running ExpenseTracker with MySQL

This guide assumes you already have Docker available or a local MySQL service. The backend automatically connects to MySQL when the appropriate environment variables are set.

## 1. Start MySQL (Docker)

```bash
cd expence_tracker
docker compose up -d mysql
```

The compose file provisions:
- database: `expense_tracker`
- user/password: `expense_app` / `expense_password`
- exposed port `3306`

## 2. Configure environment variables

Copy the example file and adjust if needed:

```bash
cd backend
cp .env.example .env
# update values if you changed credentials
```

When using a virtual environment, export the variables so Flask picks them up:

```bash
export $(grep -v '^#' .env | xargs)
```

## 3. Seed demo data (optional but recommended)

Run the existing seeding script once the DB is reachable. It works for both SQLite and MySQL because it uses SQLAlchemy:

```bash
cd expence_tracker/backend
python seed_data.py --users 1 --months 6 --per-month 30 --seed 42
```

This provisions a `demo1@example.com` account (password `demo123`) and ~180 expenses covering the last six months so that every Module has data to display immediately.

## 4. Start the backend (serves API + frontend)

```bash
python app.py
```

Visit http://127.0.0.1:5000 to open the combined Module 1-3 dashboard. You can now:
- Log/edit/delete expenses (Module 1)
- View category pie chart + monthly summary (Module 2)
- See the predictor tile with the AI forecast (Module 3)

## 5. Useful commands

- Inspect database tables inside the container:
  ```bash
  docker exec -it expence_tracker-mysql-1 mysql -uexpense_app -pexpense_password expense_tracker
  ```
- Tear down the database when done:
  ```bash
  docker compose down
  ```
- Reset data by removing the persistent volume:
  ```bash
  docker compose down -v
  ```
