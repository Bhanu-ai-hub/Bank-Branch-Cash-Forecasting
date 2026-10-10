from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify
)

from database import (
    init_db,
    seed_sample_data,
    get_branch,
    get_transactions,
    get_forecasts,
    get_cash_monitor_history,
    add_transaction,
    update_vault_balance
)

from forecasting import (
    generate_forecast,
    generate_six_hour_monitor
)


app = Flask(__name__)

init_db()
seed_sample_data()

BRANCH = "BR001"


@app.route("/")
def index():

    return render_template(

        "index.html",

        branch=get_branch(BRANCH),

        transactions=
            get_transactions(
                BRANCH,
                10
            ),

        forecast=
            generate_forecast(
                BRANCH
            ),

        monitor=
            generate_six_hour_monitor(
                BRANCH
            )
    )


@app.route("/transactions")
def transactions_page():

    return render_template(

        "transactions.html",

        branch=get_branch(BRANCH),

        transactions=
            get_transactions(
                BRANCH
            )
    )


@app.route(
    "/transactions/add",
    methods=["POST"]
)
def add_transaction_route():

    try:

        add_transaction(

            BRANCH,

            request.form[
                "transaction_date"
            ],

            request.form[
                "transaction_type"
            ],

            float(
                request.form["amount"]
            ),

            request.form["channel"],

            request.form.get(
                "description",
                ""
            ),

            int(
                request.form.get(
                    "is_salary_day",
                    0
                )
            ),

            int(
                request.form.get(
                    "is_festival_day",
                    0
                )
            )
        )

        return redirect(
            url_for(
                "transactions_page"
            )
        )

    except Exception as e:

        return (
            f"<h2>Error</h2>"
            f"<p>{e}</p>"
            f"<a href='/transactions'>Back</a>",
            400
        )


@app.route("/forecast")
def forecast_page():

    return render_template(

        "forecast.html",

        branch=get_branch(BRANCH),

        forecast=
            generate_forecast(
                BRANCH
            )
    )


@app.route("/cash-monitor")
def cash_monitor_page():

    return render_template(

        "cash_monitor.html",

        branch=get_branch(BRANCH),

        monitor=
            generate_six_hour_monitor(
                BRANCH
            ),

        history=
            get_cash_monitor_history(
                BRANCH
            )
    )


@app.route("/reports")
def reports_page():

    return render_template(

        "reports.html",

        branch=get_branch(BRANCH),

        forecasts=
            get_forecasts(
                BRANCH
            ),

        monitor_history=
            get_cash_monitor_history(
                BRANCH
            )
    )


@app.route(
    "/update-vault",
    methods=["POST"]
)
def update_vault():

    try:

        update_vault_balance(

            BRANCH,

            float(
                request.form[
                    "vault_balance"
                ]
            )
        )

        return redirect(
            url_for("index")
        )

    except Exception as e:

        return (
            f"<h2>Error updating "
            f"vault balance</h2>"
            f"<p>{e}</p>"
            f"<a href='/'>Back</a>",
            400
        )


@app.route("/api/forecast")
def forecast_api():

    try:

        return jsonify({

            "success": True,

            "data":
                generate_forecast(
                    BRANCH
                )
        })

    except Exception as e:

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


@app.route("/api/cash-monitor")
def cash_monitor_api():

    try:

        return jsonify({

            "success": True,

            "data":
                generate_six_hour_monitor(
                    BRANCH
                )
        })

    except Exception as e:

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


@app.route("/api/history")
def history_api():

    return jsonify([

        {

            "date":
                x["transaction_date"],

            "type":
                x["transaction_type"],

            "amount":
                x["amount"],

            "channel":
                x["channel"]

        }

        for x in
        get_transactions(BRANCH)
    ])


@app.route("/health")
def health():

    return jsonify({

        "status": "OK",

        "application":
            "Bank Branch Cash Forecasting Tool"

    })


if __name__ == "__main__":

    print(
        "Bank Branch Cash Forecasting Tool"
    )

    print(
        "Open "
        "http://127.0.0.1:5000 "
        "in your browser"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )