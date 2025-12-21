import csv
import random
from datetime import datetime, timedelta, timezone

import os

BASE_DIR = os.path.dirname(__file__)
USERS_CSV = os.path.join(BASE_DIR, "users_db.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "users_expense_data.csv")

CATEGORIES = {
    "Food": ["Breakfast", "Lunch", "Dinner", "Snacks"],
    "Transportation": ["Metro", "Cab", "Fuel", "Bus"],
    "Shopping": ["Groceries", "Online", "Clothing", "Essentials"],
    "Bills": ["Electricity", "Internet", "Phone", "Rent"],
    "Entertainment": ["Movies", "Streaming", "Concert"],
    "Health": ["Pharmacy", "Consultation", "Gym"],
    "Education": ["Courses", "Books", "Workshops"],
    "Travel": ["Flights", "Hotels", "Tour"],
    "Other": ["Gift", "Donation", "Misc"],
}

INCOME_NOTES = [
    "Salary credit",
    "Freelance payout",
    "Cashback",
    "Refund",
    "Gift received",
]
EXPENSE_NOTES = [
    "Quick bite",
    "Weekly stock-up",
    "Ride to office",
    "Utility payment",
    "Weekend plan",
    "Subscription",
    "Impulse buy",
]

ACCOUNT_TYPES = ["UPI", "Debit Card", "Credit Card", "Wallet", "Auto Debit"]

FREQUENCY_PROFILES = {
    "daily": (140, 210),
    "weekly": (40, 70),
    "monthly": (10, 20),
    "random": (15, 60),
}

FREQUENCY_WEIGHTS = {
    "daily": 0.2,
    "weekly": 0.35,
    "monthly": 0.2,
    "random": 0.25,
}

START_DAYS_AGO = 180
DATE_FORMAT = "%m/%d/%Y %H:%M"


def load_users(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def choose_frequency():
    choices, weights = zip(*FREQUENCY_WEIGHTS.items())
    return random.choices(choices, weights=weights, k=1)[0]


def random_datetime(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)


def build_record(user, dt: datetime):
    category = random.choice(list(CATEGORIES.keys()))
    subcategory = random.choice(CATEGORIES[category])
    is_income = random.random() < 0.18
    if is_income:
        amount = round(random.uniform(500, 8000), 2)
        entry_type = "Income"
        note = random.choice(INCOME_NOTES)
    else:
        amount = round(random.uniform(40, 2500), 2)
        entry_type = "Expense"
        note = random.choice(EXPENSE_NOTES)

    account_mode = random.choice(ACCOUNT_TYPES)
    logging_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "Date": dt.strftime(DATE_FORMAT),
        "User ID": user["user_id"],
        "Account": account_mode,
        "Category": category,
        "Subcategory": subcategory,
        "Note": note,
        "INR": amount,
        "Income/Expense": entry_type,
        "Note_dup": "",
        "Amount": f"{amount:.2f}",
        "Currency": "INR",
        "Account_dup": account_mode,
        "Logging Date": logging_date,
    }


def main():
    users = load_users(USERS_CSV)
    start = datetime.now() - timedelta(days=START_DAYS_AGO)
    end = datetime.now()
    records = []

    for user in users:
        freq = choose_frequency()
        min_entries, max_entries = FREQUENCY_PROFILES[freq]
        entries = random.randint(min_entries, max_entries)
        for _ in range(entries):
            dt = random_datetime(start, end)
            record = build_record(user, dt)
            records.append(record)

    records.sort(key=lambda r: datetime.strptime(r["Date"], DATE_FORMAT), reverse=True)

    fieldnames = [
        "Date",
        "User ID",
        "Account",
        "Category",
        "Subcategory",
        "Note",
        "INR",
        "Income/Expense",
        "Note_dup",
        "Amount",
        "Currency",
        "Account_dup",
        "Logging Date",
    ]

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Generated {len(records)} expense rows for {len(users)} users -> {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
