# Development notes

Rules and their weights are in `detection/rules.py`. This MVP uses regular expressions, and severity/confidence are engineering choices rather than measured model performance. C metrics are ancillary; Python performs semantic pattern classification. No raw scan content is intentionally persisted.
