import sqlite3
from datetime import date, timedelta
import random

DATABASE = "bank_cash.db"


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS branches (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            branch_code TEXT UNIQUE NOT NULL,

            branch_name TEXT NOT NULL,

            location TEXT,

            vault_balance REAL NOT NULL DEFAULT 0,

            safety_buffer REAL NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            branch_code TEXT NOT NULL,

            transaction_date TEXT NOT NULL,

            transaction_type TEXT NOT NULL,

            amount REAL NOT NULL,

            channel TEXT NOT NULL,

            description TEXT,

            is_salary_day INTEGER DEFAULT 0,

            is_festival_day INTEGER DEFAULT 0,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            branch_code TEXT NOT NULL,

            forecast_date TEXT NOT NULL,

            teller_forecast REAL DEFAULT 0,

            atm_forecast REAL DEFAULT 0,

            deposit_forecast REAL DEFAULT 0,

            total_forecast REAL DEFAULT 0,

            safety_stock REAL DEFAULT 0,

            vault_balance REAL DEFAULT 0,

            recommended_indent REAL DEFAULT 0,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cash_monitor (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            branch_code TEXT NOT NULL,

            slot_start TEXT NOT NULL,

            slot_end TEXT NOT NULL,

            opening_balance REAL DEFAULT 0,

            projected_withdrawal REAL DEFAULT 0,

            projected_deposit REAL DEFAULT 0,

            balance_before_transfer REAL DEFAULT 0,

            planned_transfer REAL DEFAULT 0,

            remaining_balance REAL DEFAULT 0,

            safety_buffer REAL DEFAULT 0,

            reminder_level TEXT DEFAULT 'OK',

            reminder_message TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(branch_code, slot_start)
        )
    """)

    cur.execute("""
        SELECT 1
        FROM branches
        WHERE branch_code = ?
    """, ("BR001",))

    if cur.fetchone() is None:

        cur.execute("""
            INSERT INTO branches
            (
                branch_code,
                branch_name,
                location,
                vault_balance,
                safety_buffer
            )

            VALUES (?, ?, ?, ?, ?)
        """, (
            "BR001",
            "Main Branch",
            "Andhra Pradesh",
            500000,
            100000
        ))

    conn.commit()
    conn.close()


def seed_sample_data():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) AS n
        FROM transactions
        WHERE branch_code = ?
    """, ("BR001",))

    if cur.fetchone()["n"] > 0:
        conn.close()
        return

    random.seed(42)

    today = date.today()

    festivals = {
        today - timedelta(days=14),
        today - timedelta(days=35)
    }

    rows = []

    for i in range(45, 0, -1):

        d = today - timedelta(days=i)

        salary = d.day in (
            1, 2, 5, 28, 29, 30, 31
        )

        festival = d in festivals

        factor = 1.45 if salary else 1.0

        if festival:
            factor *= 1.35

        teller_withdrawal = max(
            10000,
            random.gauss(
                115000 * factor,
                15000
            )
        )

        atm_withdrawal = max(
            15000,
            random.gauss(
                75000 * factor,
                10000
            )
        )

        deposits = max(
            10000,
            random.gauss(
                95000,
                12000
            )
        )

        rows.extend([

            (
                "BR001",
                d.isoformat(),
                "WITHDRAWAL",
                round(teller_withdrawal, 2),
                "TELLER",
                "Sample teller withdrawal",
                int(salary),
                int(festival)
            ),

            (
                "BR001",
                d.isoformat(),
                "WITHDRAWAL",
                round(atm_withdrawal, 2),
                "ATM",
                "Sample ATM cash replenishment",
                int(salary),
                int(festival)
            ),

            (
                "BR001",
                d.isoformat(),
                "DEPOSIT",
                round(deposits, 2),
                "TELLER",
                "Sample customer deposit",
                int(salary),
                int(festival)
            )
        ])

    cur.executemany("""
        INSERT INTO transactions
        (
            branch_code,
            transaction_date,
            transaction_type,
            amount,
            channel,
            description,
            is_salary_day,
            is_festival_day
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()


def get_branch(branch_code="BR001"):

    conn = get_connection()

    row = conn.execute("""
        SELECT *
        FROM branches
        WHERE branch_code = ?
    """, (branch_code,)).fetchone()

    conn.close()

    return row


def update_vault_balance(
    branch_code,
    vault_balance
):

    conn = get_connection()

    conn.execute("""
        UPDATE branches

        SET vault_balance = ?

        WHERE branch_code = ?
    """, (
        vault_balance,
        branch_code
    ))

    conn.commit()
    conn.close()


def add_transaction(
    branch_code,
    transaction_date,
    transaction_type,
    amount,
    channel,
    description="",
    is_salary_day=0,
    is_festival_day=0
):

    conn = get_connection()

    conn.execute("""
        INSERT INTO transactions
        (
            branch_code,
            transaction_date,
            transaction_type,
            amount,
            channel,
            description,
            is_salary_day,
            is_festival_day
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        branch_code,
        transaction_date,
        transaction_type,
        amount,
        channel,
        description,
        is_salary_day,
        is_festival_day
    ))

    conn.commit()
    conn.close()


def get_transactions(
    branch_code="BR001",
    limit=200
):

    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM transactions

        WHERE branch_code = ?

        ORDER BY
            transaction_date DESC,
            id DESC

        LIMIT ?
    """, (
        branch_code,
        limit
    )).fetchall()

    conn.close()

    return rows


def get_forecasts(
    branch_code="BR001",
    limit=30
):

    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM forecasts

        WHERE branch_code = ?

        ORDER BY
            forecast_date DESC,
            id DESC

        LIMIT ?
    """, (
        branch_code,
        limit
    )).fetchall()

    conn.close()

    return rows


def save_forecast(data):

    conn = get_connection()

    conn.execute("""
        INSERT INTO forecasts
        (
            branch_code,
            forecast_date,
            teller_forecast,
            atm_forecast,
            deposit_forecast,
            total_forecast,
            safety_stock,
            vault_balance,
            recommended_indent
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["branch_code"],
        data["forecast_date"],
        data["teller_forecast"],
        data["atm_forecast"],
        data["deposit_forecast"],
        data["total_forecast"],
        data["safety_stock"],
        data["vault_balance"],
        data["recommended_indent"]
    ))

    conn.commit()
    conn.close()


def save_cash_monitor(data):

    conn = get_connection()

    conn.execute("""
        INSERT INTO cash_monitor
        (
            branch_code,
            slot_start,
            slot_end,
            opening_balance,
            projected_withdrawal,
            projected_deposit,
            balance_before_transfer,
            planned_transfer,
            remaining_balance,
            safety_buffer,
            reminder_level,
            reminder_message
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(
            branch_code,
            slot_start
        )

        DO UPDATE SET

            slot_end = excluded.slot_end,

            opening_balance =
                excluded.opening_balance,

            projected_withdrawal =
                excluded.projected_withdrawal,

            projected_deposit =
                excluded.projected_deposit,

            balance_before_transfer =
                excluded.balance_before_transfer,

            planned_transfer =
                excluded.planned_transfer,

            remaining_balance =
                excluded.remaining_balance,

            safety_buffer =
                excluded.safety_buffer,

            reminder_level =
                excluded.reminder_level,

            reminder_message =
                excluded.reminder_message,

            created_at =
                CURRENT_TIMESTAMP
    """, (
        data["branch_code"],
        data["slot_start"],
        data["slot_end"],
        data["opening_balance"],
        data["projected_withdrawal"],
        data["projected_deposit"],
        data["balance_before_transfer"],
        data["planned_transfer"],
        data["remaining_balance"],
        data["safety_buffer"],
        data["reminder_level"],
        data["reminder_message"]
    ))

    conn.commit()
    conn.close()


def get_cash_monitor_history(
    branch_code="BR001",
    limit=30
):

    conn = get_connection()

    rows = conn.execute("""
        SELECT *
        FROM cash_monitor

        WHERE branch_code = ?

        ORDER BY slot_start DESC

        LIMIT ?
    """, (
        branch_code,
        limit
    )).fetchall()

    conn.close()

    return rows