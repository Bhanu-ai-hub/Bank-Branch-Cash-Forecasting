from datetime import datetime, timedelta
import pandas as pd

from database import get_connection, get_branch
from forecasting import generate_forecast


SIX_HOUR_PERIODS = 4


def get_six_hour_monitor(branch_code="BR001"):

    branch = get_branch(branch_code)

    if branch is None:
        raise ValueError("Branch not found.")

    # Get existing forecast
    forecast = generate_forecast(branch_code)

    # Get transaction history
    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT
            transaction_date,
            transaction_type,
            amount
        FROM transactions
        WHERE branch_code = ?
        ORDER BY transaction_date DESC
        """,
        conn,
        params=(branch_code,)
    )

    conn.close()

    # -----------------------------------------
    # Expected withdrawal for next 6 hours
    # -----------------------------------------

    six_hour_withdrawal = round(
        float(forecast.get("total_forecast", 0) or 0)
        / SIX_HOUR_PERIODS,
        2
    )

    # -----------------------------------------
    # Expected deposit for next 6 hours
    # -----------------------------------------

    six_hour_deposit = 0.0

    if not df.empty:

        df["transaction_date"] = pd.to_datetime(
            df["transaction_date"],
            errors="coerce"
        )

        df = df.dropna(
            subset=["transaction_date"]
        )

        cutoff = pd.Timestamp(
            datetime.now().date() - timedelta(days=14)
        )

        recent = df[
            df["transaction_date"] >= cutoff
        ]

        deposits = recent[
            recent["transaction_type"]
            .astype(str)
            .str.upper() == "DEPOSIT"
        ]

        if not deposits.empty:

            daily_deposits = (
                deposits
                .groupby(
                    deposits["transaction_date"].dt.date
                )["amount"]
                .sum()
            )

            if not daily_deposits.empty:

                average_daily_deposit = float(
                    daily_deposits.mean()
                )

                six_hour_deposit = round(
                    average_daily_deposit
                    / SIX_HOUR_PERIODS,
                    2
                )

    # -----------------------------------------
    # Current branch cash
    # -----------------------------------------

    current_balance = round(
        float(branch["vault_balance"] or 0),
        2
    )

    safety_buffer = round(
        float(branch["safety_buffer"] or 0),
        2
    )

    # -----------------------------------------
    # Calculate projected cash
    # -----------------------------------------

    projected_balance = round(
        current_balance
        + six_hour_deposit
        - six_hour_withdrawal,
        2
    )

    # -----------------------------------------
    # Transfer recommendation
    # -----------------------------------------

    if projected_balance > safety_buffer:

        transfer_direction = "OUT TO CURRENCY CHEST"

        transfer_amount = round(
            projected_balance - safety_buffer,
            2
        )

        remaining_balance = safety_buffer

        message = (
            f"6-hour reminder: transfer "
            f"₹{transfer_amount:,.2f} "
            f"to the currency chest. "
            f"Estimated branch cash after "
            f"transfer: ₹{remaining_balance:,.2f}."
        )

    elif projected_balance < safety_buffer:

        transfer_direction = "IN FROM CURRENCY CHEST"

        transfer_amount = round(
            safety_buffer - projected_balance,
            2
        )

        remaining_balance = round(
            projected_balance + transfer_amount,
            2
        )

        message = (
            f"6-hour reminder: arrange "
            f"₹{transfer_amount:,.2f} "
            f"from the currency chest. "
            f"Estimated branch cash after "
            f"transfer: ₹{remaining_balance:,.2f}."
        )

    else:

        transfer_direction = "NO TRANSFER"

        transfer_amount = 0.0

        remaining_balance = projected_balance

        message = (
            f"6-hour reminder: no transfer "
            f"required. Estimated branch cash: "
            f"₹{remaining_balance:,.2f}."
        )

    # -----------------------------------------
    # Return monitor information
    # -----------------------------------------

    return {

        "checked_at":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "current_balance":
            current_balance,

        "six_hour_withdrawal":
            six_hour_withdrawal,

        "six_hour_deposit":
            six_hour_deposit,

        "net_cash_movement":
            round(
                six_hour_deposit
                - six_hour_withdrawal,
                2
            ),

        "projected_balance_before_transfer":
            projected_balance,

        "safety_buffer":
            safety_buffer,

        "transfer_direction":
            transfer_direction,

        "transfer_amount":
            transfer_amount,

        "remaining_balance":
            remaining_balance,

        "reminder_message":
            message,

        "forecast_date":
            forecast["forecast_date"]
    }