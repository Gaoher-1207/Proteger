RULES = {
    "EMAIL": {"severity": "MEDIUM", "weight": 12, "enabled": True},
    "PHONE": {"severity": "MEDIUM", "weight": 12, "enabled": True},
    "AADHAAR_LIKE": {"severity": "HIGH", "weight": 22, "enabled": True},
    "CARD_LIKE": {"severity": "HIGH", "weight": 24, "enabled": True},
    "API_KEY": {"severity": "CRITICAL", "weight": 35, "enabled": True},
    "PASSWORD_LIKE": {"severity": "HIGH", "weight": 25, "enabled": True},
    "IP_ADDRESS": {"severity": "LOW", "weight": 7, "enabled": True},
    "URL": {"severity": "LOW", "weight": 5, "enabled": True},
    "SECRET_TOKEN": {"severity": "HIGH", "weight": 25, "enabled": True},
}
