from datetime import datetime, timedelta

import pandas as pd

from database import (
    get_branch,
    get_connection,
    save_forecast,
    save_cash_monitor
)


def load_transactions(
    branch_code="BR001"
):

    conn = get_connection()

    rows = conn.execute("""
        SELECT
            transaction_date,
            transaction_type,
            amount,
            channel,
            is_salary_day,
            is_festival_day

        FROM transactions

        WHERE branch_code = ?

        ORDER BY transaction_date
    """, (branch_code,)).fetchall()

    conn.close()

    return pd.DataFrame(
        [dict(row) for row in rows]
    )


def adjustment_factor(day):

    salary = day.day in (
        1, 2, 5, 28, 29, 30, 31
    )

    festival = False

    factor = 1.0

    if salary:
        factor *= 1.35

    if festival:
        factor *= 1.25

    if day.weekday() >= 5:
        factor *= 0.90

    return (
        factor,
        salary,
        festival
    )


def _average_daily(
    df,
    transaction_type,
    channel=None,
    days=30
):

    if df.empty:
        return 0.0

    x = df[
        df["transaction_type"]
        == transaction_type
    ].copy()

    if channel:

        x = x[
            x["channel"] == channel
        ]

    if x.empty:
        return 0.0

    x["transaction_date"] = pd.to_datetime(
        x["transaction_date"]
    )

    cutoff = (
        pd.Timestamp.now().normalize()
        - pd.Timedelta(days=days)
    )

    x = x[
        x["transaction_date"] >= cutoff
    ]

    if x.empty:
        return 0.0

    daily = x.groupby(
        "transaction_date"
    )["amount"].sum()

    return float(daily.mean())


def generate_forecast(
    branch_code="BR001",
    target_date=None
):

    target_date = (
        target_date
        or datetime.now().date()
    )

    branch = get_branch(
        branch_code
    )

    df = load_transactions(
        branch_code
    )

    factor, _, _ = adjustment_factor(
        target_date
    )

    teller = (
        _average_daily(
            df,
            "WITHDRAWAL",
            "TELLER"
        )
        * factor
    )

    atm = (
        _average_daily(
            df,
            "WITHDRAWAL",
            "ATM"
        )
        * factor
    )

    deposits = (
        _average_daily(
            df,
            "DEPOSIT"
        )
        * (
            1.0
            + (factor - 1.0) * 0.50
        )
    )

    total = teller + atm

    safety = float(
        branch["safety_buffer"] or 0
    )

    vault = float(
        branch["vault_balance"] or 0
    )

    indent = max(
        0.0,
        total + safety - vault
    )

    data = {

        "branch_code":
            branch_code,

        "forecast_date":
            target_date.isoformat(),

        "teller_forecast":
            round(teller, 2),

        "atm_forecast":
            round(atm, 2),

        "deposit_forecast":
            round(deposits, 2),

        "total_forecast":
            round(total, 2),

        "safety_stock":
            round(safety, 2),

        "vault_balance":
            round(vault, 2),

        "recommended_indent":
            round(indent, 2)
    }

    save_forecast(data)

    return data


def generate_six_hour_monitor(
    branch_code="BR001",
    now=None
):

    now = now or datetime.now()

    branch = get_branch(
        branch_code
    )

    if branch is None:

        raise ValueError(
            "Branch not found"
        )

    df = load_transactions(
        branch_code
    )

    factor, _, _ = adjustment_factor(
        now.date()
    )

    daily_withdrawal = (

        _average_daily(
            df,
            "WITHDRAWAL",
            "TELLER"
        )

        +

        _average_daily(
            df,
            "WITHDRAWAL",
            "ATM"
        )

    ) * factor

    daily_deposit = (

        _average_daily(
            df,
            "DEPOSIT"
        )

        *

        (
            1.0
            + (factor - 1.0) * 0.50
        )
    )

    # Four 6-hour slots per day

    projected_withdrawal = round(
        daily_withdrawal / 4.0,
        2
    )

    projected_deposit = round(
        daily_deposit / 4.0,
        2
    )

    opening = round(
        float(
            branch["vault_balance"] or 0
        ),
        2
    )

    safety = round(
        float(
            branch["safety_buffer"] or 0
        ),
        2
    )

    # ---------------------------------------
    # CASH BEFORE TRANSFER
    # ---------------------------------------

    before_transfer = round(

        opening
        + projected_deposit
        - projected_withdrawal,

        2
    )

    # ---------------------------------------
    # REQUIRED CURRENCY CHEST TRANSFER
    # ---------------------------------------

    planned_transfer = round(

        max(
            0.0,
            safety - before_transfer
        ),

        2
    )

    # ---------------------------------------
    # REMAINING CASH
    # ---------------------------------------

    remaining = round(

        before_transfer
        + planned_transfer,

        2
    )

    # ---------------------------------------
    # CURRENT 6-HOUR SLOT
    # ---------------------------------------

    slot_hour = (
        now.hour // 6
    ) * 6

    slot_start = now.replace(
        hour=slot_hour,
        minute=0,
        second=0,
        microsecond=0
    )

    slot_end = (
        slot_start
        + timedelta(hours=6)
    )

    # ---------------------------------------
    # REMINDER
    # ---------------------------------------

    if before_transfer < 0:

        level = "CRITICAL"

        message = (

            f"CRITICAL: projected cash "
            f"shortage is "
            f"₹{abs(before_transfer):,.2f}. "

            f"Transfer "
            f"₹{planned_transfer:,.2f} "

            f"from the currency chest "
            f"immediately."
        )

    elif planned_transfer > 0:

        level = "WARNING"

        message = (

            f"Reminder: transfer "
            f"₹{planned_transfer:,.2f} "

            f"from the currency chest "
            f"during the current "
            f"6-hour slot. "

            f"Projected remaining cash "
            f"after transfer: "
            f"₹{remaining:,.2f}."
        )

    else:

        level = "OK"

        message = (

            f"Cash level OK. "

            f"No transfer required "
            f"for the current "
            f"6-hour slot. "

            f"Projected remaining cash: "
            f"₹{remaining:,.2f}."
        )

    data = {

        "branch_code":
            branch_code,

        "slot_start":
            slot_start.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "slot_end":
            slot_end.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "opening_balance":
            opening,

        "projected_withdrawal":
            projected_withdrawal,

        "projected_deposit":
            projected_deposit,

        "balance_before_transfer":
            before_transfer,

        "planned_transfer":
            planned_transfer,

        "remaining_balance":
            remaining,

        "safety_buffer":
            safety,

        "reminder_level":
            level,

        "reminder_message":
            message,

        "next_slot_in_minutes":
            max(
                0,
                int(
                    (
                        slot_end - now
                    ).total_seconds()
                    // 60
                )
            )
    }

    save_cash_monitor(data)

    return data