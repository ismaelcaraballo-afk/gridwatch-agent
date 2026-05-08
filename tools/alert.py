import json
import os
import tempfile
import time
import requests

_ntfy_topic_raw = os.environ.get("NTFY_TOPIC", "").strip()
if not _ntfy_topic_raw:
    raise RuntimeError("NTFY_TOPIC env var is required — set it in .env")
NTFY_TOPICS = [t.strip() for t in _ntfy_topic_raw.split(",") if t.strip()]
STATE_FILE  = os.path.join(tempfile.gettempdir(), f"gridwatch_alert_{os.getuid()}.json")

PRIORITY = {
    "RED":    ("urgent", "red_circle"),
    "YELLOW": ("high",   "yellow_circle"),
    "GREEN":  ("low",    "green_circle"),
}

# Cooldown in seconds before the same risk level fires again.
# Escalation (YELLOW → RED) always bypasses cooldown.
COOLDOWN = {
    "RED":    15 * 60,   # 15 minutes
    "YELLOW": 60 * 60,   # 60 minutes
}

RISK_RANK = {"GREEN": 0, "YELLOW": 1, "RED": 2}


def _load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_state(level: str) -> None:
    if os.path.islink(STATE_FILE):
        os.unlink(STATE_FILE)
    with open(STATE_FILE, "w") as f:
        json.dump({"last_level": level, "last_time": time.time()}, f)


def _is_suppressed(level: str) -> tuple[bool, str]:
    state = _load_state()
    if not state:
        return False, ""

    last_level = state.get("last_level", "GREEN")
    last_time = state.get("last_time", 0)
    elapsed = time.time() - last_time

    # Always fire if this is an escalation
    if RISK_RANK.get(level, 0) > RISK_RANK.get(last_level, 0):
        return False, ""

    cooldown = COOLDOWN.get(level, 0)
    if elapsed < cooldown:
        remaining = int((cooldown - elapsed) / 60)
        return True, f"Alert suppressed — {level} already sent {int(elapsed/60)}m ago (cooldown {cooldown//60}m, {remaining}m remaining)."

    return False, ""


def send_alert(risk_level: str, summary: str) -> str:
    """Push a risk alert to the on-call analyst via ntfy.sh.

    Fires automatically when the agent detects RED or YELLOW conditions.
    GREEN skips the push. Repeated same-level alerts are suppressed during
    the cooldown window (RED: 15 min, YELLOW: 60 min). Escalation always fires.
    """
    level = risk_level.strip().upper().replace("\n", "").replace("\r", "")

    if level == "GREEN":
        return "No alert sent — risk level is GREEN."

    suppressed, reason = _is_suppressed(level)
    if suppressed:
        return reason

    priority, tag = PRIORITY.get(level, ("default", "warning"))

    sent = []
    failed = []
    for topic in NTFY_TOPICS:
        try:
            resp = requests.post(
                f"https://ntfy.sh/{topic}",
                data=summary.encode("utf-8"),
                headers={
                    "Title":    f"GridWatch -- {level} ALERT",
                    "Priority": priority,
                    "Tags":     f"electric_plug,{tag}",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                sent.append(topic)
            else:
                failed.append(f"{topic}(HTTP {resp.status_code})")
        except requests.RequestException as e:
            failed.append(f"{topic}({e})")

    if not sent:
        return f"Alert delivery failed for all topics: {', '.join(failed)}"

    _save_state(level)
    result = f"Alert sent → {', '.join(f'ntfy.sh/{t}' for t in sent)} | priority: {priority} | {level}"
    if failed:
        result += f" | failed: {', '.join(failed)}"
    return result


if __name__ == "__main__":
    print("--- RED alert ---")
    print(send_alert("RED", "NYISO demand 18,200 MWh -- 22% above baseline. Severe thunderstorm warning active NYC metro. Peaker deployment likely needed by 15:00."))
    print()
    print("--- YELLOW alert ---")
    print(send_alert("YELLOW", "NYISO demand tracking 14% above 5-hour avg. No active alerts but evening load ramp expected."))
    print()
    print("--- GREEN (no alert) ---")
    print(send_alert("GREEN", "Normal conditions."))
