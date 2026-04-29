import requests

NTFY_URL = "https://ntfy.sh/gridwatch-ismael"

PRIORITY = {
    "RED":    ("urgent", "red_circle"),
    "YELLOW": ("high",   "yellow_circle"),
    "GREEN":  ("low",    "green_circle"),
}


def send_alert(risk_level: str, summary: str) -> str:
    """Push a risk alert to the on-call analyst via ntfy.sh.

    Fires automatically when the agent detects RED or YELLOW conditions.
    The analyst receives a phone notification without any manual trigger.
    GREEN risk skips the notification entirely — no noise on quiet mornings.

    Args:
        risk_level: "RED", "YELLOW", or "GREEN"
        summary:    One-sentence briefing summary to include in the notification body.

    Returns:
        Delivery confirmation string the agent can include in its final output,
        or an error message if delivery failed.

    Failure cases handled:
        - Network / timeout error  → returns error string, does not raise
        - Non-200 response         → returns error string with HTTP status
        - GREEN risk level         → returns early, no HTTP call made
    """
    level = risk_level.strip().upper()

    if level == "GREEN":
        return "No alert sent — risk level is GREEN."

    priority, tag = PRIORITY.get(level, ("default", "warning"))

    try:
        resp = requests.post(
            NTFY_URL,
            data=summary.encode("utf-8"),
            headers={
                "Title":    f"GridWatch -- {level} ALERT",
                "Priority": priority,
                "Tags":     f"electric_plug,{tag}",
            },
            timeout=10,
        )
    except requests.RequestException as e:
        return f"Alert delivery failed (network error): {e}"

    if resp.status_code != 200:
        return f"Alert delivery failed (HTTP {resp.status_code}): {resp.text[:120]}"

    return f"Alert sent → ntfy.sh/gridwatch-ismael | priority: {priority} | {level}"


if __name__ == "__main__":
    print("--- RED alert ---")
    print(send_alert("RED", "NYISO demand 18,200 MWh -- 22% above baseline. Severe thunderstorm warning active NYC metro. Peaker deployment likely needed by 15:00."))
    print()
    print("--- YELLOW alert ---")
    print(send_alert("YELLOW", "NYISO demand tracking 14% above 5-hour avg. No active alerts but evening load ramp expected."))
    print()
    print("--- GREEN (no alert) ---")
    print(send_alert("GREEN", "Normal conditions."))
