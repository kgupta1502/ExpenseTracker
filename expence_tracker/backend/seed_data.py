import argparse
import random
from calendar import monthrange
from datetime import date

from werkzeug.security import generate_password_hash

from app import Expense, User, create_app, db

CATEGORIES = [
    "Food",
    "Transportation",
    "Shopping",
    "Bills",
    "Entertainment",
    "Health",
    "Education",
    "Travel",
    "Other",
]
SUBCATEGORIES = [
    "Breakfast",
    "Lunch",
    "Dinner",
    "Cab",
    "Metro",
    "Groceries",
    "Online",
    "Utilities",
    "Snacks",
    "Gym",
]
NOTES = [
    "Quick bite",
    "Weekly grocery run",
    "Ride to office",
    "Weekend outing",
    "Utility payment",
    "Subscription",
    "Gift",
    "Pharmacy visit",
]


def month_back(start: date, offset: int) -> date:
    year = start.year
    month = start.month - offset
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def ensure_users(target_count: int) -> list[User]:
    users = User.query.order_by(User.id).all()
    to_create = max(0, target_count - len(users))
    created = []
    for idx in range(to_create):
        username = f"demo{len(users) + idx + 1}"
        email = f"{username}@example.com"
        user = User(
            email=email,
            username=username,
            password_hash=generate_password_hash("demo123"),
        )
        db.session.add(user)
        created.append(user)
    if created:
        db.session.commit()
        users.extend(created)
    return users[:target_count]


def seed_expenses_for_user(user: User, months: int, per_month: int):
    today = date.today()
    for offset in range(months):
        month_start = month_back(today, offset)
        days = monthrange(month_start.year, month_start.month)[1]
        for _ in range(per_month):
            day = random.randint(1, days)
            exp_date = date(month_start.year, month_start.month, day)
            category = random.choice(CATEGORIES)
            description = random.choice(NOTES)
            amount = round(random.uniform(40, 2500), 2)
            expense = Expense(
                user_id=user.id,
                amount=amount,
                category=category,
                description=description,
                date=exp_date,
            )
            db.session.add(expense)
    db.session.commit()


def main():
    parser = argparse.ArgumentParser(description="Seed sample users and expenses")
    parser.add_argument("--months", type=int, default=6, help="Number of past months to populate")
    parser.add_argument("--per-month", type=int, default=25, help="Entries per user per month")
    parser.add_argument("--users", type=int, default=1, help="Number of demo users to ensure")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    app = create_app()
    with app.app_context():
        users = ensure_users(args.users)
        for user in users:
            seed_expenses_for_user(user, args.months, args.per_month)
        print(
            f"Seeded {len(users)} users with ~{args.months * args.per_month} expenses each."
        )


if __name__ == "__main__":
    main()
