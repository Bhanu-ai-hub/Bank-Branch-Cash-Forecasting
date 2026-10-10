let lastReminder = "";


function money(value) {

    return "₹" +
        Number(value || 0).toLocaleString(
            "en-IN",
            {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }
        );
}


function enableNotifications() {

    if (!("Notification" in window)) {

        alert(
            "This browser does not support notifications."
        );

        return;
    }


    Notification.requestPermission()
        .then(permission => {

            if (permission === "granted") {

                new Notification(
                    "Bank Cash Forecasting",
                    {
                        body:
                            "6-hour cash reminders are enabled."
                    }
                );
            }

        });
}


function updateMonitor(data) {

    const ids = {

        opening:
            data.opening_balance,

        withdrawal:
            data.projected_withdrawal,

        deposit:
            data.projected_deposit,

        before:
            data.balance_before_transfer,

        transfer:
            data.planned_transfer,

        remaining:
            data.remaining_balance
    };


    Object.entries(ids).forEach(
        ([id, value]) => {

            const element =
                document.getElementById(id);

            if (element) {

                element.textContent =
                    money(value);
            }

        }
    );


    const reminder =
        document.getElementById(
            "reminder"
        );


    if (reminder) {

        reminder.textContent =
            data.reminder_message;
    }


    const level =
        document.getElementById(
            "level"
        );


    if (level) {

        level.textContent =
            data.reminder_level;
    }


    const slot =
        document.getElementById(
            "slot"
        );


    if (slot) {

        slot.textContent =
            `${data.slot_start} → ${data.slot_end}`;
    }


    const next =
        document.getElementById(
            "next-slot"
        );


    if (next) {

        next.textContent =
            `Next slot in ${data.next_slot_in_minutes} minutes.`;
    }


    const card =
        document.getElementById(
            "monitor-card"
        );


    if (card) {

        card.className =
            `card status-card ${
                data.reminder_level.toLowerCase()
            }`;
    }


    if (

        data.reminder_level !== "OK"

        &&

        data.reminder_message !==
            lastReminder

    ) {

        if (

            "Notification" in window

            &&

            Notification.permission ===
                "granted"

        ) {

            new Notification(
                "Bank Cash Reminder",
                {
                    body:
                        data.reminder_message
                }
            );
        }


        lastReminder =
            data.reminder_message;
    }
}


async function refreshCashMonitor() {

    try {

        const response =
            await fetch(
                "/api/cash-monitor",
                {
                    cache: "no-store"
                }
            );


        const result =
            await response.json();


        if (result.success) {

            updateMonitor(
                result.data
            );
        }

    }

    catch (error) {

        console.error(
            "Cash monitor error:",
            error
        );
    }
}


document.addEventListener(
    "DOMContentLoaded",
    () => {

        refreshCashMonitor();

        setInterval(
            refreshCashMonitor,
            60 * 1000
        );

    }
);