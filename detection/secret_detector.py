from .pii_detector import detect

def detect_secrets(text):
    return [item for item in detect(text) if item["type"] in {"API_KEY", "PASSWORD_LIKE", "SECRET_TOKEN"}]
