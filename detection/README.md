# Detection and risk

`pii_detector.py` contains configurable Python regular-expression rules and masks values before they leave the analysis function. `secret_detector.py` offers a secret-focused interface. `risk_engine.py` applies documented project-defined category weights and caps the total at 100. This heuristic is not scientifically validated.
