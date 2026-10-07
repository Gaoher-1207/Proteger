from .rules import RULES

def assess(findings):
    # Project-defined heuristic: count and category weights, capped to 0–100.
    raw = sum(RULES[f["type"]]["weight"] * f["confidence"] for f in findings)
    score = min(100, round(raw))
    level = "LOW" if score < 25 else "MEDIUM" if score < 50 else "HIGH" if score < 75 else "CRITICAL"
    return {"risk_score": score, "risk_level": level}
