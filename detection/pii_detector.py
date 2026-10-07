import re
from .rules import RULES

PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "PHONE": re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"),
    "AADHAAR_LIKE": re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)"),
    "CARD_LIKE": re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
    "IP_ADDRESS": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "URL": re.compile(r"https?://[^\s<>'\"]+", re.I),
}
SECRET = re.compile(r"(?i)\b(?:api[_-]?key|token|secret)\b\s*[:=]\s*['\"]?([A-Za-z0-9_./+=-]{8,})")
PASSWORD = re.compile(r"(?i)\bpassword\b\s*[:=]\s*['\"]?([^\s'\"]{4,})")

def mask(kind, value):
    if kind == "EMAIL":
        name, sep, domain = value.partition("@")
        return (name[:1] + "*" * max(1, len(name)-1) + sep + domain) if sep else "[masked]"
    digits = re.sub(r"\D", "", value)
    if kind in {"PHONE", "AADHAAR_LIKE", "CARD_LIKE"} and digits:
        return "X" * max(0, len(digits)-4) + digits[-4:]
    return value[:2] + "[masked]" if len(value) > 2 else "[masked]"

def luhn_valid(value):
    digits = [int(x) for x in re.sub(r"\D", "", value)]
    if not 13 <= len(digits) <= 19: return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2:
            digit *= 2
            if digit > 9: digit -= 9
        total += digit
    return total % 10 == 0

def detect(text):
    found = []
    patterns = dict(PATTERNS)
    patterns["API_KEY"] = re.compile(r"(?i)\b(?:api[_-]?key)\b\s*[:=]\s*['\"]?([A-Za-z0-9_./+=-]{8,})")
    patterns["SECRET_TOKEN"] = re.compile(r"(?i)\b(?:token|secret)\b\s*[:=]\s*['\"]?([A-Za-z0-9_./+=-]{8,})")
    patterns["PASSWORD_LIKE"] = PASSWORD
    for kind, pattern in patterns.items():
        if not RULES[kind]["enabled"]: continue
        for match in pattern.finditer(text):
            value = match.group(1) if kind in {"API_KEY", "SECRET_TOKEN", "PASSWORD_LIKE"} else match.group(0)
            start = match.start(1) if match.lastindex else match.start()
            # Reject obvious invalid IPv4 octets.
            if kind == "IP_ADDRESS" and any(int(x) > 255 for x in value.split(".")): continue
            if kind == "CARD_LIKE" and not luhn_valid(value): continue
            end = start + len(value)
            found.append({"type": kind, "value": mask(kind, value), "location": f"Character {start+1}", "severity": RULES[kind]["severity"], "confidence": 0.92, "_start": start, "_end": end})
    card_spans = [(f["_start"], f["_end"]) for f in found if f["type"] == "CARD_LIKE"]
    found = [f for f in found if not (f["type"] == "AADHAAR_LIKE" and any(a <= f["_start"] and f["_end"] <= b for a,b in card_spans))]
    for finding in found:
        finding.pop("_start"); finding.pop("_end")
    found.sort(key=lambda x: int(x["location"].split()[-1]))
    return found
