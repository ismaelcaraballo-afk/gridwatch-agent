import json
import math
from pathlib import Path

HISTORY_FILE = Path(__file__).parent.parent / ".demand_history.json"
WINDOW_SIZE = 24

# NYISO seasonal baselines — used when rolling window has fewer than 3 readings
DEMAND_BASELINE_MW = 15000.0
DEMAND_STDEV_MW = 2500.0
LMP_BASELINE = 75.0
LMP_STDEV = 40.0

DEMAND_Z_THRESHOLD = 2.0
LMP_Z_THRESHOLD = 2.5


def _load_history() -> list:
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text())
    except Exception:
        pass
    return []


def _save_history(history: list) -> None:
    try:
        HISTORY_FILE.write_text(json.dumps(history[-WINDOW_SIZE:]))
    except Exception:
        pass


def _z_score(value: float, history: list) -> float:
    if len(history) < 3:
        return (value - DEMAND_BASELINE_MW) / DEMAND_STDEV_MW
    mean = sum(history) / len(history)
    variance = sum((x - mean) ** 2 for x in history) / len(history)
    std = math.sqrt(variance) if variance > 0 else 1.0
    return (value - mean) / std


def detect_anomaly(demand_mw: float, lmp_prices: dict) -> str:
    """Detect demand and LMP anomalies using Z-score rolling window. Never raises."""
    try:
        flags = []

        history = _load_history()
        demand_z = _z_score(demand_mw, history)
        history.append(demand_mw)
        _save_history(history)

        if abs(demand_z) >= DEMAND_Z_THRESHOLD:
            direction = "above" if demand_z > 0 else "below"
            flags.append(
                f"DEMAND ANOMALY: {demand_mw:,.0f} MW is {abs(demand_z):.1f}σ {direction} rolling avg"
            )

        for zone, price in lmp_prices.items():
            lmp_z = (float(price) - LMP_BASELINE) / LMP_STDEV
            if abs(lmp_z) >= LMP_Z_THRESHOLD:
                direction = "above" if lmp_z > 0 else "below"
                flags.append(
                    f"LMP ANOMALY: {zone} ${price:.0f}/MWh ({abs(lmp_z):.1f}σ {direction} baseline)"
                )

        if not flags:
            return (
                f"No anomalies detected — demand {demand_mw:,.0f} MW "
                f"(Z={demand_z:.2f}), LMP within normal range."
            )

        return "⚠ ANOMALY DETECTED\n" + "\n".join(f"  • {f}" for f in flags)

    except Exception as e:
        return f"Anomaly detection unavailable: {e}"


if __name__ == "__main__":
    print(detect_anomaly(25000, {"NYC": 187, "LONGIL": 172}))
    print()
    print(detect_anomaly(14000, {"NYC": 55, "LONGIL": 52}))
